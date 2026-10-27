"""一键口播：文案 → VoxCPM2 配音 → H3 音频直驱 → 成片。

定死了工作模式：**H3 不发声，只按输入音频对口型**。
所以唯一要操心的就是「配音长度」和「H3 段数×每段秒数」对上。

    python pipeline.py --script 剧本.txt --image 形象图.png \
      --prompt-template prompts/live_40s.txt \
      --reference "<参考音频目录>/自然口播女声01.MP3" --auto-prompt \
      --target 40 --out out/final.mp4

也可以跳过配音，直接用现成的 wav：
    python pipeline.py --audio 现成配音.wav --image 形象图.png \
      --prompt-template prompts/live_40s.txt --out out/final.mp4

它会做四件事：
  1. 调 tts.py 生成配音（或直接用 --audio）
  2. 按配音总长自动算 chunks × chunk_seconds（每块 4–30s，尽量靠近 10s）
  3. 把提示词模板的块数补齐/裁剪到 chunks 个，并把每块台词换成该块的稿子
  4. 调 h3c_run.py --drive-audio 出片
"""
import argparse
import pathlib
import re
import shutil
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
PY = sys.executable

CHUNK_MIN, CHUNK_MAX = 4.0, 30.0     # H3ContinuumSamplerV39 的硬边界
PREFER_SECONDS = 10.0                # 每段理想时长
MAX_CHUNKS = 16


