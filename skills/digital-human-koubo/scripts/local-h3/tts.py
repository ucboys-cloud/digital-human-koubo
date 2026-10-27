"""批量配音：VoxCPM2 TTS/克隆 → wav，顺手把显存管干净。

为什么要这个脚本：
  VoxCPM2 的模型实例缓存在模块级字典里，不归 ComfyUI 的显存管理管，
  跑完会常驻 5.5GB；而且 `force_offload=True` 时每段都要重新从磁盘读 8GB（约 10 秒）。
  批量配音的正解是「模型常驻跑完所有段 → 最后统一 /free 一次」。

用法：
    # 纯 TTS（音色用文字描述）
    python tts.py --script 剧本.txt --out out/voice.wav \
        --voice "年轻女声，语速偏快，字字清楚，接近资讯口播"

    # 音色克隆
    python tts.py --script 剧本.txt --out out/voice.wav \
        --reference 参考音.wav --prompt-text "参考音的原文"

    # 要对齐到 H3 的 40 秒（自动补静音，长度精确）
    python tts.py --script 剧本.txt --out out/voice.wav --target 40

剧本格式：`## 第N段` 分段，一行一句；不写 `##` 就把每个非空行当一段。
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request

COMFY = "http://127.0.0.1:8188"
HERE = pathlib.Path(__file__).resolve().parent
INPUT_DIR = pathlib.Path(__import__("os").environ.get(
    "COMFY_INPUT", r"D:\ComfyUI_windows_portable\ComfyUI\input"))


def _tool(env: str, name: str, guesses: tuple[str, ...] = ()) -> str:
    """PATH 优先，其次名字对应的环境变量（可给目录或全路径），最后常见位置。"""
    found = shutil.which(name)
    if found:
        return found
    v = (__import__("os").environ.get(env) or "").strip()
    if v:
        p = pathlib.Path(v)
        if p.is_dir():
            p = p / (name + (".exe" if __import__("os").name == "nt" else ""))
        if p.exists():
            return str(p)
    for g in guesses:
        if pathlib.Path(g).exists():
            return g
    sys.exit(f"找不到 {name}：装进 PATH，或设环境变量 {env}")


FFMPEG_EXE = _tool("FFMPEG_DIR", "ffmpeg", (r"C:\ffmpeg\bin\ffmpeg.exe",))
FFPROBE_EXE = _tool("FFMPEG_DIR", "ffprobe", (r"C:\ffmpeg\bin\ffprobe.exe",))


def _find_model(whisper_exe: str) -> str:
    """whisper 模型：WHISPER_MODEL 优先，否则在 whisper-cli 附近找 ggml-*.bin。"""
    v = (__import__("os").environ.get("WHISPER_MODEL") or "").strip()
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
    sys.exit("找不到 whisper 模型：设 WHISPER_MODEL 指向 ggml-*.bin")


def _post(path, payload=None):
    data = json.dumps(payload or {}).encode()
    req = urllib.request.Request(COMFY + path, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}


def _get(path):
    with urllib.request.urlopen(COMFY + path, timeout=60) as r:
        return json.load(r)


def parse_script(path: str) -> list[str]:
    """按 ## 分段；没有 ## 就每行一段。段内多行合并成一句。"""
    raw = pathlib.Path(path).read_text(encoding="utf-8")
    segs, cur = [], []
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("##"):
            if cur:
                segs.append("".join(cur))
                cur = []
            continue
        cur.append(s)
    if cur:
        segs.append("".join(cur))
    return segs


def prepare_audio(src: str) -> str:
    """参考音频 → ComfyUI input 目录，返回相对路径。"""
    p = pathlib.Path(src)
    if not p.exists():
        sys.exit(f"参考音频不存在: {p}")
    dst_dir = INPUT_DIR / "tts_ref"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / p.name
    shutil.copy2(p, dst)
    return f"tts_ref/{p.name}"


def transcribe_ref(src: str) -> str:
    """用本地 whisper 转写参考音频，作为克隆的 prompt_text。

    VoxCPM2 知道参考音说了什么，克隆会明显更稳（ultimate cloning）。
    whisper 中文默认输出繁体，不影响克隆（都是汉字）。
    """
    wx = _tool("WHISPER_DIR", "whisper-cli")
    model = _find_model(wx)
    if not pathlib.Path(model).exists():
        sys.exit(f"找不到 whisper 模型: {model}（设 WHISPER_MODEL 环境变量）")

    tmp = (HERE / "out" / "_tts_tmp").resolve()
    tmp.mkdir(parents=True, exist_ok=True)
    wav = tmp / "ref16.wav"
    subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-i", str(pathlib.Path(src).resolve()),
                    "-ar", "16000", "-ac", "1", str(wav)], check=True)
    r = subprocess.run([str(wx), "-m", model, "-l", "zh", "-nt", "-np", str(wav)],
                       capture_output=True, text=True)
    text = " ".join(r.stdout.split())
    if not text:
        print("⚠ 参考音频转写为空，退回「只用参考音」的克隆模式（效果略弱）")
    return text


