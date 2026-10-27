"""释放 ComfyUI 占用的显存（VoxCPM2 / TTS 跑完后残留的那种）。

ComfyUI 的 /free 接口能卸载所有已加载模型并清空 CUDA 缓存，
实测可退 19GB 以上。TTS 节点默认 force_offload=False，模型会一直挂在显存里，
所以跑完 TTS 必须手动调一次这个。

用法：
    python vram_free.py              # 立即释放
    python vram_free.py --wait       # 等队列空闲后再释放（不打断正在跑的任务）
    python vram_free.py --quiet      # 只输出结果，不打印过程

也可以在别的脚本里 import：
    from vram_free import free_vram
    free_vram(wait=True)
"""
import argparse
import json
import sys
import time
import urllib.request

COMFY = "http://127.0.0.1:8188"


def _get(path):
    with urllib.request.urlopen(COMFY + path, timeout=30) as r:
        return json.load(r)


def _post(path, payload=None):
    data = json.dumps(payload or {}).encode()
    req = urllib.request.Request(COMFY + path, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}


def vram() -> tuple[float, float]:
    """返回 (空闲GB, 总量GB)。"""
    dev = _get("/system_stats")["devices"][0]
    return dev["vram_free"] / 1e9, dev["vram_total"] / 1e9


def queue_len() -> int:
    q = _get("/queue")
    return len(q.get("queue_running", [])) + len(q.get("queue_pending", []))


def free_vram(wait: bool = False, quiet: bool = False, timeout: float = 1800) -> float:
    """释放显存，返回释放后空闲 GB。wait=True 时先等队列跑完。"""
    log = (lambda *a: None) if quiet else print

    if wait:
        t0 = time.time()
        n = queue_len()
        if n:
            log(f"队列里还有 {n} 个任务，等它跑完再释放 ...")
        while queue_len() and time.time() - t0 < timeout:
            time.sleep(5)
        if queue_len():
            log("⚠ 等待超时，仍然释放（可能打断任务）")

    before, total = vram()
    _post("/free", {"unload_models": True, "free_memory": True})
    # 给 empty_cache 一点时间真正归还给驱动
    for _ in range(10):
        time.sleep(0.5)
        after, _t = vram()
        if after - before < 0.05:
            break
    log(f"显存：已用 {total - before:.2f} GB → {total - after:.2f} GB"
        f"（释放 {after - before:.2f} GB，现空闲 {after:.2f} GB）")
    return after


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--wait", action="store_true", help="等队列空闲再释放")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    try:
        free_vram(wait=a.wait, quiet=a.quiet)
    except Exception as e:
        sys.exit(f"释放失败（ComfyUI 没在跑？）：{e}")