def ffprobe_dur(p: pathlib.Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return float((r.stdout.strip() or 0) or 0)


def plan_chunks(total: float, prefer: float = PREFER_SECONDS, prefer_n: int | None = None):
    """按总长挑 chunks × chunk_seconds：每块落在 4–30s，尽量靠近 prefer 秒。

    prefer_n 合法时优先用它——让块边界落在句子边界上，模型更容易连贯。
    """
    legal = [(n, total / n) for n in range(1, MAX_CHUNKS + 1)
             if CHUNK_MIN <= total / n <= CHUNK_MAX]
    if not legal:
        sys.exit(f"总长 {total:.2f}s 配不出合法分块（每块必须 {CHUNK_MIN}-{CHUNK_MAX}s，"
                 f"最多 {MAX_CHUNKS} 块）")
    if prefer_n and any(n == prefer_n for n, _ in legal):
        return prefer_n, total / prefer_n
    return min(legal, key=lambda x: abs(x[1] - prefer))


def split_chunks(text: str) -> tuple[str, list[str]]:
    """把模板拆成 preamble + 各块正文（块正文不含 [Chunk N] 标记行）。"""
    m = re.search(r"^\[Chunk 1\]\s*$", text, re.M)
    if not m:
        sys.exit("模板里没找到独占一行的 `[Chunk 1]`")
    pre = text[:m.start()].rstrip()
    parts = re.split(r"^\[Chunk \d+\]\s*$", text[m.start():], flags=re.M)[1:]
    return pre, [p.strip("\n") for p in parts]


def fit_prompt(tpl: str, n: int, seg_texts: list[str]) -> str:
    """把模板块数调整到 n：多则截断，少则复制末块（加 Continuation）。"""
    pre, blocks = split_chunks(tpl)
    if len(blocks) > n:
        blocks = blocks[:n]
    while len(blocks) < n:
        src = blocks[-1]
        src = re.sub(r"^Continuation of Chunk \d+\.\s*", "", src).strip()
        blocks.append(f"Continuation of Chunk {len(blocks)}.\n" + src)

    out = [pre]
    for i, b in enumerate(blocks, 1):
        # 台词换成这一块的稿子（H3 不发声，台词只是帮它对语义和表情）
        if i - 1 < len(seg_texts) and seg_texts[i - 1]:
            line = f"<d>[中文] {seg_texts[i-1]}</d>"
            if re.search(r"<d>\s*\[[^\]]*\]\s*.*?</d>", b, re.S):
                b = re.sub(r"<d>\s*\[[^\]]*\]\s*.*?</d>", line, b, flags=re.S)
            else:
                b = b.rstrip() + "\n" + line
        out.append(f"\n[Chunk {i}]\n{b.strip()}\n")
    return "\n".join(out) + "\n"


def group_script(segs: list[str], n: int) -> list[str]:
    """把剧本分段合并成 n 组（每组对应一个 chunk）。"""
    if not segs:
        return []
    if len(segs) <= n:
        return segs + [""] * (n - len(segs))
    per, rem = divmod(len(segs), n)
    out, k = [], 0
    for i in range(n):
        take = per + (1 if i < rem else 0)
        out.append("".join(segs[k:k + take]))
        k += take
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default="", help="文稿（## 分段）")
    ap.add_argument("--audio", default="", help="已有配音，跳过 TTS")
    ap.add_argument("--image", required=True)
    ap.add_argument("--prompt-template", required=True, help="Continuum 提示词模板（含 [Chunk 1]）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--target", type=float, default=None, help="配音目标总长（精确对齐）")
    ap.add_argument("--seconds", type=float, default=None, help="每段秒数，不传则自动挑")
    # 配音参数（透传给 tts.py）
    ap.add_argument("--reference", default="")
    ap.add_argument("--prompt-text", default="")
    ap.add_argument("--auto-prompt", action="store_true")
    ap.add_argument("--voice", default="")
    ap.add_argument("--gap", type=float, default=0.0)
    ap.add_argument("--lead", type=float, default=0.0,
                    help="片头留多少秒静音（给人站稳的准备时间，常用 1.2–1.8）")
    ap.add_argument("--timesteps", type=int, default=15)
    ap.add_argument("--cfg", type=float, default=2.0)
    # 视频参数
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    ap.add_argument("--megapixels", type=float, default=None)
    ap.add_argument("--size-source", default=None)
    ap.add_argument("--steps", type=int, default=None)
    ap.add_argument("--keep-temp", action="store_true")
    a = ap.parse_args()

    if not a.script and not a.audio:
        sys.exit("需要 --script（生成配音）或 --audio（用现成配音）")

    outdir = pathlib.Path(a.out).parent
    outdir.mkdir(parents=True, exist_ok=True)
    tag = time.strftime("%H%M%S")

    # ---- 1. 配音 ----
    if a.audio:
        voice = pathlib.Path(a.audio)
        if not voice.exists():
            sys.exit(f"配音不存在: {voice}")
        print(f"用现成配音: {voice}")
    else:
        sys.path.insert(0, str(HERE))
        from tts import parse_script
        segs = parse_script(a.script)
        print(f"配音：{len(segs)} 段")
        voice = outdir / f"_voice_{tag}.wav"
        cmd = [PY, str(HERE / "tts.py"), "--script", a.script, "--out", str(voice),
               "--timesteps", str(a.timesteps), "--cfg", str(a.cfg),
               "--gap", str(a.gap), "--offload", "end"]
        if a.reference:
            cmd += ["--reference", a.reference]
            if a.auto_prompt:
                cmd += ["--auto-prompt"]
            if a.prompt_text:
                cmd += ["--prompt-text", a.prompt_text]
        if a.voice:
            cmd += ["--voice", a.voice]
        if a.target:
            cmd += ["--target", str(a.target)]
        if a.lead:
            cmd += ["--lead", str(a.lead)]
        subprocess.run(cmd, check=True)

    total = ffprobe_dur(voice)
    print(f"\n配音总长 {total:.3f}s")

    # ---- 2. 配分块 ----
    sys.path.insert(0, str(HERE))
    from tts import parse_script
    n_segs = len(parse_script(a.script)) if a.script else 0

    if a.seconds:
        n = max(1, round(total / a.seconds))
        n = min(n, MAX_CHUNKS)
        secs = total / n
        if not (CHUNK_MIN <= secs <= CHUNK_MAX):
            sys.exit(f"{n} 段 × {secs:.2f}s 越界（每块须 {CHUNK_MIN}-{CHUNK_MAX}s）")
    else:
        n, secs = plan_chunks(total, prefer_n=n_segs or None)
    print(f"→ H3 分块: {n} 段 × {secs:.2f}s = {n*secs:.2f}s")

    # ---- 3. 生成匹配块数的提示词 ----
    tpl = pathlib.Path(a.prompt_template).read_text(encoding="utf-8")
    if a.script:
        seg_texts = group_script(parse_script(a.script), n)
    else:
        seg_texts = []
    prompt_path = outdir / f"_prompt_{tag}.txt"
    prompt_path.write_text(fit_prompt(tpl, n, seg_texts), encoding="utf-8")
    print(f"→ 提示词: {prompt_path}（{n} 块）")

    # ---- 4. 出片 ----
    cmd = [PY, "-u", str(HERE / "h3c_run.py"),
           "--image", a.image, "--text-file", str(prompt_path),
           "--chunks", str(n), "--seconds", f"{secs:.3f}",
           "--drive-audio", str(voice),
           "--prefix", f"koubo/pipe{tag}", "--out", a.out]
    for k, v in (("--width", a.width), ("--height", a.height),
                 ("--megapixels", a.megapixels), ("--steps", a.steps)):
        if v is not None:
            cmd += [k, str(v)]
    if a.size_source:
        cmd += ["--size-source", a.size_source]
    print()
    subprocess.run(cmd, check=True)

    if not a.keep_temp:
        voice.unlink(missing_ok=True)
        prompt_path.unlink(missing_ok=True)
        shutil.rmtree(HERE / "out" / "_tts_tmp", ignore_errors=True)

    print(f"\n完成: {a.out}")
