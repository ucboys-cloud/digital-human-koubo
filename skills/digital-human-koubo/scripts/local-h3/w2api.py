"""UI 工作流 → API prompt 通用转换器（Continuum / 原生工作流通用）。

相比手写 API，这里不做任何精简：节点、连线、参数全部原样搬运。

关键规则（踩过的坑）：
1. **被连线占用的 widget 不会出现在 widgets_values 里** —— 例如 H3ContinuumSamplerV39 的
   sequence_prompt 一旦接上 PrimitiveStringMultiline，UI 就不序列化它。映射前必须剔除，
   否则后面 30 个参数全部错位一格。
2. seed / base_seed / noise_seed 后面紧跟 control_after_generate（fixed/randomize…），要跳过。
3. 多出来的尾部 UI 值（上传按钮等）直接忽略。
4. 动态下拉框（COMFY_DYNAMICCOMBO_V3）的子参数在 API 里要点号全名，如 selection.tau。
5. rgthree Power Lora Loader 要转成 lora_1 / lora_2 … 结构。
"""
from __future__ import annotations

import argparse
import json
import pathlib

VIRTUAL = {"Note", "MarkdownNote", "Reroute", "SetNode", "GetNode", "PrimitiveNode",
           "Fast Groups Bypasser (rgthree)", "Fast Groups Muter (rgthree)"}
WIDGET_T = {"INT", "FLOAT", "STRING", "BOOLEAN", "COMBO"}
CTRL = {"fixed", "increment", "decrement", "randomize"}
SEEDS = {"seed", "noise_seed", "base_seed"}


def widget_defs(oi, ntype):
    """按 object_info 声明顺序返回 [(name, type)]，含动态下拉框本体。"""
    info = oi.get(ntype)
    if not info:
        return []
    out = []
    for sec in ("required", "optional"):
        for k, v in (info.get("input", {}).get(sec) or {}).items():
            t0 = v[0] if v else None
            if isinstance(t0, list) or t0 in WIDGET_T or t0 == "COMFY_DYNAMICCOMBO_V3":
                out.append((k, t0 if isinstance(t0, str) else "enum"))
    return out


def dynamic_children(oi, ntype, field, key):
    v = (oi[ntype]["input"]["required"].get(field) or [None, {}])
    if v[0] != "COMFY_DYNAMICCOMBO_V3":
        return []
    for opt in (v[1].get("options") or []):
        if opt.get("key") == key:
            names = []
            for sec in ("required", "optional"):
                for k in ((opt.get("inputs") or {}).get(sec) or {}):
                    names.append(f"{field}.{k}")
            return names
    return []


