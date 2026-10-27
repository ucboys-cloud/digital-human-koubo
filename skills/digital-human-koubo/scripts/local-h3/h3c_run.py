"""Continuum 长视频口播：按原工作流（V3.9 Turbo）跑分块生成。

基底 continuum_base.json 由 w2api.py 从用户工作流**忠实转出**（含 6 个 LoRA、旁路节点已剔除），
本脚本只改「每次任务必须变的几项」，其余一律沿用工作流原值：
  1. #188 sequence_prompt  → 分块 Continuum 提示词
  2. #312 采样器           → 分块数、每块秒数、竖版尺寸、seed、Run 名
  3. 形象图                → first_frame + reference_image_1（自建 H3EasyLoadImage）
  4. #191 SaveVideo        → 输出前缀
  5. 驱动音频（可选）       → 自建 LoadAudio 接 driving_audio
模型 / LoRA / 采样器 / 步数 / 调度器 / 注意力后端 **默认全部继承工作流**，
只有显式传 --unet / --lora / --steps / --scheduler 才覆盖。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

import os

COMFY = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
INPUT_DIR = pathlib.Path(os.environ.get(
    "COMFY_INPUT", r"D:\ComfyUI_windows_portable\ComfyUI\input"))
HERE = pathlib.Path(__file__).parent
BASE = HERE / "continuum_base.json"
UNET_REF2VA = "Minimax-h3_Singularity_ref2va_Pruned_v1.3_int8.safetensors"

N_UNET = "147"
N_PROMPT = "188"
N_SAMPLER = "312"
N_SAVE = "191"
N_REFIMGS = "348"
N_SCHED = "153"   # BasicScheduler
N_REFAUDIO = "331"
N_LORA = "362"           # Power Lora Loader (rgthree)：lora_1… 是动态输入项
N_DECODE = "344"         # H3DecodeCacheHelper：解码缓存的磁盘预算
N_FIRST = "first_img"    # 自建 H3EasyLoadImage（基底里不再复用示例素材节点）
N_LAST = "last_img"

# 旧基底里存在、新基底已按「旁路即剔除」清理掉的节点；保留 pop 以防旧基底再被用到
DROP_NODES = ["313", "314", "316", "349", "350", "351", "319", "355", "320",
              "315", "284", "249", "321"]

# 解码缓存：插件把每段解码结果写进 %TEMP%\h3-decode-cache-<pid>-*，
# 一次出片新建一份、跑完不清（owner pid 还活着，它自己判定为"在用"）。
# 实测堆 7 份 = 43GB 全落在 C 盘。这里只做两件事：调小单份预算 + 跑完清旧的。
DEFAULT_DISK_CACHE_GB = 2


def decode_cache_parents() -> list[pathlib.Path]:
    """所有可能藏着 h3-decode-cache-* 的父目录（去重）。

    插件支持三处来源，优先级：显式 temp_parent > 环境变量 > 插件 Temporary Storage > 系统 TEMP。
    官方 API 是 GET /h3-continuum/storage/status，其中 current=true 的 decode 根即为当前生效位置。
    """
    import tempfile as _tempfile

    parents: list[pathlib.Path] = []
    seen: set[str] = set()

    def add(p: str | pathlib.Path | None) -> None:
        if not p:
            return
        try:
            q = pathlib.Path(p).expanduser()
        except (OSError, ValueError):
            return
        key = str(q).lower()
        if key in seen:
            return
        seen.add(key)
        parents.append(q)

    add(os.environ.get("H3_DECODE_CACHE_TEMP_DIR"))
    try:
        st = json.loads(urllib.request.urlopen(
            f"{COMFY}/h3-continuum/storage/status", timeout=10).read() or b"{}")
        for r in st.get("roots") or []:
            if r.get("kind") == "decode" and r.get("current"):
                add(r.get("path"))
    except Exception:
        pass  # 插件没装/接口不在，退回系统 TEMP
    add(_tempfile.gettempdir())
    return parents


def purge_decode_cache(keep_newest: int = 1, min_age_min: float = 5.0,
                       quiet: bool = False) -> tuple[int, float]:
    """清理 h3-decode-cache-*，只删「非最新」且「闲置超过 min_age_min 分钟」的。

    会同时扫系统 TEMP 与插件 Temporary Storage 配置的 decode 根（可能已搬到别的盘）。
    保守策略：留最新一份（可能正被 ComfyUI 内存索引引用），被占用的文件跳过不报错。
    """
    import shutil as _shutil
    import time as _time

    dirs: list[pathlib.Path] = []
    for root in decode_cache_parents():
        if not root.is_dir():
            continue
        dirs += [d for d in root.glob("h3-decode-cache-*")
                 if d.is_dir() and not d.is_symlink()]
    if len(dirs) <= keep_newest:
        return 0, 0.0
    dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    now = _time.time()
    n, freed = 0, 0.0
    for d in dirs[keep_newest:]:
        try:
            age_min = (now - d.stat().st_mtime) / 60
            if age_min < min_age_min:
                continue
            size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            _shutil.rmtree(d)
            n += 1
            freed += size
        except OSError:
            continue  # 有文件被占用就整个跳过，不硬删
    if n and not quiet:
        print(f"解码缓存：清理 {n} 个旧目录，释放 {freed / 1073741824:.1f} GB")
    return n, freed


def stage(path: str, sub: str = "kotalk") -> str:
    src = pathlib.Path(path)
    if not src.exists():
        sys.exit(f"素材不存在: {src}")
    dst_dir = INPUT_DIR / sub
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    if not dst.exists() or dst.stat().st_size != src.stat().st_size:
        shutil.copy2(src, dst)
    return f"{sub}/{src.name}"


def _exe(name: str) -> str:
    """ffmpeg/ffprobe：先查 PATH，再查 FFMPEG_DIR，最后回落本机工具目录。"""
    found = shutil.which(name)
    if found:
        return found
    for d in (os.environ.get("FFMPEG_DIR"), r"C:\ffmpeg\bin"):
        if d and (pathlib.Path(d) / f"{name}.exe").exists():
            return str(pathlib.Path(d) / f"{name}.exe")
    sys.exit(f"找不到 {name}：装 ffmpeg，或设环境变量 FFMPEG_DIR 指向 bin 目录")


def prepare_drive_audio(path: str) -> str:
    """现成音频 → 44.1k 双声道 wav 落到 ComfyUI input，返回相对路径（给 LoadAudio）。"""
    src = pathlib.Path(path)
    if not src.exists():
        sys.exit(f"驱动音频不存在: {src}")
    dst_dir = INPUT_DIR / "kotalk"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / f"{src.stem}_drive.wav"
    subprocess.run([_exe("ffmpeg"), "-y", "-v", "error", "-i", str(src),
                    "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(dst)], check=True)
    return f"kotalk/{dst.name}"


def audio_seconds(path: pathlib.Path) -> float:
    out = subprocess.run([_exe("ffprobe"), "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def build(image: str, prompt: str, chunks: int, seconds: float, megapixels: float | None,
          aspect: str | None, seed: int, prefix: str, run_name: str,
          unet: str | None = None, end_image: str = "",
          steps: int | None = None, scheduler: str | None = None,
          width: int | None = None, height: int | None = None,
          size_source: str | None = None, preset: str | None = None,
          drive_audio: str = "", video_ref_size: str | None = None,
          loras: list[tuple[str, float]] | None = None,
          prompt_mode: str | None = None,
          first_frame: bool = False,
          disk_cache_gb: int | None = DEFAULT_DISK_CACHE_GB) -> dict:
    """未显式传入的参数一律沿用工作流自身的值（保持与用户工作流一致）。"""
    p = json.loads(BASE.read_text(encoding="utf-8"))

    if unet:  # 不传就继承工作流里的 UNET
        p[N_UNET]["inputs"]["unet_name"] = unet
    p[N_PROMPT]["inputs"]["value"] = prompt

    s = p[N_SAMPLER]["inputs"]
    s.update({
        "chunks": int(chunks),
        "chunk_seconds": float(seconds),
        "base_seed": int(seed),
        "generation_mode": "Full Run",
        "run_storage": "Off",
        "diagnostics": "Basic",
        "run_name": run_name,
        "project_id": str(uuid.uuid4()),
    })
    # prompt_mode 默认继承工作流（用户是 Auto）。Auto 按行序检测：正文里出现 [Chunk N] 即判 Timeline；
    # 提示词里若没有 [Chunk N] 头，Auto 会退化成 Fixed（所有块共用一块），所以核对一下。
    if prompt_mode:
        s["prompt_mode"] = prompt_mode
    if s.get("prompt_mode") == "Auto" and not re.search(r"^\s*\[\s*(?:chunk|clip)\s*\d+\s*\]\s*$",
                                                        prompt, re.I | re.M):
        print("⚠ 提示词里没有 [Chunk N] 头，Auto 会按 Fixed 处理（每块共用同一段）——请检查模板")
    # 尺寸：全部写进 H3ContinuumSamplerV39（#312）自身的字段，别处不设分辨率
    if width and height:
        s["size_source"] = size_source or "Manual"
        s["width"], s["height"] = int(width), int(height)
        # preset/custom_mp 在 Manual 下不参与计算，但要让节点显示的数字跟实际一致
        s["preset"] = "Custom"
        s["custom_mp"] = round(int(width) * int(height) / 1_000_000, 2)
    if size_source:
        s["size_source"] = size_source
    if preset:
        s["preset"] = preset
    if megapixels and not (width and height):
        s["preset"] = "Custom"
        s["custom_mp"] = float(megapixels)
        if not size_source:
            s["size_source"] = "First Image"
    if aspect:
        s["aspect"] = aspect
    # 续拍引导帧尺寸：Efficient 0.4MP 会让每块都从低清引导里"编"细节，长片越跑越糊
    if video_ref_size:
        s["video_reference_size"] = video_ref_size

    # LoRA：rgthree 的 lora 是动态输入项（lora_1/lora_2…），w2api 转换时会整个丢掉，
    # 于是脚本跑的是「裸模型」——步数再对也达不到该有的质感。这里显式写回去。
    if loras is not None:
        li = p[N_LORA]["inputs"]
        for k in [k for k in li if k.startswith("lora_")]:
            del li[k]
        for i, (name, st) in enumerate(loras, 1):
            li[f"lora_{i}"] = {"on": True, "lora": name,
                               "strength": float(st), "strengthTwo": None}

    # 解码缓存磁盘预算：工作流出厂是 8GB/份，一份一次出片，堆起来能吃掉几十 GB C 盘。
    # 只在构建时压小，不改基底文件（基底必须与用户工作流一致）。
    if disk_cache_gb is not None and N_DECODE in p:
        p[N_DECODE]["inputs"]["disk_budget_gb"] = int(disk_cache_gb)

    p[N_SAVE]["inputs"]["filename_prefix"] = prefix

    sch = p[N_SCHED]["inputs"]
    if steps:
        sch["steps"] = int(steps)
    if scheduler:
        sch["scheduler"] = scheduler

    # 形象图：默认只做 reference_image_1（属性参考），**不接 first_frame**。
    # 接了 first_frame = 让模型把那帧当第 0 帧输出 → 开头 0~0.5s 就是参考图本身（NCC 0.99），
    # 这是「一开头闪一下原图」的根因。ref2va 的规矩是只锚身份、不锁首帧。
    p[N_FIRST] = {"class_type": "H3EasyLoadImage",
                  "inputs": {"image": stage(image)},
                  "_meta": {"title": "形象图（kotalk）"}}

    ref = p[N_REFIMGS]["inputs"]
    for k in [k for k in ref if k.startswith("reference_image_")]:
        del ref[k]
    ref["reference_image_1"] = [N_FIRST, 0]
    ref["reference_use"] = "All chunks"
    ref["reference_r1_chunks"] = ",".join(str(i + 1) for i in range(int(chunks)))

    if first_frame:
        s["first_frame"] = [N_FIRST, 0]
    else:
        s.pop("first_frame", None)

    if end_image:
        p[N_LAST] = {"class_type": "H3EasyLoadImage", "inputs": {"image": stage(end_image)}}
        s["last_frame"] = [N_LAST, 0]

    # 断掉与原示例无关的输入
    for k in ("reference_video_1", "last_frame"):
        s.pop(k, None)
    if not end_image:
        s.pop("last_frame", None)

    for nid in DROP_NODES:
        p.pop(nid, None)

    # 音频直驱：给一段现成音频，口型与节奏跟随它（driving_audio，不是 reference_audio 音色参考）
    if drive_audio:
        rel = prepare_drive_audio(drive_audio)
        p["drive_audio"] = {"class_type": "LoadAudio", "inputs": {"audio": rel}}
        s["driving_audio"] = ["drive_audio", 0]
        target = float(chunks) * float(seconds)
        dur = audio_seconds(pathlib.Path(INPUT_DIR) / rel)
        flag = "✓ 吻合" if abs(dur - target) <= 0.35 else "⚠ 与目标时长不一致"
        print(f"驱动音频 {rel}：{dur:.2f}s / 目标 {target:g}s  {flag}")
        if abs(dur - target) > 0.35:
            n = max(1, min(16, round(dur / float(seconds))))
            alt = dur / n
            hint = (f"chunks={n} × chunk_seconds={alt:.1f}s = {n * alt:.1f}s"
                    if 4.0 <= alt <= 30.0 else
                    f"chunks={n} × {seconds:g}s = {n * float(seconds):g}s（最接近，仍差 "
                    f"{abs(n * float(seconds) - dur):.1f}s）")
            print(f"  → 按音频实际 {dur:.2f}s 改采样器：{hint}；"
                  f"不改就会被截断或后段无声")
    else:
        s.pop("driving_audio", None)
    return p


def post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        COMFY + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    body = urllib.request.urlopen(req, timeout=180).read().decode()
    return json.loads(body) if body.strip() else {}


def submit(prompt: dict) -> str:
    r = post("/prompt", {"prompt": prompt, "client_id": uuid.uuid4().hex})
    if r.get("node_errors"):
        print("节点报错:", json.dumps(r["node_errors"], ensure_ascii=False)[:3000])
        sys.exit(1)
    return r["prompt_id"]


def wait(pid: str, timeout: float = 14400) -> dict:
    t0 = time.time()
    last = 0
    while time.time() - t0 < timeout:
        d = json.loads(urllib.request.urlopen(f"{COMFY}/history/{pid}", timeout=30).read() or b"{}")
        if d:
            v = list(d.values())[0]
            st = v.get("status", {})
            for m in st.get("messages", []):
                if m[0] == "execution_error":
                    e = m[1]
                    print("\n执行失败:", e.get("node_id"), e.get("node_type"))
                    print("异常:", str(e.get("exception_message"))[:2000])
                    sys.exit(2)
            if st.get("completed"):
                print()
                return v
        el = int(time.time() - t0)
        if el - last >= 30:
            print(f"  ...{el}s", flush=True)
            last = el
        time.sleep(5)
    sys.exit("超时")


def collect(v: dict, dest: pathlib.Path) -> pathlib.Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cands = []
    for _nid, o in (v.get("outputs") or {}).items():
        for key in ("gifs", "videos", "video", "images", "files"):
            for it in (o.get(key) or []):
                if not isinstance(it, dict):
                    continue
                fn = str(it.get("filename", ""))
                if fn.lower().endswith((".mp4", ".webm", ".mov")):
                    cands.append(it)
    if not cands:
        print("输出记录:", json.dumps(v.get("outputs"), ensure_ascii=False)[:1200])
        sys.exit("没找到视频输出")
    it = cands[0]
    url = (f"{COMFY}/view?filename={urllib.parse.quote(it['filename'])}"
           f"&subfolder={urllib.parse.quote(it.get('subfolder') or '')}"
           f"&type={it.get('type', 'output')}")
    dest.write_bytes(urllib.request.urlopen(url, timeout=1800).read())
    return dest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--end-image", default="")
    ap.add_argument("--text", default="")
    ap.add_argument("--text-file", default="")
    ap.add_argument("--chunks", type=int, default=4)
    ap.add_argument("--seconds", type=float, default=10)
    ap.add_argument("--megapixels", type=float, default=None)
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    ap.add_argument("--aspect", default=None)
    ap.add_argument("--size-source", default=None,
                    choices=["First Image", "Manual", "Legacy Aspect"])
    ap.add_argument("--preset", default=None,
                    choices=["draft", "balanced", "native", "custom"],
                    help="draft=0.30MP / balanced=0.60MP / native=768 / custom=配 --megapixels")
    ap.add_argument("--drive-audio", default="",
                    help="现成音频直接驱动口型（driving_audio），不是音色参考")
    ap.add_argument("--no-dialogue", action="store_true",
                    help="配 --drive-audio 用：删掉 prompt 里的 <d> 台词块，避免模型自己再念一遍")
    ap.add_argument("--seed", type=int, default=778899123456)
    ap.add_argument("--prefix", default="koubo/long")
    ap.add_argument("--run-name", default="")
    ap.add_argument("--unet", default=None,
                    help="覆盖 UNET 模型；不传则沿用工作流（默认就是工作流里那个模型）")
    ap.add_argument("--steps", type=int, default=None, help="不传则沿用工作流自身步数")
    ap.add_argument("--video-ref-size", default=None,
                    choices=["Efficient - 0.4 MP", "Balanced - 0.6 MP", "Match Output"],
                    help="续拍引导帧尺寸。长片一律 Match Output，否则越到后面越糊（默认沿用工作流）")
    ap.add_argument("--lora", action="append", default=None, metavar="NAME:STRENGTH",
                    help='临时替换 LoRA，可重复（基底已带工作流那 6 个，一般不用传）')
    ap.add_argument("--first-frame", action="store_true",
                    help="把参考图同时接成 first_frame。默认不接——接了开头 0~0.5s 就是原图静止帧（闪一下参考图）")
    ap.add_argument("--prompt-mode", default=None,
                    choices=["Auto", "Fixed", "List", "Timeline"],
                    help="不传则沿用工作流（Auto 会按 [Chunk N] 自动判为 Timeline）")
    ap.add_argument("--disk-cache-gb", type=int, default=DEFAULT_DISK_CACHE_GB,
                    help=f"解码缓存的磁盘预算 GB/次（工作流出厂 8，默认压到 {DEFAULT_DISK_CACHE_GB}）。传 0 = 用工作流原值")
    ap.add_argument("--no-cache-purge", action="store_true",
                    help="出片后不清 %%TEMP%% 里的旧 h3-decode-cache 目录")
    ap.add_argument("--scheduler", default=None, help="不传则沿用工作流自身调度器")
    ap.add_argument("--out", default="")
    ap.add_argument("--no-free", action="store_true",
                    help="提交前不清理显存（默认会清，避免 TTS 残留挤占）")
    ap.add_argument("--free-after", action="store_true",
                    help="出片后也清一次显存（连续只跑一条时用）")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    text = a.text
    if a.text_file:
        text = pathlib.Path(a.text_file).read_text(encoding="utf-8").strip()
    if not text:
        sys.exit("需要 --text 或 --text-file")

    PRESETS = {"draft": "Draft — 0.30 MP", "balanced": "Balanced — 0.60 MP",
               "native": "Native 768", "custom": "Custom"}
    preset = PRESETS.get(a.preset, a.preset)

    loras = None
    if a.lora is not None:
        loras = []
        for item in a.lora:
            name, _, st = item.rpartition(":")
            if not name:
                name, st = item, "1.0"
            loras.append((name.replace("/", "\\"), float(st)))

    if a.no_dialogue:
        text = re.sub(r"<d>\s*\[[^\]]*\]\s*.*?</d>\s*", "", text, flags=re.S)
        print("已删掉 <d> 台词块（口型交给驱动音频）")

    prompt = build(a.image, text, a.chunks, a.seconds, a.megapixels, a.aspect,
                   a.seed, a.prefix, a.run_name or f"koubo_{int(time.time())}",
                   a.unet, a.end_image, a.steps, a.scheduler,
                   a.width, a.height, a.size_source, preset, a.drive_audio,
                   a.video_ref_size, loras, a.prompt_mode, a.first_frame,
                   a.disk_cache_gb or None)
    print(f"节点 {len(prompt)} 个")
    print("—— 模型链路（继承自工作流）——")
    print(f"  UNET   = {prompt[N_UNET]['inputs']['unet_name']}")
    print(f"  CLIP   = {prompt['142']['inputs']['clip_name']}")
    print(f"  VAE    = {prompt['135']['inputs']['vae_name']} + {prompt['136']['inputs']['vae_name']}")
    _chain = " → ".join(f"#{k} {prompt[k]['class_type'].replace(' (rgthree)', '')}"
                        for k in ("361", "240", "362", "363", "364", "365") if k in prompt)
    print(f"  模型链 = {_chain}")
    print(f"  注意力 = {prompt['363']['inputs'].get('attention', '?')}"
          f" / {prompt['364']['inputs'].get('selection', '?')}")
    _s = prompt[N_SAMPLER]["inputs"]
    print("—— #312 H3ContinuumSamplerV39 设置 ——")
    print(f"  段数 chunks        = {_s['chunks']}   每段 chunk_seconds = {_s['chunk_seconds']:g}s"
          f"   合计 = {_s['chunks'] * _s['chunk_seconds']:g}s")
    print(f"  尺寸 size_source   = {_s['size_source']}"
          + (f"   {_s['width']}×{_s['height']}" if _s['size_source'] == "Manual"
             else f"   preset={_s['preset']} custom_mp={_s['custom_mp']}"))
    print(f"  比例 aspect        = {_s['aspect']}   连贯 continuity = {_s['continuity']}")
    print(f"  引导帧 video_guide = {_s.get('video_reference_size', '?')}"
          f"   参考图 reference = {_s.get('reference_size', '?')}")
    _lo = [k for k in prompt.get(N_LORA, {}).get("inputs", {}) if k.startswith("lora_")]
    if _lo:
        print(f"  LoRA {len(_lo)} 个: " + " | ".join(
            f"{prompt[N_LORA]['inputs'][k]['lora'].split(chr(92))[-1]}@{prompt[N_LORA]['inputs'][k]['strength']}"
            for k in sorted(_lo)))
    else:
        print("  LoRA 0 个（裸模型运行）")
    print(f"  提示词 prompt_mode = {_s['prompt_mode']}   采样 steps = {prompt[N_SCHED]['inputs']['steps']}"
          f" / {prompt[N_SCHED]['inputs']['scheduler']}")
    print(f"  口型来源           = " + (f"驱动音频 {_s['driving_audio']}"
                                     if _s.get("driving_audio") else "模型自带 TTS（<d> 台词）"))
    print(f"  首帧 first_frame   = " + ("接参考图（开头会闪原图）" if _s.get("first_frame")
                                     else "不接（只作属性参考，开场直接是生成画面）"))
    if N_DECODE in prompt:
        _where = " | ".join(str(p) for p in decode_cache_parents()[:2]) or "?"
        print(f"  解码缓存 budget    = {prompt[N_DECODE]['inputs'].get('disk_budget_gb')} GB"
              f"\n  缓存位置           = {_where}")

    if a.dry_run:
        try:
            r = post("/prompt", {"prompt": prompt, "client_id": "dry"})
            pid = r["prompt_id"]
            print("校验通过，已入队:", pid)
            post("/queue", {"delete": [pid]})
            print("已撤出队列")
        except urllib.error.HTTPError as e:
            print("HTTP", e.code, e.read().decode()[:3000])
        sys.exit()

    if not a.no_free:
        # TTS（VoxCPM2 等）跑完常留 5-8GB 不释放，H3 要 20GB+，
        # 不清干净会逼 ComfyUI 反复在 CPU/GPU 之间搬权重，反而变慢。
        try:
            from vram_free import free_vram
            free_vram(wait=True)
        except Exception as e:
            print(f"（显存预清理跳过：{e}）")

    pid = submit(prompt)
    print("已入队:", pid, flush=True)
    v = wait(pid)
    out = collect(v, pathlib.Path(a.out or HERE / "out" / "long.mp4"))
    print("完成:", out)

    if not a.no_cache_purge:
        try:
            purge_decode_cache()
        except Exception as e:
            print(f"（解码缓存清理跳过：{e}）")

    if a.free_after:
        try:
            from vram_free import free_vram
            free_vram(quiet=False)
        except Exception as e:
            print(f"（出片后清理跳过：{e}）")
