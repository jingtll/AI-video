"""Offline regression tests: malformed scripts and audio must stop production."""
import importlib.util
import asyncio
import json
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("gen_narration", SCRIPTS / "gen_narration.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


class ScriptTests(unittest.TestCase):
    def test_fullwidth_frame_heading_is_read(self):
        self.assertEqual(gen.parse_script_lines("## Line 7 — 标题（Frame 2）\n    缓存让读取更快。\n"), {2: "缓存让读取更快。"})

    def test_duplicate_frame_is_rejected(self):
        with self.assertRaises(ValueError):
            gen.parse_script_lines("## Line 1 — A (Frame 1)\n    甲。\n## Line 2 — B (Frame 1)\n    乙。")

    def test_missing_spoken_block_is_rejected(self):
        with self.assertRaises(ValueError):
            gen.parse_script_lines("## Line 1 — A (Frame 1)\n没有缩进口播。")

    def test_unrecognized_script_is_rejected(self):
        with self.assertRaises(ValueError):
            gen.parse_script_lines("# 随便一个标题\n    这段不能悄悄消失。")

    def test_negative_speech_samples_are_not_tail_silence(self):
        pcm = struct.pack("<hhhh", 500, -10000, -9000, 0)
        self.assertAlmostEqual(gen.tail_silence(pcm), 1 / 24000)


class NarrationCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)
        (self.project / "assets/voice").mkdir(parents=True)
        self.text = "缓存让读取更快。"
        (self.project / "SCRIPT.md").write_text("## Line 7 — 标题 (Frame 2)\n    " + self.text + "\n", encoding="utf-8")
        self.audio = self.project / "assets/voice/02.wav"
        with wave.open(str(self.audio), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(24000)
            out.writeframes(struct.pack("<h", 3000) * 48000)
        self.voice = {"frame": 2, "path": "assets/voice/02.wav", "duration_s": 2.5,
                      "audio_duration_s": 2.0, "tail_pad_s": 0.5, "source_text": self.text,
                      "words": [{"id": 0, "text": self.text, "start": 0.1, "end": 1.9}]}

    def tearDown(self):
        self.tmp.cleanup()

    def run_qa(self, voices):
        (self.project / "audio_meta.json").write_text(json.dumps({"voices": voices, "sfx": [], "bgm": None}, ensure_ascii=False), encoding="utf-8")
        return subprocess.run([sys.executable, str(SCRIPTS / "qa_narration.py"), "--project", str(self.project)], capture_output=True, text=True, encoding="utf-8")

    def test_valid_audio_passes_with_line_number_different_from_frame(self):
        result = self.run_qa([self.voice])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_empty_voices_stop_pipeline(self):
        self.assertNotEqual(self.run_qa([]).returncode, 0)

    def test_missing_word_timestamps_stop_pipeline(self):
        self.voice["words"] = []
        self.assertNotEqual(self.run_qa([self.voice]).returncode, 0)

    def test_missing_audio_file_stops_pipeline(self):
        self.audio.unlink()
        self.assertNotEqual(self.run_qa([self.voice]).returncode, 0)

    def test_word_past_actual_audio_stops_pipeline(self):
        self.voice["words"][0]["end"] = 2.3
        self.assertNotEqual(self.run_qa([self.voice]).returncode, 0)

    def test_duplicate_metadata_frames_stop_pipeline(self):
        self.assertNotEqual(self.run_qa([self.voice, self.voice]).returncode, 0)

    def test_unspoken_stale_frame_stops_pipeline(self):
        stale = dict(self.voice, frame=3)
        self.assertNotEqual(self.run_qa([self.voice, stale]).returncode, 0)

    def test_changed_script_stops_pipeline(self):
        self.voice["source_text"] = "旧版本旁白。"
        self.assertNotEqual(self.run_qa([self.voice]).returncode, 0)

    def test_preflight_checks_storyboard_before_creating_audio(self):
        (self.project / "STORYBOARD.md").write_text("## Frame 3 — 新镜头\n- voiceover: 第二段旁白。\n", encoding="utf-8")
        result = subprocess.run([sys.executable, str(SCRIPTS / "gen_narration.py"), "--project", str(self.project), "--check-only"], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.project / "audio_meta.json").exists())


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)
        self.voice_dir = self.project / "assets/voice"
        self.voice_dir.mkdir(parents=True)
        (self.project / "SCRIPT.md").write_text("## Line 1 — A (Frame 1)\n    第一段。\n## Line 2 — B (Frame 2)\n    第二段。\n", encoding="utf-8")
        self.meta = {"bgm": {"path": "assets/bgm/test.mp3"}, "sfx": [{"frame": 1, "file": "assets/sfx/test.wav"}], "voices": [{"frame": 3, "path": "assets/voice/03.mp3", "duration_s": 2.5, "words": []}]}
        self.meta_path = self.project / "audio_meta.json"
        self.meta_path.write_text(json.dumps(self.meta), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    async def fake_tts(self, text, voice, rate, out_path):
        # Replace only the network boundary; actual WAV decoding/MP3 encoding remains real.
        with wave.open(str(out_path), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(24000)
            out.writeframes(struct.pack("<h", 3000) * 48000)
        return [{"id": 0, "text": text, "start": 0.1, "end": 1.9}]

    def test_selective_update_preserves_other_audio_and_music_fields(self):
        old = self.voice_dir / "02.mp3"
        old.write_bytes(b"untouched-frame-2")
        self.meta["voices"].append({"frame": 2, "path": "assets/voice/02.mp3", "duration_s": 2.5, "words": []})
        self.meta_path.write_text(json.dumps(self.meta), encoding="utf-8")
        with patch.object(gen, "synth", self.fake_tts), patch.object(sys, "argv", ["gen", "--project", str(self.project), "--frames", "1", "--segmented"]):
            asyncio.run(gen.main())
        meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
        self.assertEqual([v["frame"] for v in meta["voices"]], [1, 2])
        self.assertEqual(meta["bgm"], self.meta["bgm"])
        self.assertEqual(meta["sfx"], self.meta["sfx"])
        self.assertEqual(old.read_bytes(), b"untouched-frame-2")
        self.assertEqual(meta["voices"][0]["source_text"], "第一段。")

    def test_later_tts_failure_preserves_published_audio_and_metadata(self):
        old = self.voice_dir / "01.mp3"
        old.write_bytes(b"published-before-run")
        original_meta = self.meta_path.read_bytes()
        async def failing_tts(text, voice, rate, path):
            if text == "第二段。":
                raise OSError("controlled network failure")
            return await self.fake_tts(text, voice, rate, path)
        with patch.object(gen, "synth", failing_tts), patch.object(sys, "argv", ["gen", "--project", str(self.project)]):
            with self.assertRaises(OSError):
                asyncio.run(gen.main())
        self.assertEqual(old.read_bytes(), b"published-before-run")
        self.assertEqual(self.meta_path.read_bytes(), original_meta)

    def test_duplicate_existing_frames_stop_before_tts(self):
        self.meta["voices"] = [{"frame": 2, "path": "first.mp3"}, {"frame": 2, "path": "second.mp3"}]
        self.meta_path.write_text(json.dumps(self.meta), encoding="utf-8")
        before = self.meta_path.read_bytes()
        with patch.object(gen, "synth") as tts, patch.object(sys, "argv", ["gen", "--project", str(self.project), "--frames", "1"]):
            with self.assertRaises(ValueError):
                asyncio.run(gen.main())
            tts.assert_not_called()
        self.assertEqual(self.meta_path.read_bytes(), before)

    def assert_publication_failure_rolls_back(self, failed_name):
        for number in (1, 2):
            (self.voice_dir / f"{number:02d}.mp3").write_bytes(f"old-{number}".encode())
        before = self.meta_path.read_bytes()
        real_replace = Path.replace
        def failing_replace(source, target):
            if Path(target).name == failed_name:
                raise OSError("controlled publication failure")
            return real_replace(source, target)
        with patch.object(gen, "synth", self.fake_tts), patch.object(Path, "replace", failing_replace), patch.object(sys, "argv", ["gen", "--project", str(self.project)]):
            with self.assertRaises(OSError):
                asyncio.run(gen.main())
        self.assertEqual((self.voice_dir / "01.mp3").read_bytes(), b"old-1")
        self.assertEqual((self.voice_dir / "02.mp3").read_bytes(), b"old-2")
        self.assertEqual(self.meta_path.read_bytes(), before)

    def test_second_audio_publication_failure_rolls_back(self):
        self.assert_publication_failure_rolls_back("02.mp3")

    def test_metadata_publication_failure_rolls_back(self):
        self.assert_publication_failure_rolls_back("audio_meta.json")


if __name__ == "__main__":
    unittest.main()