def run_one(text: str, cfg: dict, tag: str) -> pathlib.Path:
    """跑一段，返回下载到本地的 flac。"""
    prefix = f"tts_{tag}"
    if cfg["mode"] == "clone":
        graph = {
            "1": {"class_type": "LoadAudio", "inputs": {"audio": cfg["ref_audio"]}},
            "2": {"class_type": "VoxCPM2_Clone", "inputs": {
                "model_name": "VoxCPM2", "lora_name": "None",
                "voice_description": cfg.get("voice", ""),
                "text": text, "reference_audio": ["1", 0],
                "prompt_text": cfg.get("prompt_text", ""),
                "cfg_value": cfg["cfg_value"], "inference_timesteps": cfg["timesteps"],
                "max_tokens": cfg["max_tokens"], "normalize_text": True,
                "enable_denoiser": False, "seed": cfg["seed"],
                "force_offload": cfg["force_offload"],
                "dtype": "auto", "device": "cuda",
                "enable_asr": False, "retry_max_attempts": 0, "retry_threshold": 6.0,
                "torch_compile": False,
            }},
            "3": {"class_type": "SaveAudio", "inputs": {"audio": ["2", 0], "filename_prefix": prefix}},
        }
    else:
        graph = {
            "1": {"class_type": "VoxCPM2_TTS", "inputs": {
                "model_name": "VoxCPM2", "lora_name": "None",
                "voice_description": cfg.get("voice", ""),
                "text": text, "cfg_value": cfg["cfg_value"],
                "inference_timesteps": cfg["timesteps"], "max_tokens": cfg["max_tokens"],
                "normalize_text": True, "seed": cfg["seed"],
                "force_offload": cfg["force_offload"],
                "dtype": "auto", "device": "cuda", "torch_compile": False,
            }},
            "2": {"class_type": "SaveAudio", "inputs": {"audio": ["1", 0], "filename_prefix": prefix}},
        }

    r = _post("/prompt", {"prompt": graph, "client_id": f"tts_{tag}"})
    if r.get("node_errors"):
        print("节点报错:", json.dumps(r["node_errors"], ensure_ascii=False)[:1500])
        sys.exit(1)
    pid = r["prompt_id"]

    t0 = time.time()
    out_dir = HERE / "out" / "_tts_tmp"
    out_dir.mkdir(parents=True, exist_ok=True)
    while time.time() - t0 < 900:
        h = _get(f"/history/{pid}")
        if h:
            v = list(h.values())[0]
            st = v.get("status", {})
            for m in st.get("messages", []):
                if m[0] == "execution_error":
                    print("\n执行失败:", str(m[1].get("exception_message"))[:600])
                    sys.exit(2)
            if st.get("completed"):
                for _nid, o in (v.get("outputs") or {}).items():
                    for it in (o.get("audio") or []):
                        fn = it.get("filename")
                        if not fn:
                            continue
                        url = (f"{COMFY}/view?filename={urllib.parse.quote(fn)}"
                               f"&subfolder={urllib.parse.quote(it.get('subfolder') or '')}"
                               f"&type={it.get('type', 'output')}")
                        dest = out_dir / fn
                        dest.write_bytes(urllib.request.urlopen(url, timeout=300).read())
                        return dest
                sys.exit("历史里没找到音频输出")
        time.sleep(1.5)
    sys.exit("超时")


