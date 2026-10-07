# mix_bgm.py — post-mix a BGM bed onto a finished narration video (renderer's track-11
# BGM is unreliable; this is the battle-tested path). Sidechain-ducks the bed under
# the existing narration, fades in/out, keeps the video stream untouched (stream copy).
#
# Usage:
#   python mix_bgm.py --video renders/video.mp4 --bgm assets/bgm/bgm.mp3 [--out ...] \
#                     [--volume 0.18] [--pre-duck 0.02] [--ratio 5]
#
# Verify after: volumedetect on a narration window (~ -24dB) and a breathing-gap
# window (~ -30dB bed audible); gap windows of ~ -90dB mean the bed is MISSING.
import argparse
import subprocess
import shutil
from pathlib import Path


def ffmpeg_bin():
    import _ff
    return _ff.ffmpeg()


def duration_of(path: Path) -> float:
    out = subprocess.run([ffmpeg_bin(), "-v", "error", "-i", str(path), "-f", "null", "-"], capture_output=True)
    # use ffprobe-equivalent via ffmpeg parsing: prefer ffprobe if present
    import _ff
    fp = _ff.ffprobe()
    if fp:
        r = subprocess.run([fp, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
        return float(r.stdout.strip())
    raise SystemExit("ffprobe not found")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--bgm", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument("--volume", type=float, default=0.18)
    ap.add_argument("--pre-duck", type=float, default=0.02, help="sidechain threshold (linear)")
    ap.add_argument("--ratio", type=float, default=5.0)
    args = ap.parse_args()

    video = Path(args.video)
    out = Path(args.out) if args.out else video.with_name(video.stem + "_bgm.mp4")
    dur = duration_of(video)
    fade_out_start = max(0.0, dur - 2.0)

    fc = (
        f"[1:a]atrim=0:{dur:.3f},"
        f"afade=t=in:st=0:d=1.2,afade=t=out:st={fade_out_start:.3f}:d=2,"
        f"volume={args.volume}[bed];"
        f"[bed][0:a]sidechaincompress=threshold={args.pre_duck}:ratio={args.ratio}:attack=120:release=800[duck];"
        f"[duck][0:a]amix=inputs=2:duration=first:normalize=0[aout]"
    )
    cmd = [
        ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(video), "-stream_loop", "-1", "-i", str(args.bgm),
        "-filter_complex", fc,
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        str(out),
    ]
    subprocess.run(cmd, check=True)
    print(f"✓ {out} · dur {dur:.2f}s · bed volume {args.volume} · duck ratio {args.ratio}")
    print("  自检建议：旁白窗口 ~-24dB（人声主导）；呼吸气口窗口 ~-30dB（底乐透出）；若气口 ~-90dB 则底乐缺失")


if __name__ == "__main__":
    main()
