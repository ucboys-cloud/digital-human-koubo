"""给参考音频库建索引：文件名 / 时长 / 采样率 / 说话内容摘要。

用本地 whisper 逐个转写，输出 markdown 表。
一次性跑，之后直接看 refs_index.md 挑音色。
"""
import json
import os
import pathlib
import shutil
import subprocess

# 参考音频目录：分号（Windows）或冒号（*nix）分隔，可给多个
DIRS = [d for d in os.environ.get("REFS_DIRS", "").replace(os.pathsep, ";").split(";") if d.strip()]
OUT_MD = pathlib.Path(__file__).resolve().parent / "out" / "refs_index.md"
TMP = pathlib.Path(__file__).resolve().parent / "out" / "refs" / "_tmp"


def _tool(env: str, name: str) -> str:
    """先看环境变量（可给目录或可执行文件全路径），再退回 PATH。"""
    v = os.environ.get(env, "").strip()
    if v:
        p = pathlib.Path(v)
        if p.is_dir():
            p = p / (name + (".exe" if os.name == "nt" else ""))
        if p.exists():
            return str(p)
    found = shutil.which(name)
    if not found:
        raise SystemExit(f"找不到 {name}：设环境变量 {env}，或把它加进 PATH")
    return found


FF = _tool("FFMPEG_DIR", "ffmpeg")
WX = _tool("WHISPER_DIR", "whisper-cli")


def _find_model(whisper_exe: str) -> str:
    """WHISPER_MODEL 优先，否则在 whisper-cli 附近找 ggml-*.bin。"""
    v = os.environ.get("WHISPER_MODEL", "").strip()
    if v and pathlib.Path(v).exists():
        return v
    base = pathlib.Path(whisper_exe).parent
    for d in (base, base.parent, base / "models", base.parent / "models",
              pathlib.Path.cwd() / "models", pathlib.Path.cwd()):
        if not d.is_dir():
            continue
        hits = sorted(d.glob("ggml-*.bin"))
        if hits:
            return str(hits[0])
    raise SystemExit("找不到 whisper 模型：设 WHISPER_MODEL 指向 ggml-*.bin")


MODEL = _find_model(WX)
AUDIO_EXT = (".wav", ".mp3", ".flac", ".m4a")


def probe(p: pathlib.Path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration:stream=sample_rate,channels",
                        "-of", "json", str(p)], capture_output=True, text=True)
    j = json.loads(r.stdout or "{}")
    dur = float(j.get("format", {}).get("duration", 0) or 0)
    st = (j.get("streams") or [{}])[0]
    return dur, st.get("sample_rate", "?"), st.get("channels", "?")


def transcribe(p: pathlib.Path, idx: int) -> str:
    TMP.mkdir(parents=True, exist_ok=True)
    wav = TMP / f"i{idx}.wav"
    subprocess.run([FF, "-y", "-v", "error", "-i", str(p), "-ar", "16000", "-ac", "1", str(wav)],
                   capture_output=True)
    r = subprocess.run([WX, "-m", MODEL, "-l", "zh", "-nt", "-np", str(wav)],
                       capture_output=True, text=True)
    return " ".join(r.stdout.split())


if __name__ == "__main__":
    rows = []
    idx = 0
    for d in DIRS:
        p = pathlib.Path(d)
        if not p.is_dir():
            continue
        for f in sorted(x for x in p.iterdir() if x.suffix.lower() in AUDIO_EXT):
            idx += 1
            dur, sr, ch = probe(f)
            txt = transcribe(f, idx)
            rows.append({"dir": p.name, "name": f.name, "dur": dur, "sr": sr,
                         "ch": ch, "text": txt, "path": str(f)})
            print(f"[{idx}] {f.name[:26]:<28} {dur:>6.1f}s  {txt[:34]}", flush=True)

    lines = ["# 参考音频库索引", "",
             f"共 {len(rows)} 个。VoxCPM2 克隆要求参考音频 **≤50 秒**、内容干净（无背景音乐、无第二人声）。", ""]
    for d in DIRS:
        sub = [r for r in rows if r["dir"] == pathlib.Path(d).name]
        if not sub:
            continue
        lines += [f"## {d}（{len(sub)} 个）", "",
                  "| 文件 | 时长 | 格式 | 说话内容（whisper 转写，可能是繁体） | 可用 |",
                  "|---|---|---|---|---|"]
        for r in sub:
            ok = "✅" if 3 <= r["dur"] <= 50 else ("⚠ 过长需裁" if r["dur"] > 50 else "⚠ 过短")
            lines.append(f"| {r['name']} | {r['dur']:.1f}s | {r['sr']}Hz/{r['ch']}ch | "
                         f"{r['text'][:40] or '（转写为空）'} | {ok} |")
        lines.append("")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n索引已写入 {OUT_MD}")
