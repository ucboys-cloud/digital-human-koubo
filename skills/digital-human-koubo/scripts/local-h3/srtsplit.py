"""按语音端点（silencedetect）切分时间轴生成 SRT。

适用：多段拼接的成片，段间有静音间隙，whisper 的连续转写对齐会错位。
做法：检测语音区间 -> 取长度达标的区间 -> 与剧本逐句配对。
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys


def speech_spans(wav: pathlib.Path, noise="-32dB", min_sil=0.25) -> list[tuple[float, float]]:
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(wav), "-af",
         f"silencedetect=n={noise}:d={min_sil}", "-f", "null", "-"],
        capture_output=True, text=True)
    log = p.stderr
    total = float(re.search(r"Duration: (\d+):(\d+):([\d.]+)", log).group(0).split("Duration: ")[1]
                  .replace(":", " ").split()[0]) if False else None
    dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(wav)], capture_output=True, text=True).stdout.strip()
    total = float(dur)

    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]

    spans: list[tuple[float, float]] = []
    cur = 0.0
    for i, s in enumerate(starts):
        if s > cur + 0.05:
            spans.append((cur, s))
        cur = ends[i] if i < len(ends) else total
    if cur < total - 0.05:
        spans.append((cur, total))
    return spans


def ts(t: float) -> str:
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def main() -> None:
    wav, txt, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
    min_len = float(sys.argv[4]) if len(sys.argv) > 4 else 0.6

    lines = [x.strip() for x in txt.read_text(encoding="utf-8").splitlines() if x.strip()]
    spans = [s for s in speech_spans(wav) if s[1] - s[0] >= min_len]
    if len(spans) != len(lines):
        print(f"⚠ 语音区间 {len(spans)} 个 / 剧本 {len(lines)} 句")
        for i, s in enumerate(spans):
            print(f"   span{i + 1}: {s[0]:.2f}-{s[1]:.2f} ({s[1] - s[0]:.2f}s)")

    blocks = []
    for i, (a, b) in enumerate(spans[: len(lines)]):
        blocks.append(f"{i + 1}\n{ts(a)} --> {ts(b)}\n{lines[i]}")
    out.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    print(f"共 {len(blocks)} 条 -> {out}")
    for b in blocks:
        n, t, x = b.split("\n")
        print(f"  {t.split(' --> ')[0]}  {x}")


if __name__ == "__main__":
    main()