def dur(p: pathlib.Path) -> float:
    out = subprocess.run([FFPROBE_EXE,
                          "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def trim_head(src: pathlib.Path, dest: pathlib.Path, scan: float = 0.85,
              window: float = 0.02, silence: float = 0.012, need_ms: float = 60) -> bool:
    """裁掉开头粘着的「上一句尾音残响」。

    VoxCPM2 每生成一段，都会把上一次推理的尾部残响贴到新段开头：前 ~260ms 是
    一段固定形状的衰减噪声（实测峰值 0.43–0.62，500 次采样三点一致），接着是
    ~100ms 完全静音，然后台词才真正起音——听感就是「开头啪一下」。

    判断依据只认「完全静音段」：前 scan 秒里最后一段 ≥need_ms 的全静音之后才是
    语音起点。找不到就认为没有残响，原样保留（不误伤正常起音）。
    """
    import array
    import wave
    w = wave.open(str(src), "rb")
    sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
    raw = w.readframes(min(n, int(sr * scan)))
    w.close()
    a = array.array("h")
    a.frombytes(raw)
    if len(a) < sr // 20:
        return False
    if ch > 1:
        a = a[::ch]
    win = max(1, int(sr * window))
    runs, cur = [], []
    for i in range(len(a) // win):
        blk = a[i * win:(i + 1) * win]
        if max(max(blk), -min(blk)) / 32768.0 < silence:
            cur.append(i)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    need = max(1, int(need_ms / (window * 1000)))
    runs = [r for r in runs if len(r) >= need]
    if not runs:
        return False
    end = (runs[-1][-1] + 1) * win / sr
    if end <= 0.03:
        return False
    subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-ss", f"{end:.3f}", "-i", str(src),
                    "-c:a", "pcm_s16le", str(dest)], check=True)
    print(f"   ✂ {src.name}: 去掉开头 {end*1000:.0f}ms 残响")
    return True


