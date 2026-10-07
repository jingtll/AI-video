# pick_bgm.py — objective busy-ness metrics for BGM candidates (choose the STEADIEST bed).
# Lower onset density + lower env variance + moderate brightness = won't fight the narration.
# Usage: python pick_bgm.py c1.mp3 c2.mp3 ...
import struct
import subprocess
import sys
from pathlib import Path

SR = 16000


def ffmpeg_bin():
    import _ff
    return _ff.ffmpeg()


def pcm(path: Path):
    return subprocess.run([ffmpeg_bin(), "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True).stdout


def analyze(path: Path):
    raw = pcm(path)
    n = len(raw) // 2
    x = struct.unpack(f"<{n}h", raw)
    hop = SR // 100
    env = [sum(abs(v) for v in x[i:i + hop]) / hop for i in range(0, n - hop, hop)]
    onsets, last = 0, -10
    for i in range(4, len(env) - 1):
        loc = sum(env[max(0, i - 20):i]) / max(1, min(20, i))
        if env[i] > loc * 1.6 and env[i] > 300 and i - last > 10:
            onsets += 1
            last = i
    dur = n / SR
    zc = sum(1 for i in range(1, n, 7) if (x[i] >= 0) != (x[i - 1] >= 0))
    zcr = zc / (n / 7) * SR / 2 / 1000
    mean = sum(env) / len(env)
    var = sum((e - mean) ** 2 for e in env) / len(env)
    print(f"{path.name}: dur {dur:.0f}s · onsets {onsets/dur:.1f}/s · brightness~{zcr:.2f}kHz · 动态方差 {var:.0f}（越低越稳=越适合垫底）")


if __name__ == "__main__":
    for f in sys.argv[1:]:
        analyze(Path(f))
