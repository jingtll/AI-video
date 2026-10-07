# gen_narration.py — edge-tts narration generator for the HyperFrames faceless-explainer pipeline.
#
# Generates per-frame narration MP3s + word-level timings from SCRIPT.md, and writes
# audio_meta.json in the "product-launch" shape consumed by the pipeline
# (sync-durations / captions.mjs / assemble-index.mjs).
#
# Modes:
#   (default)            regenerate ALL frames, plain synthesis (one shot per line)
#   --frames 2,3,5       regenerate only these frames
#   --segmented          split lines at major boundaries (。；：？！——) and insert a
#                        breathing gap (0.32s default) — kills "run-on" narration
#   --extra-split 标记    additionally split after this exact substring (frame 3 style)
#   --gap 0.32           breathing gap seconds (with --segmented)
#   --rate +8%           speech rate
#   --voice zh-CN-YunyangNeural   any edge-tts voice id
#
# CRITICAL: edge-tts >= 7 defaults boundary="SentenceBoundary" — captions need
# boundary="WordBoundary" or you get ZERO word events. Do not remove.
#
# Usage:
#   python gen_narration.py --project <project_dir> [--frames 2,3] [--segmented] [...]
import argparse
import asyncio
import json
import re
import shutil
import struct
import subprocess
import tempfile
import wave
from pathlib import Path

from _contracts import SR, TAIL_PAD, decoded_duration, parse_script_lines, script_for_project, validate_words
SPLIT_AFTER = "。；：？！"


def split_text(text: str, extra_marks=()):
    parts, buf, i = [], "", 0
    while i < len(text):
        ch = text[i]
        buf += ch
        if ch in SPLIT_AFTER:
            parts.append(buf)
            buf = ""
        elif ch == "—" and i + 1 < len(text) and text[i + 1] == "—":
            parts.append(buf + "—")
            buf = ""
            i += 1
        i += 1
    if buf.strip():
        parts.append(buf)
    segs = [p for p in parts if p.strip()]
    for mark in extra_marks:
        out = []
        for part in segs:
            out.extend(x for x in part.replace(mark, mark + "\x00").split("\x00") if x.strip())
        segs = out
    return segs


async def synth(text: str, voice: str, rate: str, out_path: Path):
    import edge_tts
    words = []
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    with open(out_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                s = chunk["offset"] / 1e7
                words.append({"id": len(words), "text": chunk["text"], "start": round(s, 3), "end": round(s + chunk["duration"] / 1e7, 3)})
    if not words or out_path.stat().st_size == 0:
        raise ValueError("TTS 未返回音频或 WordBoundary；保留原有文件并停止")
    return words


def ffmpeg_bin():
    import _ff
    return _ff.ffmpeg()


def mp3_to_pcm(mp3_path: Path, wav_path: Path):
    subprocess.run([ffmpeg_bin(), "-y", "-loglevel", "error", "-i", str(mp3_path), "-ar", str(SR), "-ac", "1", "-sample_fmt", "s16", str(wav_path)], check=True)
    with wave.open(str(wav_path), "rb") as w:
        return w.readframes(w.getnframes())


def write_wav(pcm: bytes, path: Path):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm)


def tail_silence(pcm: bytes) -> float:
    n = len(pcm) // 2
    tail = 0
    while tail < n and abs(struct.unpack_from("<h", pcm, (n - 1 - tail) * 2)[0]) < 120:
        tail += 1
    return tail / SR


async def synth_plain(frame_no, text, voice, rate, voice_dir):
    final = voice_dir / f"{frame_no:02d}.mp3"
    words = await synth(text, voice, rate, final)
    total = decoded_duration(final)
    return final, words, total


async def synth_segmented(frame_no, text, voice, rate, gap, extra_marks, voice_dir):
    segs = split_text(text, extra_marks)
    pieces, words_all, offset = [], [], 0.0
    tmps = []
    for si, seg in enumerate(segs):
        raw_mp3 = voice_dir / f"tmp_{frame_no}_{si}.mp3"
        raw_wav = voice_dir / f"tmp_{frame_no}_{si}.wav"
        tmps += [raw_mp3, raw_wav]
        w = await synth(seg, voice, rate, raw_mp3)
        pcm = mp3_to_pcm(raw_mp3, raw_wav)
        dur = len(pcm) / 2 / SR
        head = max(0.0, (w[0]["start"] if w else 0.0) - 0.06)
        last_end = max(x["end"] for x in w) if w else dur
        tail_cut = min(dur, max(last_end + 0.10, dur - tail_silence(pcm)), dur)
        pcm_cut = pcm[int(head * SR) * 2: int(tail_cut * SR) * 2]
        d = len(pcm_cut) / 2 / SR
        for x in w:
            words_all.append({"id": len(words_all), "text": x["text"], "start": round(max(0.0, x["start"] - head + offset), 3), "end": round(x["end"] - head + offset, 3)})
        pieces.append(pcm_cut)
        if si < len(segs) - 1:
            pieces.append(b"\x00\x00" * int(gap * SR))
            offset += d + int(gap * SR) / SR
        else:
            offset += d
    final = voice_dir / f"{frame_no:02d}.mp3"
    final_wav = voice_dir / f"tmp_{frame_no}_final.wav"
    tmps.append(final_wav)
    write_wav(b"".join(pieces), final_wav)
    subprocess.run([ffmpeg_bin(), "-y", "-loglevel", "error", "-i", str(final_wav), "-c:a", "libmp3lame", "-q:a", "2", str(final)], check=True)
    for t in tmps:
        t.unlink(missing_ok=True)
    return final, words_all, len(b"".join(pieces)) / 2 / SR


