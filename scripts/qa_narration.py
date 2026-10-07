"""Fail-closed narration QA: exit 1 for content/timing failures, 2 for bad input."""
import argparse
import json
import re
import subprocess
from pathlib import Path
from _contracts import TAIL_PAD, audio_path, decoded_duration, finite_number, script_for_project, validate_words


def spoken_beats(text: str) -> int:
    return len(re.findall(r"[\u3400-\u9fff]", text)) + len(re.findall(r"[A-Za-z0-9][A-Za-z0-9.\-]*", text))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--max-rate", type=float, default=5.6)
    ap.add_argument("--min-rate", type=float, default=3.0)
    ap.add_argument("--max-run", type=float, default=6.5)
    ap.add_argument("--min-tail", type=float, default=0.35)
    ap.add_argument("--pause-threshold", type=float, default=0.25)
    args = ap.parse_args()
    for name in ("max_rate", "min_rate", "max_run", "min_tail", "pause_threshold"):
        finite_number(getattr(args, name), name, 0.001)
    if args.min_rate > args.max_rate:
        raise ValueError("min-rate 不能大于 max-rate")
    project = Path(args.project).resolve()
    lines = script_for_project(project)
    meta = json.loads((project / "audio_meta.json").read_text(encoding="utf-8-sig"))
    voices = meta.get("voices")
    if not isinstance(voices, list) or not voices:
        raise ValueError("voices 为空或缺失；有口播的项目必须有音频")
    numbers = [v.get("frame") for v in voices if isinstance(v, dict)]
    if len(numbers) != len(voices) or any(type(n) is not int or n < 1 for n in numbers):
        raise ValueError("voices 包含无效镜头编号")
    if len(set(numbers)) != len(numbers):
        raise ValueError("voices 包含重复镜头编号")
    if set(numbers) != set(lines):
        raise ValueError(f"音频/脚本镜头不一致: 缺少 {sorted(set(lines) - set(numbers))}, 遗留 {sorted(set(numbers) - set(lines))}")
    failures = []
    print("镜头   实际音频   语速   尾气口   最长无停顿   结果")
    for voice in voices:
        number = voice["frame"]
        try:
            duration = decoded_duration(audio_path(project, voice.get("path")))
            scene_duration = finite_number(voice.get("duration_s"), "duration_s", 0.001)
            pad = finite_number(voice.get("tail_pad_s", TAIL_PAD), "tail_pad_s")
            recorded = finite_number(voice.get("audio_duration_s", scene_duration - pad), "audio_duration_s", 0.001)
            if abs(recorded - duration) > 0.08 or abs(scene_duration - duration - pad) > 0.08:
                raise ValueError("元数据时长与实际音频不一致；重新生成后同步分镜")
            if "source_text" in voice and voice["source_text"] != lines[number]:
                raise ValueError("脚本已变更，当前音频来自旧旁白")
            words = voice.get("words")
            validate_words(words, duration)
            last = max(w["end"] for w in words)
            tail = scene_duration - last
            rate = spoken_beats(lines[number]) / duration
            run, start = 0.0, words[0]["start"]
            for previous, word in zip(words, words[1:]):
                if word["start"] - previous["end"] > args.pause_threshold:
                    run = max(run, previous["end"] - start)
                    start = word["start"]
            run = max(run, last - start)
            flags = []
            if not args.min_rate <= rate <= args.max_rate:
                flags.append("语速不在项目阈值内")
            if tail < args.min_tail:
                flags.append("尾气口不足")
            if run > args.max_run:
                flags.append("长段无停顿")
            print(f"{number:>3} {duration:>9.2f}s {rate:>5.2f} {tail:>7.2f}s {run:>9.2f}s  {'；'.join(flags) or '通过'}")
            if flags:
                failures.append(number)
        except (ValueError, OSError, subprocess.CalledProcessError) as exc:
            failures.append(number)
            print(f"{number:>3}  失败: {exc}")
    print("结论: " + (f"需处理镜头 {failures}" if failures else "配音体检通过"))
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, TypeError, AttributeError) as exc:
        print(f"配音体检失败: {exc}")
        raise SystemExit(2) from exc