def build_concat(files: list[pathlib.Path], gap: float, target: float | None,
                 dest: pathlib.Path, lead: float = 0.0, trim: bool = True):
    """拼接各段：先逐段去开头残响 → 段间插 gap → 开头补 lead 秒静音
    → 对齐 target → 首尾淡入淡出（防 click）。"""
    dest = dest.resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = (dest.parent / "_concat").resolve()
    tmp.mkdir(exist_ok=True)

    # 统一成 44.1k 双声道，顺手去掉开头残响
    norm = []
    for i, f in enumerate(files):
        o = tmp / f"n{i:02d}.wav"
        subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-i", str(f.resolve()),
                        "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(o)], check=True)
        if trim:
            t = tmp / f"t{i:02d}.wav"
            if trim_head(o, t):
                o = t
        norm.append(o)

    # ffmpeg 的 concat 会按 list.txt 所在目录解析相对路径，这里统一给绝对路径
    if gap <= 0:
        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in norm), encoding="utf-8")
        subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-f", "concat", "-safe", "0",
                        "-i", str(lst), "-c:a", "pcm_s16le", str(dest)], check=True)
    else:
        sil = tmp / "sil.wav"
        subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-f", "lavfi",
                        "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{gap:.3f}",
                        "-c:a", "pcm_s16le", str(sil)], check=True)
        lst = tmp / "list.txt"
        parts = []
        for i, p in enumerate(norm):
            parts.append(f"file '{p.as_posix()}'")
            if i < len(norm) - 1:
                parts.append(f"file '{sil.as_posix()}'")
        lst.write_text("\n".join(parts) + "\n", encoding="utf-8")
        subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-f", "concat", "-safe", "0",
                        "-i", str(lst), "-c:a", "pcm_s16le", str(dest)], check=True)

    # 开头补静音：给人「站稳、抬眼」的准备时间，别一上来就念
    if lead > 0:
        sil = tmp / "lead.wav"
        subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-f", "lavfi",
                        "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{lead:.3f}",
                        "-c:a", "pcm_s16le", str(sil)], check=True)
        lst = tmp / "list_lead.txt"
        lst.write_text(f"file '{sil.as_posix()}'\nfile '{dest.as_posix()}'\n", encoding="utf-8")
        subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-f", "concat", "-safe", "0",
                        "-i", str(lst), "-c:a", "pcm_s16le", str(tmp / "leaded.wav")], check=True)
        shutil.move(str(tmp / "leaded.wav"), dest)

    if target:
        cur = dur(dest)
        if cur < target - 0.01:
            pad = target - cur
            subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-i", str(dest),
                            "-af", f"apad=pad_dur={pad:.3f}",
                            "-c:a", "pcm_s16le", str(tmp / "padded.wav")], check=True)
            shutil.move(str(tmp / "padded.wav"), dest)
            if pad / target > 0.15:
                print(f"⚠ 尾部补了 {pad:.1f}s 静音（占目标 {pad/target*100:.0f}%）。"
                      f"台词偏少，H3 生成的后半段会没话讲——建议加字数或放慢语速。")
        elif cur > target + 0.01:
            cut = cur - target
            subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-i", str(dest),
                            "-t", f"{target:.3f}", "-c:a", "pcm_s16le",
                            str(tmp / "cut.wav")], check=True)
            shutil.move(str(tmp / "cut.wav"), dest)
            print(f"⚠ 砍掉了末尾 {cut:.1f}s。台词偏多，H3 会把后半句吃掉——建议减字数。")

    # 首尾各做一次极短淡入淡出，避免 PCM 波形硬切造成 click
    d = dur(dest)
    if d > 0.06:
        subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-i", str(dest),
                        "-af", f"afade=t=in:st=0:d=0.008,afade=t=out:st={d - 0.03:.3f}:d=0.025",
                        "-c:a", "pcm_s16le", str(tmp / "fade.wav")], check=True)
        shutil.move(str(tmp / "fade.wav"), dest)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True)
    ap.add_argument("--out", required=True, help="输出 wav")
    ap.add_argument("--voice", default="", help="音色/语速描述（写进音色描述里）")
    ap.add_argument("--reference", default="", help="克隆用的参考音频")
    ap.add_argument("--prompt-text", default="", help="参考音频的原文（克隆用）")
    ap.add_argument("--auto-prompt", action="store_true",
                    help="不给 --prompt-text 时，用本地 whisper 自动转写参考音频")
    ap.add_argument("--cfg", type=float, default=2.0)
    ap.add_argument("--timesteps", type=int, default=10)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--gap", type=float, default=0.0, help="段间静音秒数")
    ap.add_argument("--target", type=float, default=None, help="目标总长（精确对齐到 H3 段长）")
    ap.add_argument("--lead", type=float, default=0.0,
                    help="开头补多少秒静音（给出镜人物留准备时间，常用 1.2–1.8）")
    ap.add_argument("--no-trim", action="store_true",
                    help="不自动去掉开头那截「上一句尾音残响」（默认去掉）")
    ap.add_argument("--offload", default="end", choices=["end", "always", "never"],
                    help="end=全部跑完清一次（默认，最快）；always=每段卸；never=不清")
    ap.add_argument("--keep-tmp", action="store_true")
    a = ap.parse_args()

    segs = parse_script(a.script)
    if not segs:
        sys.exit("剧本是空的")
    mode = "clone" if a.reference else "tts"
    print(f"共 {len(segs)} 段 | 模式 {mode} | 显存策略 {a.offload}")

    cfg = {
        "mode": mode, "voice": a.voice, "cfg_value": a.cfg, "timesteps": a.timesteps,
        "max_tokens": a.max_tokens, "seed": a.seed,
        "force_offload": a.offload == "always",
    }
    if mode == "clone":
        cfg["ref_audio"] = prepare_audio(a.reference)
        prompt_text = a.prompt_text
        if not prompt_text and a.auto_prompt:
            print("转写参考音频（whisper）...", flush=True)
            prompt_text = transcribe_ref(a.reference)
            if prompt_text:
                print(f"  原文: {prompt_text[:60]}{'...' if len(prompt_text) > 60 else ''}")
        cfg["prompt_text"] = prompt_text
        if prompt_text:
            print("克隆模式: ultimate（参考音 + 原文）")
        else:
            print("克隆模式: controllable（只用参考音，建议加 --auto-prompt 效果更好）")
        print(f"参考音频 → ComfyUI input/{cfg['ref_audio']}")

    files = []
    t_all = time.time()
    for i, text in enumerate(segs, 1):
        n = len(text)
        print(f"\n[{i}/{len(segs)}] {n} 字: {text[:28]}{'...' if n > 28 else ''}", flush=True)
        t0 = time.time()
        f = run_one(text, cfg, f"{i:02d}_{int(time.time())}")
        d = dur(f)
        print(f"   → {f.name}  {d:.2f}s  ({d and n/d:.2f} 字/秒)  耗时 {time.time()-t0:.0f}s", flush=True)
        files.append(f)

    print(f"\n全部生成完，用时 {time.time()-t_all:.0f}s")

    # 统一清理一次显存
    if a.offload != "never":
        try:
            from vram_free import free_vram
            free_vram(wait=True)
        except Exception as e:
            print(f"（显存清理跳过：{e}）")

    outpath = pathlib.Path(a.out)
    build_concat(files, a.gap, a.target, outpath, lead=a.lead, trim=not a.no_trim)
    total = dur(outpath)
    chars = sum(len(s) for s in segs)
    print(f"\n输出: {outpath}  {total:.3f}s   {chars} 字   {chars/total:.2f} 字/秒" if total else f"\n输出: {outpath}")

    if a.target:
        print(f"已对齐到目标 {a.target:g}s")
    else:
        print("\n→ 喂给 H3 时，chunks × chunk_seconds 必须等于这个时长：")
        for cs in (5, 8, 10, 12, 15):
            n = round(total / cs)
            if 1 <= n <= 16 and abs(n * cs - total) <= 0.35:
                print(f"   约 {n} 段 × {cs}s = {n*cs}s  ✅")

    if not a.keep_tmp:
        shutil.rmtree(pathlib.Path(__file__).resolve().parent / "out" / "_tts_tmp", ignore_errors=True)
