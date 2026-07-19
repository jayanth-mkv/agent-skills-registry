#!/usr/bin/env python3
"""Create a compact GIF preview from selected segments of a real demo video."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def segment(value: str) -> tuple[float, float]:
    try:
        start, duration = (float(part) for part in value.split(":", 1))
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError("segment must be START:DURATION in seconds") from exc
    if start < 0 or duration <= 0:
        raise argparse.ArgumentTypeError("segment start must be >= 0 and duration must be > 0")
    return start, duration


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--segment",
        action="append",
        type=segment,
        dest="segments",
        help="START:DURATION in seconds; repeat to join multiple moments",
    )
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--fps", type=int, default=10)
    parser.add_argument("--colors", type=int, default=96)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    segments = args.segments or [(0.0, 10.0)]

    if not args.source.is_file():
        print(f"Source video not found: {args.source}", file=sys.stderr)
        return 2
    if args.output.suffix.lower() != ".gif":
        print("Output must use the .gif extension.", file=sys.stderr)
        return 2
    if args.width < 320 or not 4 <= args.fps <= 20 or not 16 <= args.colors <= 256:
        print("Use width >= 320, fps 4–20, and colors 16–256.", file=sys.stderr)
        return 2

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        print("ffmpeg is required but was not found on PATH.", file=sys.stderr)
        return 2

    command = [ffmpeg, "-y"]
    for start, duration in segments:
        command.extend(["-ss", str(start), "-t", str(duration), "-i", str(args.source)])

    filters: list[str] = []
    labels: list[str] = []
    for index, (_, duration) in enumerate(segments):
        fade_out = max(duration - 0.2, 0)
        chain = f"[{index}:v]setpts=PTS-STARTPTS"
        chain += f",fade=t=out:st={fade_out}:d=0.2"
        if index:
            chain += ",fade=t=in:st=0:d=0.2"
        label = f"v{index}"
        filters.append(f"{chain}[{label}]")
        labels.append(f"[{label}]")

    filters.append(f"{''.join(labels)}concat=n={len(labels)}:v=1:a=0[cut]")
    filters.append(
        f"[cut]fps={args.fps},scale={args.width}:-2:flags=lanczos,split[base][palettein]"
    )
    filters.append(f"[palettein]palettegen=max_colors={args.colors}:stats_mode=diff[palette]")
    filters.append("[base][palette]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle[out]")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    command.extend(["-filter_complex", ";".join(filters), "-map", "[out]", "-loop", "0", str(args.output)])

    completed = subprocess.run(command, check=False)
    if completed.returncode:
        return completed.returncode

    size_mb = args.output.stat().st_size / (1024 * 1024)
    print(f"Created {args.output} ({size_mb:.2f} MB)")
    if sum(duration for _, duration in segments) > 12:
        print("WARN: preview is longer than the recommended 12 seconds.")
    if size_mb > 5:
        print("WARN: preview is larger than the preferred 5 MB.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
