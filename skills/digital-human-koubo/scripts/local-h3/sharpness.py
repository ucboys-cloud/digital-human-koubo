"""逐秒测画面清晰度（拉普拉斯方差），用来判断长视频有没有分块性发虚。"""
import os
import pathlib
import shutil
import subprocess
import sys

import numpy as np


def _ffmpeg() -> str:
    """PATH 优先，其次 FFMPEG_DIR，最后几个常见安装位置。"""
    found = shutil.which("ffmpeg")
    if found:
        return found
    exe = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    cands = [pathlib.Path(os.environ["FFMPEG_DIR"]) / exe] if os.environ.get("FFMPEG_DIR") else []
    cands += [pathlib.Path(r"C:\ffmpeg\bin") / exe]
    for c in cands:
        if c.exists():
            return str(c)
    sys.exit("找不到 ffmpeg：装进 PATH，或设 FFMPEG_DIR 指向 bin 目录")


FFMPEG = _ffmpeg()


def frame_at(path, t, w=416):
    cmd = [FFMPEG, "-v", "error", "-ss", str(t), "-i", path, "-frames:v", "1",
           "-vf", f"scale={w}:-2,format=gray", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    h = len(raw) // w
    return np.frombuffer(raw[: w * h], dtype=np.uint8).reshape(h, w).astype(np.float32)


def sharpness(img):
    k = np.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]], dtype=np.float32)
    h, w = img.shape
    out = np.zeros((h - 2, w - 2), dtype=np.float32)
    for dy in range(3):
        for dx in range(3):
            if k[dy, dx]:
                out += k[dy, dx] * img[dy: dy + h - 2, dx: dx + w - 2]
    return float(out.var())


def main():
    path = sys.argv[1]
    dur = float(subprocess.run([FFMPEG.replace("ffmpeg.exe", "ffprobe.exe"), "-v", "error",
                                "-show_entries", "format=duration", "-of", "csv=p=0", path],
                               capture_output=True, text=True).stdout.strip())
    print(f"{path}  时长 {dur:.2f}s")
    t = 1.0
    vals = []
    while t < dur - 0.5:
        s = sharpness(frame_at(path, t))
        vals.append((t, s))
        bar = "#" * int(min(60, s / 4))
        print(f"  {t:>5.1f}s  {s:>8.1f}  {bar}")
        t += 2.0
    arr = np.array([v for _t, v in vals])
    print(f"\n  均值 {arr.mean():.1f}  最低 {arr.min():.1f}  最高 {arr.max():.1f}  "
          f"波动(标准差/均值) {arr.std() / arr.mean() * 100:.0f}%")


if __name__ == "__main__":
    main()