class Converter:
    def __init__(self, wf, oi):
        self.wf = wf
        self.oi = oi
        self.N = {n["id"]: n for n in wf["nodes"]}
        self.L = {l[0]: l for l in wf["links"]}
        # mode: 0=正常 2=静音(不执行,输出为空) 4=旁路(直通同类型输入)
        self.mute = {n["id"] for n in wf["nodes"] if n.get("mode") == 2}
        self.bypass = {n["id"] for n in wf["nodes"] if n.get("mode") == 4}
        self.sets = {}
        for n in wf["nodes"]:
            if n["type"] == "SetNode":
                name = (n.get("widgets_values") or [""])[0]
                for inp in n.get("inputs") or []:
                    if inp.get("link") is not None:
                        self.sets[name] = inp["link"]

    def passthrough(self, node, want_type, depth=0):
        """旁路节点的某个输出：找同类型的已连输入当直通源；找不到就返回 None。"""
        for inp in (node.get("inputs") or []):
            if inp.get("link") is not None and inp.get("type") == want_type:
                return self.resolve(inp["link"], depth + 1)
        return None

    def resolve(self, link_id, depth=0):
        if depth > 60:
            raise RuntimeError("连线解析层数过深，可能成环")
        l = self.L.get(link_id)
        if not l:
            return None
        _, origin, oslot, _t, _ts, ltype = l
        node = self.N.get(origin)
        if node is None:
            return None
        if origin in self.mute:
            return None
        if node["type"] == "Reroute":
            ins = node.get("inputs") or []
            return self.resolve(ins[0]["link"], depth + 1) if ins and ins[0].get("link") is not None else None
        if node["type"] == "GetNode":
            name = (node.get("widgets_values") or [""])[0]
            up = self.sets.get(name)
            if up is None:
                raise RuntimeError(f"GetNode「{name}」找不到对应 SetNode")
            return self.resolve(up, depth + 1)
        if origin in self.bypass:
            return self.passthrough(node, ltype, depth)
        return [str(origin), oslot]

    def linked_names(self, node):
        return {i["name"] for i in (node.get("inputs") or []) if i.get("link") is not None}

    def widgets(self, node):
        t = node["type"]
        wv = node.get("widgets_values")

        if isinstance(wv, dict):  # VHS_* 一类用命名字典
            allowed = {k for k, _ in widget_defs(self.oi, t)}
            return {k: v for k, v in wv.items() if k in allowed}

        # rgthree: 动态 lora 项不是 object_info 里的固定 widget（required 为空），
        # 必须放在「无 widget 定义就返回空」之前，否则整个 LoRA 块会被静默丢掉。
        if t == "Power Lora Loader (rgthree)":
            out, idx = {}, 0
            for item in (wv or []):
                if isinstance(item, dict) and "lora" in item:
                    idx += 1
                    out[f"lora_{idx}"] = {
                        "on": item.get("on", True),
                        "lora": item["lora"],
                        "strength": item.get("strength", 1.0),
                        "strengthTwo": item.get("strengthTwo"),
                    }
            return out

        defs = widget_defs(self.oi, t)
        if not defs:
            return {}

        linked = self.linked_names(node)
        names = [(k, ty) for k, ty in defs if k not in linked]

        # 动态下拉框：子参数紧跟在选择值之后（API 里要点号全名）
        if any(ty == "COMFY_DYNAMICCOMBO_V3" for _k, ty in names):
            key = next(k for k, ty in names if ty == "COMFY_DYNAMICCOMBO_V3")
            pos = [k for k, _ty in names].index(key)
            kids = dynamic_children(self.oi, t, key, (wv or [])[0])
            names = names[: pos + 1] + [(c, "enum") for c in kids] + names[pos + 1:]

        vals = list(wv or [])
        out, vi = {}, 0
        for k, ty in names:
            if vi >= len(vals):
                break
            out[k] = vals[vi]
            vi += 1
            if k in SEEDS and vi < len(vals) and isinstance(vals[vi], str) and vals[vi] in CTRL:
                vi += 1
        return out

    def convert(self):
        prompt = {}
        for n in self.wf["nodes"]:
            if n["type"] in VIRTUAL:
                continue
            if n["id"] in self.mute or n["id"] in self.bypass:
                continue  # 静音/旁路节点不进执行图（其输出已在 resolve 里直通或断掉）
            entry = {"class_type": n["type"], "inputs": dict(self.widgets(n))}
            for inp in n.get("inputs") or []:
                if inp.get("link") is None:
                    continue
                src = self.resolve(inp["link"])
                if src is not None:
                    entry["inputs"][inp["name"]] = src
            prompt[str(n["id"])] = entry
        return prompt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workflow")
    ap.add_argument("--object-info", default="oi2.json")
    ap.add_argument("--out", default="base_prompt.json")
    a = ap.parse_args()
    wf = json.load(open(a.workflow, encoding="utf-8"))
    oi = json.load(open(a.object_info, encoding="utf-8"))
    p = Converter(wf, oi).convert()
    pathlib.Path(a.out).write_text(json.dumps(p, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"节点 {len(p)} 个 -> {a.out}")


if __name__ == "__main__":
    main()
