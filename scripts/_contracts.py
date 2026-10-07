"""Shared SCRIPT.md and audio contracts for the Chinese narration adapters."""
import math
import re
import subprocess
from pathlib import Path

SR = 24000
TAIL_PAD = 0.5


def parse_script_lines(md: str) -> dict[int, str]:
    out, current, parts = {}, None, []

    def flush():
        if current is None:
            return
        text = re.sub(r"\s+", " ", " ".join(parts)).strip()
        if not text:
            raise ValueError(f"Frame {current}: 缺少 4 空格缩进的口播文本")
        out[current] = text

    for line in md.splitlines():
        if re.match(r"^#{2,3}\s+", line):
            flush()
            current, parts = None, []
            match = re.search(r"[（(]\s*frame\s+(\d+)\s*[)）]", line, re.I)
            if match:
                current = int(match.group(1))
                if current < 1 or current in out:
                    raise ValueError(f"Frame {current}: 编号重复或小于 1")
            elif re.match(r"^#{2,3}\s+Line\b", line, re.I):
                raise ValueError(f"无法识别口播标题: {line}")
            continue
        if current is not None and not re.match(r"^\s*\*\*", line):
            match = re.match(r"^(?: {4,}|\t)(\S.*)$", line)
            if match:
                parts.append(match.group(1).strip())
    flush()
    if not out:
        raise ValueError("SCRIPT.md 未解析出任何口播；检查 (Frame N) 和文本缩进")
    return out


def script_for_project(project: Path) -> dict[int, str]:
    lines = parse_script_lines((project / "SCRIPT.md").read_text(encoding="utf-8-sig"))
    storyboard = project / "STORYBOARD.md"
    if storyboard.exists():
        expected, seen, frame = set(), set(), None
        for line in storyboard.read_text(encoding="utf-8-sig").splitlines():
            heading = re.match(r"^#{2,3}\s+(?:Frame|Beat|Scene)\s+(\d+)\b", line, re.I)
            if heading:
                frame = int(heading.group(1))
                if frame in seen or frame < 1:
                    raise ValueError(f"STORYBOARD.md: Frame {frame} 编号重复或无效")
                seen.add(frame)
            elif re.match(r"^#{1,3}\s+", line):
                frame = None
            voice = re.match(r"^\s*[-*]\s*(?:voiceover|vo|voice_over|narration)\s*:\s*(.*)$", line, re.I)
            if frame is not None and voice:
                text = voice.group(1).strip().strip("\"'")
                if text and text.lower() not in {"none", "null", "~", "-"}:
                    expected.add(frame)
        if not seen:
            raise ValueError("STORYBOARD.md 未识别到 Frame/Beat/Scene N 镜头")
        if expected != set(lines):
            raise ValueError(f"分镜/脚本口播不一致: 缺少 {sorted(expected - set(lines))}, 多余 {sorted(set(lines) - expected)}")
    return lines


def finite_number(value, name: str, minimum=0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: 必须是数值")
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f"{name}: 非有限值或小于 {minimum}")
    return float(value)


def validate_words(words, audio_duration: float):
    if not isinstance(words, list) or not words:
        raise ValueError("无词级时间戳，无法生成字幕")
    previous_end = 0.0
    for index, word in enumerate(words):
        if not isinstance(word, dict) or not isinstance(word.get("text"), str) or not word["text"].strip():
            raise ValueError(f"词 {index}: 缺少文字")
        start = finite_number(word.get("start"), f"词 {index}.start")
        end = finite_number(word.get("end"), f"词 {index}.end")
        if end <= start or start < previous_end - 0.03 or end > audio_duration + 0.03:
            raise ValueError(f"词 {index}: 时间戳倒序、重叠或超过实际音频")
        previous_end = end


def audio_path(project: Path, value) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("缺少音频路径")
    path = (project / value).resolve()
    if not path.is_relative_to(project.resolve()) or not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"音频缺失、为空或不在项目目录内: {value}")
    return path


def decoded_duration(path: Path) -> float:
    import _ff
    result = subprocess.run([_ff.ffmpeg(), "-v", "error", "-i", str(path), "-ar", str(SR), "-ac", "1", "-f", "s16le", "-"], capture_output=True, check=True)
    duration = len(result.stdout) / (2 * SR)
    if duration <= 0:
        raise ValueError(f"音频解码为空: {path.name}")
    return duration
