# synth_bgm.py — synthesize an ambient chord-progression music bed locally with ffmpeg.
# No library, no license: pure sines layered into chord pads (fundamental + 2 soft
# harmonics + a detuned copy), gentle edges, room echo, band-limited under narration.
#
# Usage:
#   python synth_bgm.py --out assets/bgm/synth.mp3 [--dur 120] [--mood bright|calm] [--tempo 4]
#
# Output mean level is auto-normalized to ~ -20dB (a good pre-mix bed level; the
# sidechain duck in mix_bgm.py handles the rest).
import argparse
import math
import struct
import subprocess
import wave
from pathlib import Path

import _ff

SR = 24000


def ffmpeg_bin():
    return _ff.ffmpeg()


# simple pad voicings (Hz). bright: C–G–Am–F around C4 · calm: Am–F–C–G an octave down.
PROGRESSIONS = {
    "bright": [
        [261.63, 329.63, 392.00],
        [196.00, 246.94, 293.66],
        [220.00, 261.63, 329.63],
        [174.61, 220.00, 261.63],
    ],
    "calm": [
        [110.00, 130.81, 164.81],
        [87.31, 110.00, 130.81],
        [130.81, 164.81, 196.00],
        [87.31, 130.81, 174.61],
    ],
}


def tone_pcm(freq: float, seconds: float, gain: float, detune: float = 0.0) -> bytes:
    n = int(seconds * SR)
    out = bytearray()
    w = 2 * math.pi / SR
    for i in range(n):
        v = 0.0
        v += math.sin(w * freq * i)
        if detune:
            v += 0.5 * math.sin(w * (freq + detune) * i)
        v += 0.35 * math.sin(w * 2 * freq * i)
        v += 0.12 * math.sin(w * 3 * freq * i)
        # soft edge envelope so chords don't click
        edge = SR // 8
        g = gain
        if i < edge:
            g *= i / edge
        if n - i < edge:
            g *= (n - i) / edge
        out += struct.pack("<h", int(max(-1.0, min(1.0, v / 2.2)) * 32767 * g))
    return bytes(out)


def build_chord(notes, seconds) -> bytes:
    parts = [tone_pcm(f, seconds, 1.0, detune=2.5 if j == 0 else 0.0) for j, f in enumerate(notes)]
    n = len(parts[0]) // 2
    mix = [0] * n
    for p in parts:
        vals = struct.unpack(f"<{len(p)//2}h", p)
        for i, v in enumerate(vals):
            mix[i] += v
    peak = max(1, max(abs(v) for v in mix))
    scale = min(1.0, 32767 * 0.9 / peak)
    return struct.pack(f"<{n}h", *[int(v * scale) for v in mix])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="assets/bgm/synth.mp3")
    ap.add_argument("--dur", type=float, default=120.0, help="target bed length in seconds")
    ap.add_argument("--mood", choices=["bright", "calm"], default="bright")
    ap.add_argument("--tempo", type=float, default=4.0, help="seconds per chord")
    args = ap.parse_args()

    prog = PROGRESSIONS[args.mood]
    chord_secs = max(2.0, args.tempo)
    loop_pcm = b"".join(build_chord(notes, chord_secs) for notes in prog)
    n_needed = int(args.dur * SR) * 2
    pcm = (loop_pcm * (n_needed // len(loop_pcm) + 1))[:n_needed]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp_wav = out.with_suffix(".tmp.wav")
    with wave.open(str(tmp_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm)

    ff = ffmpeg_bin()
    # band-limit + gentle room + normalize toward -20dB mean
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(tmp_wav), "-af",
                    "highpass=f=70,lowpass=f=3000,aecho=0.8:0.7:60|120:0.25|0.15,"
                    "volume=-14dB,loudnorm=I=-20:TP=-3:LRA=7",
                    "-ar", "24000", "-ac", "1", str(tmp_wav) + ".n.wav"], check=True)
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(tmp_wav) + ".n.wav", "-c:a", "libmp3lame", "-q:a", "2", str(out)], check=True)
    tmp_wav.unlink(missing_ok=True)
    Path(str(tmp_wav) + ".n.wav").unlink(missing_ok=True)
    print(f"✓ {out} · {args.dur}s · mood {args.mood} · 和弦进行 {args.mood} · 供 mix_bgm.py 侧链后混使用")


if __name__ == "__main__":
    main()