def publish_files(files, voice_dir):
    """Roll back caught publication errors; retain backups if recovery fails."""
    backup_dir = Path(tempfile.mkdtemp(prefix="narration-backup-", dir=voice_dir))
    backups, attempted, retain = {}, [], False
    try:
        for index, (_, destination) in enumerate(files):
            backup = backup_dir / str(index) if destination.exists() else None
            if backup is not None:
                shutil.copyfile(destination, backup)
            backups[destination] = backup
        for source, destination in files:
            attempted.append(destination)
            source.replace(destination)
    except OSError as failure:
        recovery_errors = []
        for destination in reversed(attempted):
            try:
                backup = backups[destination]
                if backup is None:
                    destination.unlink(missing_ok=True)
                else:
                    shutil.copyfile(backup, destination)
            except OSError as error:
                recovery_errors.append(str(error))
        if recovery_errors:
            retain = True
            raise OSError(f"发布失败且回滚未完成；原文件备份保留于 {backup_dir}: {recovery_errors}") from failure
        raise
    finally:
        if not retain:
            for backup in backup_dir.iterdir():
                backup.unlink()
            backup_dir.rmdir()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--frames", default="")
    ap.add_argument("--segmented", action="store_true")
    ap.add_argument("--gap", type=float, default=0.32)
    ap.add_argument("--tail-pad", type=float, default=TAIL_PAD)
    ap.add_argument("--check-only", action="store_true", help="validate script without TTS or writes")
    ap.add_argument("--rate", default="+8%")
    ap.add_argument("--voice", default="zh-CN-YunyangNeural")
    ap.add_argument("--extra-split", action="append", default=[], help="split after this substring (applies to all selected frames)")
    args = ap.parse_args()

    project = Path(args.project).resolve()
    import math
    if not all(math.isfinite(v) and v >= 0 for v in (args.gap, args.tail_pad)):
        raise ValueError("gap / tail-pad 必须是有限的非负秒数")
    lines = script_for_project(project)
    wanted = sorted(int(x) for x in args.frames.split(",")) if args.frames else sorted(lines)
    if len(wanted) != len(set(wanted)) or any(n not in lines for n in wanted):
        raise ValueError("--frames 存在重复编号或脚本中不存在的镜头")
    meta_path = project / "audio_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8-sig")) if meta_path.exists() else {"bgm": None, "bgm_pending": False, "voices": [], "sfx": []}
    if not isinstance(meta, dict) or not isinstance(meta.get("voices", []), list):
        raise ValueError("audio_meta.json 必须是对象，voices 必须是数组")
    meta_by_frame, seen = {}, set()
    for item in meta.get("voices", []):
        number = item.get("frame") if isinstance(item, dict) else None
        if type(number) is not int or number < 1 or number in seen:
            raise ValueError("已有 voices 含无效或重复镜头；先修复元数据，不能静默覆盖")
        seen.add(number)
        if number in lines:
            meta_by_frame[number] = dict(item)
    if args.check_only:
        print(f"脚本预检通过: {len(lines)} 个口播镜头，选中 {wanted}")
        return
    voice_dir = project / "assets" / "voice"
    voice_dir.mkdir(parents=True, exist_ok=True)
    # Finish synthesis in staging before replacing any published audio.
    with tempfile.TemporaryDirectory(prefix="narration-", dir=voice_dir) as temporary:
        stage = Path(temporary)
        generated = []
        for n in wanted:
            text = lines[n]
            if args.segmented:
                final, words, _ = await synth_segmented(n, text, args.voice, args.rate, args.gap, tuple(args.extra_split), stage)
            else:
                final, words, _ = await synth_plain(n, text, args.voice, args.rate, stage)
            total = decoded_duration(final)
            validate_words(words, total)
            v = meta_by_frame.get(n, {"frame": n})
            v.update({"path": f"assets/voice/{n:02d}.mp3", "duration_s": round(total + args.tail_pad, 3),
                      "audio_duration_s": round(total, 3), "tail_pad_s": args.tail_pad,
                      "source_text": text, "voice": args.voice, "rate": args.rate, "words": words})
            meta_by_frame[n] = v
            generated.append((final, voice_dir / f"{n:02d}.mp3"))
            print(f"帧{n}: {total:.2f}s + {args.tail_pad:.2f}s 尾气口 · {len(words)} 词事件")
        meta["voices"] = [meta_by_frame[k] for k in sorted(meta_by_frame)]
        meta.setdefault("bgm", None)
        meta.setdefault("bgm_pending", False)
        meta.setdefault("sfx", [])
        meta_tmp = stage / "audio_meta.json"
        meta_tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        publish_files([*generated, (meta_tmp, meta_path)], voice_dir)
    print(f"✓ audio_meta.json · voices {len(meta['voices'])} · bgm {'保留' if meta['bgm'] else '无'} · sfx {len(meta['sfx'])}（已有 sfx/bgm 字段原样保留）")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"配音生成失败: {exc}") from exc
