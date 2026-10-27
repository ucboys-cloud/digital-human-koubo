# 本地 ComfyUI · H3 Continuum 长视频（数字人口播的默认生成后端）

> 2026-10-26 在 RTX 5090 D v2（24GB）+ 68GB RAM 上跑通并交付成片，40 秒 4 段。
> 替代 Renoise 云端：不出网、不计 credits、形象和音色完全可控。
> 触发：用户说「本地跑 / 用我的显卡 / ComfyUI / 不要云端 / 直播感 / 长视频 / 40 秒 / 1 分钟」。

---

## 0. 环境（已装好，先自检，别重装）

| 项 | 位置 / 检查方式 |
|---|---|
| ComfyUI | `http://127.0.0.1:8188`，`curl -s $COMFY/system_stats` 有返回即在跑 |
| 工作流 | 用户的 Continuum V3.9：手头 JSON 用 `w2api.py` 转成 `continuum_base.json`（本项目已转好，33 节点→21 节点） |
| 模型 | **沿用用户工作流里的值**（当前 = `Minimax-h3_Singularity_x_10Eros-Max_PRISM_int8.safetensors`）。要换用 `--unet`；`ref2va_Pruned_v1.3` 是可用的备选 |
| 插件 | `comfyui-h3-continuum`（`H3ContinuumSamplerV39` 等节点）、`rgthree-comfy`（Power Lora Loader） |
| ffmpeg / ffprobe | PATH 里有就行；否则设 `FFMPEG_DIR` 指向 bin 目录 |
| whisper.cpp | PATH 里有 `whisper-cli`；否则设 `WHISPER_DIR`。模型自动在 `whisper-cli` 附近找 `ggml-*.bin`，找不到再用 `WHISPER_MODEL` 指定 |
| Python | 3.10+，需 numpy / opencv-python-headless / pillow |

所有脚本**环境变量优先、PATH 兜底**，换机器一般只需要设这几个：

```bash
set COMFY_URL=http://127.0.0.1:8188
rem 下面几个按自己机器改；ffmpeg/whisper 已在 PATH 里就不用设
set COMFY_INPUT=<ComfyUI 安装目录>\ComfyUI\input
set FFMPEG_DIR=<ffmpeg 的 bin 目录>
set WHISPER_DIR=<whisper.cpp 目录>
set WHISPER_MODEL=<ggml-*.bin 的完整路径>
set REFS_DIRS=<参考音频目录1>;<参考音频目录2>
```

例（Windows）：`set COMFY_INPUT=D:\ComfyUI_windows_portable\ComfyUI\input`

---

## 0.4 🔴 基底怎么来：优先要「Save (API Format)」导出（2026-10-27 定稿）

用户工作流是 UI 格式，必须转成 API 才能提交。**优先让用户在前端 Ctrl+S 旁的下拉里选
`Save (API Format)` 导出一份**——那是 ComfyUI 自己转的，零风险。

没有 API 版时才用 `scripts/local-h3/w2api.py`。UI 版转换有两个**静默**陷阱（都真踩过）：

| 陷阱 | 表现 | 修法 |
|---|---|---|
| rgthree LoRA 丢失 | `Power Lora Loader` 只剩 `{"model":[…]}`，6 个 LoRA 全没 | 特判必须排在 `if not defs: return {}` **之前**（该节点 required 为空，只有 optional model/clip） |
| 旁路节点被当真执行 | `mode=4` 的节点进了执行图，还被连进 `first_frame` / `driving_audio` / `reference_image_4..6` | `mute`(2) 输出置空；`bypass`(4) 按同类型输入直通，不进 prompt |

另外 `Fast Groups Bypasser (rgthree)` / `MarkdownNote` 是**纯前端节点**，后端 `object_info` 里不存在，
必须归入 `VIRTUAL` 跳过。

**转换后必须四项对账**（缺一项就是丢东西）：

```
节点数 == 前端节点数 - 纯UI节点 - 旁路节点
LoRA 项数 == 前端 Power Lora Loader 里 on:true 的个数
模型名 == 前端 UNETLoader 的值（别自作主张换）
无残留旁路节点（grep 那些 mode=4 的 id）
```

**已存档**：`scripts/local-h3/base_official_api.json`（24 节点 / 6 LoRA / 官方导出原样）。
现行 `continuum_base.json` 就是它。

> 教训：转出来只有 24 节点而前端有 35 个，看着"对不上"其实是旁路节点被正确剔除了；
> 真正的错是**节点数对了但 LoRA 没了**——肉眼对节点数没用，必须逐字段 diff。

---

## 0.5 🔴 LoRA 必须在基底里（现在已修，不再靠 `--lora` 补）

**现象**：UI 工作流里 `Power Lora Loader (rgthree)` 挂了 6 个 LoRA、全部 `on: true`，
转成 API 后节点只剩 `{"model": ["240", 0]}` —— **一个 LoRA 都没有，且不报错**。

**后果（很容易误判成参数问题）**：模型按「裸模型」跑。裸模型用 5 步 = 严重欠采样 →
画面发虚、细节不足、长片后段更明显。此时去查步数、continuity、引导帧尺寸全是白费力气。

**实测差距**（同参考图同提示词，26s 同尺度人脸）：

| 配置 | 发丝 / 皮肤 | sharpness 均值 |
|---|---|---|
| 裸模型 5 步 | 糊成片、皮肤无纹理 | 96.5 |
| + 6 个 LoRA（同样 5 步） | 根根分明、有明暗层次 | **127.2** |

**现状**：`w2api.py` 已修，基底自带用户那 6 个（Motion_Repair 0.3 / wushu_spatial 0.3 /
H3_Combat 0.5 / dmad_dareties 0.8 / Singularity_64-fro95 0.3 / Motion_Booster 0.5）。
`--lora` 只在临时替换时用，可重复；提交前会打印 `LoRA N 个: 文件名@强度`，**跑之前先核对这一行**。

---

## 1. 全流程（每步都能返工）
```
看内容 → 选风格 → 写稿（按 H3 语速排字）→ 分段 prompt（Continuum 格式）
   → h3c_run.py 提交 → 轮询 → 取片 → whisper 回听 → 清晰度检测 → 抽帧看
   → 拆条字幕 → （需要时）Remotion 包装
```

```bash
# 1) 生成（4 段 × 10 秒，严格按参考图比例）
python h3c_run.py --image 参考图.png --text-file 提示词.txt \
  --chunks 4 --seconds 10 --width 864 --height 1280 --size-source Manual \
  --prefix koubo/live40 --out out/live40.mp4

# 2) 回听
ffmpeg -y -v error -i out/live40.mp4 -ar 16000 -ac 1 out/live40.wav
whisper-cli -m "$WHISPER_MODEL" -l zh -nt -np out/live40.wav

# 3) 清晰度（判断有没有分块发虚）
python sharpness.py out/live40.mp4

# 4) 字幕（多段拼接必须用这个，不要用连续转写）
python srtsplit.py out/live40.wav 台词.txt out/live40.srt
```

---

## 2. 段数 / 时长 / 分辨率 —— 全部在 `H3ContinuumSamplerV39`（节点 #312）

| 字段 | 含义 | 取值 |
|---|---|---|
| `chunks` | 段数 | 1–16，默认 3 |
| `chunk_seconds` | 每段秒数 | **4.0–30.0**，默认 5.0 |
| `prompt_mode` | 提示词切分 | 长片一律 `Timeline` |
| `size_source` | 尺寸来源 | `Manual`（最准）／`First Image`／`Legacy Aspect`（默认，别用） |
| `width` / `height` | Manual 下的宽高 | **必须是 32 的倍数** |
| `preset` | 预设档 | Draft 0.30MP / Balanced 0.60MP / Native 768 / Custom |
| `custom_mp` | 自定义百万像素 | 0.1–16.0 |
| `aspect` | 比例 | 只在 `Legacy Aspect` 下生效，Manual/First Image 下忽略 |
| `continuity` | 段间连贯帧数 | Balanced — 22 frames（默认） |
| `video_reference_size` | **续拍引导帧（Video Guide）尺寸** | `Efficient - 0.4 MP`（出厂默认，长片会糊）／`Balanced - 0.6 MP`／**`Match Output`（长片必须用这个）** |
| `reference_size` | 首图/参考图尺寸 | `Match Output`（默认）／`Max Identity`（保留更多细节） |

### 🔴 长片越跑越糊：Video Guide 一定要 Match Output（2026-10-27 定位）

现象：30 秒片子里**第 1 段清晰，第 2 段开始发虚，第 3 段明显雾化磨皮**。

根因：工作流出厂值 `video_reference_size = Efficient - 0.4 MP`，官方说明是「引导帧限制在约 0.4MP」。
而输出是 864×1536 = 1.33MP。于是：

| 段 | 引导帧从哪来 | 引导分辨率 | 结果 |
|---|---|---|---|
| 1 | 你的原图（1296×2352） | 全清 | 清晰 |
| 2 | 第 1 段末帧 → 压到 0.4MP | ~473×842 | 细节靠"编"，开始虚 |
| 3 | 第 2 段末帧 → 再压 0.4MP | ~473×842 | 继续累积，最糊 |

每块都要从低清引导里"猜"出 1.33MP 的细节，误差逐块累积——这就是中间开始劣化的原因。

**修法**：`video_reference_size = Match Output`（引导帧 = 输出像素面积）。
`h3c_run.py` 已加 `--video-ref-size`，基底 `continuum_base.json` 也已改成 Match Output。
代价：显存与耗时上升（30 秒片 10.5 → 约 13–16 分钟），但这是长片保画质的必要成本。

**验证方法**：抽 5s / 13s / 26s 三帧同区域放大对比，配合 `sharpness.py` 的逐段均值；
只糊在后段 = 引导帧降质，不是步数问题。

**选尺寸的规矩**

- 图生视频**不要用 Legacy Aspect** 硬指比例 —— H3 不裁切，只拉伸。参考图 2:3 却输出 9:16，脸会被拉长 1.18 倍（实测踩过）。
- 想严格保比例 → `Manual` + 32 倍数的宽高。例：截图 1440×2128（0.6767）配 **864×1280**（0.675），误差 0.25%。
- 图省事走 `First Image`：会被 32 取整拉到 896×1344（0.6667），差 1.5%，脸略瘦。
- Manual 模式下 `preset`/`custom_mp` 不参与计算，但要同步写成 `Custom` 和 `w*h/1e6`，否则节点显示「Draft 0.3MP」，看着像没设。
- `h3c_run.py` 提交前会打印 #312 的设置摘要，跑之前先看这四行对不对。

**时长与算数**：总时长 = `chunks × chunk_seconds`。40 秒 = 4×10s（推荐）；30 秒 = 4×8s 或 6×5s；60 秒 = 6×10s。

---

## 3. 字数密度 —— 按实测语速排，不要按公式拍脑袋

| 后端 | 默认语速 | 加速写法 | 加速后实测 |
|---|---|---|---|
| H3（本地） | **2.6 字/秒**（156 字/分） | 把语速写进**音色描述** | **3.58 字/秒**（215 字/分） |
| Grok Video（云端） | 约 5.4 字/秒 | — | — |

**加速写法**（写在人物设定的音色句里，不要单列一段「语速要求」）：

> 声音清亮偏柔，带一点书卷气，**语速偏快、接近资讯口播，字字清楚不含糊，句子之间几乎不留空隙**（S1）。

**排字档位**（技能 `minimax-video-prompt` L2199-2216：「信息密集/交代」档 260 字/分 × 占时比 70%）：

| 总时长 | 安全区间 | 每段（10s） |
|---|---|---|
| 40 s | **120–146 字** | 30–33 字 |
| 30 s | 90–110 字 | 23–27 字（8s 段） |
| 60 s | 180–220 字 | 30–36 字 |

排完必须自检：`字数 ÷ 3.58 ≤ 每段秒数`。留 1–2 秒气口，不要顶满，顶满了会被截尾。

**第一次用新音色 / 新语速时先标定**：跑 1 段 10 秒，台词按目标密度写满，whisper 回听看是否念完、实测多少字/秒，再定全长。这一步 2.5 分钟，省下 10 分钟白跑。

---

## 4. 提示词格式（Continuum V3.9 + ref2va 规范）

结构行英文，正文全中文。`[Chunk N]` **必须独占一行**，否则整份回退成 Fixed（诊断码 H3C-P100）。

```text
<共享 preamble：画质锚 + 人物指代 + 版式固定段 + 文字规则 + 环境动态 + 音效声明>
   这段会被自动附加到每一个 chunk

[Chunk 1]
# 口播默认用「身份锚定」这一句（换场景换姿态）
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is referenced for the subject's identity, wardrobe and color grading; the location, framing and body pose are newly staged.
# 只有真要「首帧=参考图」时才用这一句
# For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.
integrated_multimodal_description:
[Shot 1] 中景，<她此刻在做什么 + 开口说话>。
她的脸型、妆容、发型、发饰、服装与整体色调以 <Picture 1> 为准；姿势、取景与背景不复制 <Picture 1>。
<S1> 音色+语速（S1）：
<d>[中文] 台词</d>
她闭上嘴，<视线落点>。
本段结束时：位置…；动作相位…；镜头…；环境…。
overall_soundscape:
两个具体音效，各对应一个画面动作。
non_diegetic_music:
N/A

[Chunk 2]
integrated_multimodal_description:
[Shot 1] Continuation of Chunk 1. 承接第 1 段末尾：<四件套接住>。
...（三字段每段都要闭合）
```

**Ref2VA 四行结构，缺一行就漂**：增量行 → 保留行 → 锁定行（背景不变/镜头固定）→ 台词行，**每句台词后必须补「她闭上嘴」**（控唇形）。

**禁止对绑定的图做文字重述**：图已经定了脸、发型、服装、构图、光线，文字只写「谁在动、怎么动、说了什么」。写了「二十岁上下、鹅蛋脸、白色交领」就是在跟图打架。

**首帧锚句只在 Chunk 1 写一次**，重复会被当成每段重设首帧。

---

## 4.4 🔴 官方 skill 的长视频纪律（2026-10-27 按 `write-continuum-h3-prompts` 校正）

插件自带官方 skill：`custom_nodes/comfyui-h3-continuum/H3-Continuum-Skill-v1.zip`
→ `write-continuum-h3-prompts/references/prompt-quality.md` 与 `continuity.md`。写长片前先读这两份。

1. **preamble 只放真正不变的东西**。每块 body 只写：当前状态 + 动作 + 镜头演进 + 台词 + 交接状态（end state）。
2. **禁止每块重复外观形容词**。`high contrast / glossy skin / extreme sharpness / vivid saturation` 这类词
   因为 preamble 会被自动附加到每一块，反复叠加会**加剧**长视频外观漂移——官方原话是会「污染 Issue #13 的对比」。
   → 所以「画质干净锐利／毛孔／发丝根根分明／不粘连／曝光一致」这类句子**只写一次都嫌多**，写进 preamble 等于每块重复。
3. **Issue #13 是插件已知问题，提示词只能减轻、不能根治**：
   > A better prompt can clarify intent; it cannot guarantee removal of cumulative saturation, contrast, sharpness or oily-skin drift (Issue #13).
4. **每块开头写 `Continuation of Chunk N.`**（N = 紧邻上一块），后面必须跟具体继承状态：姿势、支撑、动量、视线、机位。
5. **不要每块把 I2VA 续拍重置回原图**，否则会把参考图的姿势重新拉回来。
6. 否定式改正面：`non_diegetic_music: N/A` 就够，别在 preamble 再堆「不生成任何背景音乐…」（用户红线留一句即可）。
7. 官方明确：39 帧 overlap 是**别的节点**的 workaround，不是 Continuum 默认，别当规则搬过来。

**踩过的坑**：v3/v4 的 preamble 堆到约 640 字（画质锚 + 身份锚 + 表演要求 + 曝光锁），
每块重复一遍 → 与第 2 条正面冲突，实测段 2 起发白发软。v8 压到 170 字、块内只写状态与动作后重跑对比。

---

## 4.5 🔴 ref2va 的自由度：参考图只锚身份，不锁场景与姿态

> 2026-10-27 用户抓出「为什么每片都从参考图那个姿势开始」。这是踩过的坑，别再犯。

我们用的就是 **ref2va**（`Minimax-h3_Singularity_ref2va_*`）。ref2va 的"参考"是**属性参考**，不是"首帧复刻"：

| | 参考图说了算 | 分镜说了算 |
|---|---|---|
| 人 | 脸型、五官、妆容、发型、发饰、服装、配色 | 站/坐/走/倚、朝向、手脚动作、表情 |
| 画 | 色调、光线方向、画质基调 | 取景、构图、景别、机位、镜头运动 |
| 景 | 视觉气质（"清新透亮的绿荫"） | 具体场景、道具、与环境的接触 |

官方保留关系里这叫 **`attribute_transfer`**；`fully_preserved`（整帧复制）只在"就要首帧等于这张图"时用。

**口播默认走 attribute_transfer**。复刻会得到「一张会说话的图」：站定、镜头锁死、只有嘴动——真实感弱。

### 🔴 `first_frame` 必须不接（2026-10-27 用户抓出「开头一秒是参考图的镜头」）

`reference_image_1`（#348）和 `first_frame`（#312）是**两个接口**，作用完全不同：

| 接口 | 作用 | 口播该不该接 |
|---|---|---|
| `reference_image_1` | 属性参考，每块都可用（`reference_use=All chunks`） | **要接** |
| `first_frame` | 把这张图当**第 0 帧**逐帧输出 | **不接**（`h3c_run.py` 默认已断，`--first-frame` 才接） |

接了 `first_frame` 的实际观感就是「一开头闪一下原图」，实测与参考图的 NCC（归一化互相关）：

| t | 0.00s | 0.25s | 0.50s | 0.75s | 1.00s |
|---|---|---|---|---|---|
| 接了 first_frame | 0.995 | 0.978 | 0.867 | 0.533 | 0.551 |
| 不接 | 0.392 | 0.412 | 0.511 | 0.594 | 0.599 |

断开后 `t=0` 直接就是生成画面，脸、妆、发饰、服装照样锚得住（属性参考在工作）。
`size_source` 已手工指定宽高时，断开 `first_frame` 不会影响比例——`aspect` 字段本来就是 V3.8 遗留兼容项。

### 动作要有动机，别"站着念稿"

| 要素 | 写法 |
|---|---|
| 动机 | 别回耳后的头发 / 扶着树干 / 拂肩头落叶 / 端茶盏 / 翻账本 —— 说话是这个动作的自然延续 |
| 重心 | 站姿重心在两脚间换一次；久站会换脚、身体轻微前倾或后靠 |
| 手势 | 只在关键处抬手，做**有内容**的手势（比数量、摊手、指向身侧），做完自然落下 |
| 呼吸 | 句间换气；强调处停顿半拍，说完轻轻呼气 |
| 眼神 | 多数时候看镜头，偶尔短暂移向手边再收回；不要全程死盯 |
| 环境 | 发丝衣摆持续被风带动、光斑在脸上移动、脚下踩过落叶 |
| 机位 | 段间推进 / 跟移 / 换景别（中景→近景），不要全程固定 |

**幅度红线**：不大转身背对镜头、不快速大幅摆动、手不挡脸 —— 会掉脸 / 形变。幅度取"看得出来但不抢戏"。

### 段间怎么变（30 秒 3 段示例）

| 段 | 场景动作 | 景别与机位 |
|---|---|---|
| 1 | 侧身站在光斑里低头别头发 → 抬眼转正开口 | 中景，极小幅度缓慢推近 |
| 2 | 一边说一边沿小径走两步 → 停在一棵树旁、手扶树干 | 中景略退，镜头小幅跟移 |
| 3 | 松开树干、上身微前倾、语气沉下来收尾 | 推近到近景（胸部以上） |

每段结尾都要写清**相位**（站位 / 手的落点 / 视线 / 机位 / 环境），下一段开头用「承接上一段末尾」接住。

### 自检

- [ ] 有没有写「起幅与 <Picture 1> 完全一致 / 保留 <Picture 1> 的构图与姿态」？口播类出现即犯规。
- [ ] 开场动作有没有动机？
- [ ] 全片有没有景别 / 机位 / 站位变化？
- [ ] 换姿态后，脸 / 服装 / 发饰的锚定句还在不在？

---

## 5. 🔴 声音：只留音效和台词，严禁配乐
用户的硬性规则，任何片子都不例外。

| 层 | 写在哪 | 内容 |
|---|---|---|
| 台词 | `<d>[中文] …</d>` | 只有台词 |
| 音效 | `overall_soundscape:` | 画面内真实声音：底噪、烛火、纸张、笔触、脚步、开合门 |
| 配乐 | `non_diegetic_music:` | **一律 `N/A`** |

并在 preamble 结尾加一句：

> 声音只有台词与画面内的真实音效，不生成任何背景音乐、配乐、垫乐、伴奏、旋律或哼唱。

- 多段拼接**必须** N/A：段间 BGM 风格、节奏、音量必然不一致，接缝处断掉。
- 全片声音元素 ≤4 个（音效个数 + 尾音），有台词时再减。
- **验证是否混进音乐**（比听更硬）：对说话间隙做 `showspectrumpic` 放大频谱 —— 有音乐时 800–4000Hz 是连续宽带漫射，纯音效时基本全黑只剩零星瞬态。

```bash
ffmpeg -y -v error -ss 28.0 -t 2.8 -i out.mp4 -lavfi "showspectrumpic=s=800x400:legend=1:scale=log:stop=4000" spec.png
```

---

## 5.5 音频输入有两种，别搞混

| 模式 | 接哪里 | 作用 | 谁在说话 |
|---|---|---|---|
| **A 模型自念（默认）** | 不接音频，台词写在 `<d>[中文] …</d>` | H3 自带 TTS 念台词 | H3 生成的音色 |
| **B 现成音频直驱** | 采样器 `driving_audio`（AUDIO） | 口型、节奏、停顿全部跟着这段音频 | **就是这段音频本身** |
| C 音色参考（另一回事） | `reference_audio_1` / `reference_audios` | 只借音色，内容仍由 H3 念 | H3 用那个音色念 `<d>` 台词 |

用户说「音频直接输入、不当参考」＝ **B**。

**用法**

```bash
python h3c_run.py --image 形象图.png --text-file 提示词.txt \
  --chunks 4 --seconds 10 --width 864 --height 1280 --size-source Manual \
  --drive-audio 配音.wav --out out/xxx.mp4
```

- 脚本会自动把音频转成 44.1k 双声道 wav 放进 ComfyUI 的 `input/kotalk/`，新建一个 `LoadAudio` 节点接到 `driving_audio`（原来的 Audio Switch 和示例 mp3 直接摘掉）。
- 提交前会 ffprobe 比时长并打印：吻合打 ✓，不吻合会直接给出该改成 `chunks=? × chunk_seconds=?`。

**三条硬规矩**

1. **音频总长必须等于 `chunks × chunk_seconds`**（±0.35s）。不等就会被截断，或后段没声音。40 秒音频 → `4 × 10s`；44.6 秒 → `4 × 11.1s`。
2. **`<d>` 台词可以留着**。2026-10-27 实测：接了 driving_audio 之后，成片音轨与驱动音频**波形相关性 r = 1.0**（就是同一段），`<d>` 不会触发额外 TTS、不会念两遍。台词留着还能帮模型对齐语义和表情。
   真遇到重复念（换模型/LoRA 后可能变）再用 `--no-dialogue` 把 `<d>` 块整段删掉。
3. **验证一次只要 4 秒**：`chunk_seconds` 最小 4.0，切一段 4 秒音频跑 1 段，1 分钟出片。检查三项 —— 视频时长 = 4.000s、音轨是不是原音频（相关系数应接近 1.0）、口型有没有开合。

**为什么口型比自念更准**：B 模式下时间轴由音频定死，模型只负责把嘴型贴合上去；A 模式要模型自己决定念到哪、停多久，语速和停顿都是估的。

---

## 5.6 用 VoxCPM2 自己配音（`tts.py`）

要给 B 模式准备配音，或者想固定音色/克隆自己声音时用。

```bash
# 纯 TTS，音色用文字描述
python tts.py --script 剧本.txt --out out/voice.wav \
  --voice "年轻女声，语速偏快，字字清楚，接近资讯口播"

# 音色克隆：参考音频 + 自动转写原文（推荐）
python tts.py --script 剧本.txt --out out/voice.wav \
  --reference "<参考音频目录>/自然口播女声01.MP3" --auto-prompt

# 音色克隆：自己给原文（比自动转写更准，尤其生僻词）
python tts.py --script 剧本.txt --out out/voice.wav \
  --reference 参考音.wav --prompt-text "参考音的原话"

# 精确对齐到 H3 的 40 秒（自动补静音 / 裁尾）
python tts.py --script 剧本.txt --out out/voice.wav --target 40 --gap 0.15
```

**两种克隆模式**（VoxCPM2 内部区分，`tts.py` 自动选）

| 模式 | 条件 | 效果 |
|---|---|---|
| ultimate | 有参考音频 **+ 原文** | 更稳，推荐。原文用 `--auto-prompt` 让 whisper 自动转写，或 `--prompt-text` 手写 |
| controllable | 只有参考音频 | 也能用，音色略飘 |

参考音频要求：**≤50 秒**（节点硬限制 `MAX_REFERENCE_AUDIO_SECONDS`）、单人、无背景音乐。
太长会直接报错，先裁一段干净的 8–15 秒。
whisper 转写中文默认输出繁体，当 prompt_text 不影响克隆（都是汉字）。

**参考音频库**（自己攒，任意目录都行；单条 ≤50 秒、纯净人声最好）

用 `REFS_DIRS` 环境变量给目录（分号分隔），`refs_index.py` 会递归扫：

```bash
set REFS_DIRS=D:\参考声音;D:\index-tts\reference_audios
```

跑 `refs_index.py` 会生成 `out/refs_index.md`：文件名 / 时长 / 采样率 / 内容摘要，挑音色看这个。

**克隆实测**（`自然口播女声01.MP3`，10.9 秒，抖音口播腔）

| 指标 | 参考音 | 生成音 | 偏差 |
|---|---|---|---|
| 基频（F0 中位数） | 210.5 Hz | 242.4 Hz | 15.2%（约 2.4 个半音，偏高一点） |
| 频谱质心（音色明亮度） | 1026 Hz | 1066 Hz | **3.9%** |
| 语速 | — | 4.5–4.9 字/秒 | — |

→ 共振峰特征（决定「像不像」）很接近；音高略偏高是克隆常见波动，可降 `--cfg` 或换更长的参考音改善。


**显存策略 `--offload`（这个脚本存在的意义）**

| 值 | 行为 | 什么时候用 |
|---|---|---|
| `end`（默认） | 模型常驻跑完所有段，**最后统一 `/free` 一次** | 批量配音，最快。每段省掉 8GB 重载（约 10 秒） |
| `always` | 每段跑完就卸 | 只录一两段、且马上要跑视频 |
| `never` | 完全不管显存 | 调试 |

**语速差异（重要，排字要用这个）**

| 谁在念 | 实测语速 |
|---|---|
| H3 自带 TTS（默认） | 2.6 字/秒 |
| H3 自带 TTS + 写「语速偏快、接近资讯口播」 | **3.58 字/秒** |
| VoxCPM2（TTS 节点，写「语速偏快」） | **4.0–5.2 字/秒**（实测 20 字 ≈ 4.0–5.0s） |

→ 所以走「VoxCPM2 配音 + H3 音频直驱」时，**40 秒可以排到 160–200 字**，比 H3 自念的 120–146 字多得多。
反过来，如果按 120 字配 40 秒的音频，`--target 40` 会补十几秒静音，脚本会警告「台词偏少，后半段会没话讲」。

剧本格式：`## 第N段` 分段，一行一句；不写 `##` 就把每个非空行当一段。

### 🔴 开头那声「爆音」= 上一句的尾音残响（2026-10-27 定位，不是模型抽风）

现象：每段配音一开头「啪」一下，听起来像爆音。

根因（实测，非猜测）：**ComfyUI 端 VoxCPM2 直出的 flac 第 0 个采样就有能量**。前 ~260ms 是一段
固定形状的衰减噪声，接着 ~100ms **采样本全为 0 的完全静音**，然后台词才真正起音。五段实测形状一致：

```
20ms 窗口峰值：0.61 0.61 0.62 0.61 0.55 0.41 0.12 0.06 0.04 0.04 0.04 0.04 0.05
               0.00 0.00 0.00 0.00 0.00  ← 100ms 死静音
               0.07 0.19 0.29 …        ← 台词起音
```

峰值随内容变化、形状不变 → 是**上一次推理的尾部残响**（模型缓存没清）被贴到了新段开头。

判断（不听，看数）：每 20ms 打一次峰值，开头出现「高能量 → 全 0 → 起音」三段结构就是它。

修法（`tts.py` 已内置，默认开）：

- `trim_head()`：在前 0.85s 里找**最后一段 ≥60ms 的完全静音**，从它结束处裁掉——那里才是语音真起点。
  找不到这种静音段就认为没有残响，原样不动（不会误伤正常起音）。
- 首尾各 8ms / 25ms 淡入淡出，防 PCM 硬切造成 click。
- `--no-trim` 可关（不推荐）。

### 🔴 片头必须留白，别一开口就念

人还没站稳就说话，是最假的地方。

```bash
python tts.py --script 段1.txt --out s1.wav --target 10.2 --lead 1.5 ...
```

- `--lead 1.5`：开头插 1.5s 静音。**lead 算在 `--target` 之内**，所以第一段台词要相应减字：
  10.2s 段长、1.5s lead → 只剩 8.7s 语音 → 约 **33 字**（3.8 字/秒）。
- **提示词必须写时间锚**，否则 H3 在 0 秒就张嘴，嘴型对不上音频：

  > 开场第 0 到 1.5 秒她还没有开口：……约 1.5 秒时开始说第一句——前 1.5 秒只有环境音，没有任何人声。

- 只给第一段加 lead；段与段之间不加（靠段内的自然停顿衔接）。

---

## 5.7 一键成片：`pipeline.py`（推荐的日常入口）

定死了模式：**H3 不发声，只按输入音频对口型**。唯一要操心的就是配音长度 ↔ H3 段数对上。

```bash
python pipeline.py --script 剧本.txt --image 形象图.png \
  --prompt-template prompts/某模板.txt \
  --reference "<参考音频目录>/自然口播女声01.MP3" --auto-prompt \
  --width 864 --height 1536 --size-source Manual \
  --out out/final.mp4
```

它自动做四件事：
1. 调 `tts.py` 生成配音（`--offload end`，跑完统一清显存）；已有配音就用 `--audio xxx.wav` 跳过
2. **按配音总长自动算 `chunks × chunk_seconds`**：每块落在 4–30s，尽量靠近 10s；
   **优先让块数 = 剧本段数**（块边界落在句子边界，模型更连贯），不合法才回退
3. 把提示词模板的块数补齐/裁剪到 chunks 个：模板只需写 `[Chunk 1]` 一块，多的块自动复制并加
   `Continuation of Chunk N.`，且**每块台词自动换成该块对应的稿子**
4. 调 `h3c_run.py --drive-audio` 出片（提交前自动清显存）

排字公式：**配音稿按 4.5–4.9 字/秒排**；30 秒 ≈ 140 字、40 秒 ≈ 190 字、60 秒 ≈ 280 字，
分 3/4/6 段（`## 第N段`），块数会自动对上。想精确卡时长再加 `--target 30`。

模板写法：preamble（画质 + 人物指代 + 禁配乐声明）+ 一个 `[Chunk 1]` 块（含 `<d>[中文] 台词占位。</d>`）。
参考 `scripts/local-h3/` 同目录给的示例。

---

## 6. 直播截图当参考图（保留界面元素）

用户要「抖音直播那种真实感、要状态栏和滚动弹幕」时，走这套。

**整张截图直接入槽**，界面元素**不排除、要保留**。依据技能 `minimax-video-prompt` 铁律 #2 的「文字三分类」：

| 类 | 例子 | 处理 |
|---|---|---|
| ① 场景实体文字 | 招牌、书页、宣纸字迹 | 逐字抄 + 与图一致 |
| ② **界面/叠加层** | 状态栏、昵称条、弹幕、底部输入栏 | **按场景定：要保留的进「版式固定段」逐条列**；只在相册截图类才排除 |
| ③ 参考图自带小角标 | 时间戳水印、边框小字 | 一律排除 |

**版式固定段**（preamble 里）按九宫格坐标逐条锁：左上角状态栏、右上角、左侧中下部弹幕列表、底部输入栏、最底部手势条。每一条写清「位置 + 内容 + 颜色 + 行为」。弹幕写成：

> 弹幕以极慢的速度整体向上推移：最上面一条缓缓移出画面，新的在列表最底部淡入顶上来；文字始终水平、清晰、笔画完整，不变形、不闪烁、不左右漂移。

实测：状态栏 `21:47`、信号/WiFi/电池 `83`、昵称、`12.8万`、九条弹幕、`说点什么...` 全部逐字还原；弹幕跨 10s 分块边界连续上移、不跳回。**唯一风险**是单个生僻字（如《醉花阴》的「阴」会略糊），整条弹幕不会崩。

---

## 7. 采样步数：别信 Turbo 工作流自带的 3 步

Continuum 的 `Turbo_Sample` 工作流 `BasicScheduler` 是 **3 步**，但 LoRA 栈里**没有 turbo 蒸馏 LoRA**，3 步不收敛 → 分块质量忽高忽低。

| 采样 | 清晰度均值 | 最低值 | 现象 |
|---|---|---|---|
| 3 步 simple | 100.9 | **49.8** | 4 块里第 2、4 块整段雾化 |
| 10 步 beta | **258.4** | 165.1 | 干净 |
| 5 步（新版工作流 + 稀疏注意力） | 1005.9 | 855.3 | 干净，速度快 2 倍 |

判断方法只有一个：`python sharpness.py 成片.mp4` 看最低值。低于 100 就是有段发虚，别交。

---

## 8. 显存管理：TTS 跑完必须清，否则视频生成变慢

**现象**：跑完 VoxCPM2 / 任何 TTS 后，显存被占 5–8GB 不退，接着跑视频/图片明显变慢。

**原因**（已定位到源码）：
1. `VoxCPM2_TTS` / `VoxCPM2_Clone` 节点自带 `force_offload` 开关，**默认 False**。模型实例缓存在 `modules/loader.py` 的模块级字典 `LOADED_MODELS_CACHE` 里，不进 ComfyUI 的自动回收流程。
2. 它还会以 `currently_used=True` 把模型登记进 `model_management.current_loaded_models`，等于告诉 ComfyUI「这个正在用」，`free_memory` 不会主动卸。
3. ComfyUI 启动带 `--cuda-malloc`（cudaMallocAsync），显存池由驱动托管，`nvidia-smi` 上的 used 不会自己回落。

**实测数据**（RTX 5090 D v2 / 25.64GB）：

| 操作 | 跑完显存 | 结论 |
|---|---|---|
| `force_offload=False`（默认） | 已用 1.96 → **7.49 GB** | 残留 **5.53 GB** |
| 之后调 `/free` | 7.49 → **1.96 GB** | 能全退，只是没人触发 |
| `force_offload=True` | 1.96 → **1.96 GB** | **零残留**，且生成反而更快（16.5s vs 22.1s） |

### 会不会「跑一次涨一点」？—— 会，但会收敛

连续跑多轮的实测（同一台机器）：

| 实验 | 结果 |
|---|---|
| `force_offload=True` 连跑 5 次 | 2.00 → 2.00 GB，**完全持平** |
| `force_offload=False` 连跑 6 次**同样长度** | 7.13 → 7.12 GB，**持平** |
| `force_offload=False` 长度阶梯（短/长/短/长/短） | 7.16 → 7.20 → 7.27 → 7.38 → 7.38 GB，**涨 0.22 后收敛** |

结论：
- **不是内存泄漏**，是 `--cuda-malloc`（cudaMallocAsync）的显存池**按峰值扩张后不自动收缩**，加上 VoxCPM 的 KV cache 缓冲随输入长度取峰值。
- 每轮涨 0.02–0.08 GB，几轮后就稳住，不会无限涨。
- 真正值钱的还是那 **5.53 GB 常驻**，不是这 0.22 GB。
- 任何一次 `/free` 都能压回 1.96 GB（实测 `7.38 → 1.98`）。

### 三层解法，推荐前两个一起用

**① 治本：把工作流里的 `force_offload` 改成 True**（改一次，以后都干净）

节点参数位（`widgets_values` 下标）：
- `VoxCPM2_TTS` → 第 **10** 位（前面依次 model_name / lora_name / voice_description / text / cfg_value / inference_timesteps / max_tokens / normalize_text / seed / control_after_generate）
- `VoxCPM2_Clone` → 第 **12** 位（多 reference_audio / prompt_text / enable_denoiser）

改完回读校验一下。代价是每次要重新加载 8GB 模型，但实测反而更快——因为省掉了显存紧张时的 CPU↔GPU 搬运。

**② 兜底：跑完点一下 `scripts/local-h3/vram_free.py`**

```bash
python vram_free.py          # 立即释放
python vram_free.py --wait   # 等队列跑完再释放，不打断任务
```

实测一次释放 5.53GB。`h3c_run.py` 里也可以 `from vram_free import free_vram; free_vram(wait=True)`。

**③ 全局：ComfyUI 启动参数**（改启动 bat，影响所有工作流）
- `--disable-smart-memory`：每次执行完就把模型移出显存，不再"智能"缓存
- `--cache-none`：不缓存节点输出（省 RAM/VRAM，代价是重复执行变慢）
- 不建议去 `--cuda-malloc`：50 系上它是性能项，去掉会整体变慢

**提交视频任务前自动清理**：`h3c_run.py` 已内置，提交前调 `free_vram(wait=True)`。
不想要就加 `--no-free`；想连出片后也清一次加 `--free-after`。

---

## 8.5 🔴 磁盘：解码缓存会吃掉几十 GB 的 C 盘（2026-10-27 实测）

**现象**：C 盘莫名其妙少 40GB+，查 `%TEMP%` 全是 `h3-decode-cache-<pid>-*` 目录。

**实测**：一上午 7 次出片 → 7 个目录（4 个 7.9GB + 3 个 3.9GB = **43.3GB**），全在
`%TEMP%`（C 盘）。

**机制**（读插件源码 `decode_cache/store.py:208` + `storage_settings.py:417`）：

- 每次出片 `tempfile.mkdtemp(prefix=f"h3-decode-cache-{os.getpid()}-")` 新建一份
- 目录里 `.h3-owner.json` 记 `{pid, created}`；插件靠 `owner_alive()` 判断能不能删
- **owner 是 ComfyUI 自己**，只要 ComfyUI 不重启就永远"活着" → 旧目录一律不删
- 单份上限由 `H3DecodeCacheHelper`（#344）的 `disk_budget_gb` 决定，**工作流出厂 8GB**

所以「跑一次少 8GB C 盘」是必然，不是偶发。

**处理**（两件事都做了，`h3c_run.py` 内置）：

| 措施 | 做法 | 效果 |
|---|---|---|
| 压小单份 | 构建时把 #344 `disk_budget_gb` 改成 **2**（`--disk-cache-gb`，0=用工作流原值） | 每份 8GB → 2GB |
| 出片后清旧 | `purge_decode_cache()`：只删「非最新」且「闲置 >5 分钟」的目录，被占用的跳过 | 不再堆积 |

**⚠ 搬盘后必须同步改清理函数的扫描范围**：`purge_decode_cache()` 原来只 glob `%TEMP%`，
缓存一改到 G 盘它就**扫不到任何东西、静默失效**。现在改成 `decode_cache_parents()`：
先读 `GET /h3-continuum/storage/status` 取 `current=true` 的 decode 根，再兜底加系统 TEMP，
两处一起扫（去重）。以后换盘不用再改代码。

**注意**：改的是**构建时**的值，`continuum_base.json` 保持与用户工作流一致（仍写 8）——
基底是"忠实镜像"，任何任务级覆盖都只在脚本里发生，别写回基底。
`--no-cache-purge` 可关闭自动清理。

**根治（2026-10-27 已落地：改用插件自带的 Temporary Storage 指向 G 盘，比改 bat 更干净）**

插件自带 HTTP 接口，**不用进 UI、不用重启、不用改 bat**：

```bash
# 1) 看当前状态（revision / 现状路径 / 各卷剩余）
curl -s http://127.0.0.1:8188/h3-continuum/storage/status

# 2) 校验目标父目录（插件会在其下建 h3-continuum-scratch/{finalize,decode}）
curl -s -X POST http://127.0.0.1:8188/h3-continuum/storage/validate \
     -H "Content-Type: application/json" -d '{"path":"G:/ComfyScratch"}'

# 3) 写入（revision 必须是刚读到的最新值，否则报 Settings changed）
curl -s -X POST http://127.0.0.1:8188/h3-continuum/storage/settings \
     -H "Content-Type: application/json" -d '{"path":"G:/ComfyScratch","revision":0}'

# 4) 清理旧根（进程仍持句柄时会拒绝，属正常）
curl -s -X POST http://127.0.0.1:8188/h3-continuum/storage/cleanup \
     -H "Content-Type: application/json" -d '{}'
```

- 传的是**父目录**，插件自动建 `G:\ComfyScratch\h3-continuum-scratch\{finalize,decode}`
- 要求 `h3-continuum-scratch` **为空**（有陌生文件会被拒，保护误删）；成功后写 `.h3-scratch.json` 记归属
- **finalize 和 decode 一起搬**：原来 finalize 在 `ComfyUI\temp\h3-continuum-v35-file-backed`（单份 ~11GB，在 D 盘）
- 改完**立即生效**：`store.py:_directory()` 每次取目录都重新 `manager.resolve("decode", …)`，
  发现 parent 变了就把 `root=None`，下次出片直接在 G 盘建新目录
- 配置文件落在 `ComfyUI/user/__h3_continuum/temporary-storage.json`（revision 单调递增）
- 旧根**不会自动消失**：`kv`/mmap 句柄还挂着 → 手动删会被 Windows 共享冲突挡住，
  要等 ComfyUI 重启才释放。别为这事去强删，重启一次自动清
- 优先级：显式 `temp_parent` > `H3_DECODE_CACHE_TEMP_DIR` 环境变量 > 插件设置 > 系统 `TEMP`
- **这是服务端全局设置**：脚本提交的任务和在 ComfyUI UI 里手动排队的任务走同一套 `StorageSettings`，
  两边都落 G 盘，不需要在 UI 里再点什么
- **副作用（要知道）**：G 盘不可用（掉盘/改盘符）时插件会**直接报错拒绝出图**，不会静默退回 TEMP。
  所以别把 scratch 放在移动硬盘/网络盘上
- 旧根删除：句柄释放前删掉目录名也不会立刻还空间（Windows delete-on-close），
  `df` 看得到的那部分要等 ComfyUI 重启才真正回收

**手动清理**：直接删 `%TEMP%\h3-decode-cache-*` 里最早的几个即可（保留最新的活着那份），
删错了顶多是下次重算一遍缓存，不会坏任何已成片。

---

## 9. 耗时与返工成本（RTX 5090 D v2）

| 配置 | 耗时 |
|---|---|
| 1 段 6s / 864×480 | 1 分 41 秒（5 步） |
| 1 段 10s / 864×1280 | 2 分 26 秒（5 步） |
| 4 段 40s / 864×1280 | **10 分 17 秒**（5 步） |
| 4 段 40s / 832×1472 | 27 分钟（10 步） |

→ 先用 1 段 5–6 秒（2 分钟）验证比例、界面、语速，再跑全长。**先标定再量产**。

---

## 10. 踩过的坑（每条都真踩过）

| # | 坑 | 修法 |
|---|---|---|
| 1 | ~~模型用了 `_x_10Eros-Max_PRISM` 画面是花的~~ **结论已作废** | 当时是「裸模型 + 3 步」两个错叠一起，怪到了模型头上。补回 6 个 LoRA 后该模型 5 步出片完全正常（2026-10-27 复测）。**默认继承用户工作流的模型，别自己换** |
| 1b | 转换后 LoRA 全丢、旁路节点进执行图 | 见 §0.4 / §0.5。优先要 API 格式导出 |
| 1c | 片头 0~0.5s 是参考图本身（"闪一下原图"） | #312 的 `first_frame` 接了参考图。断开它，只留 `reference_image_1`（见 §4.5） |
| 2 | `BlockSparseAttention` 报 `required_input_missing: selection.tau` | 动态下拉框的子参数在 API 里要写**点号全名** `selection.tau` |
| 3 | UI→API 转换后采样器 30 个参数全错位一格 | **被连线占用的 widget 不会出现在 widgets_values 里**，转换时先剔除再按位对齐 |
| 4 | `highres_tiling_mode=global_stream` 报错 | 它**强制要求**模型链上有 sol-attn 稀疏注意力，不能跳 |
| 5 | 用 Legacy Aspect 硬指 9:16 → 脸被拉长 1.18 倍 | 改 `Manual` + 32 倍数宽高，或 `First Image` |
| 6 | 3 步采样分块雾化 | 见 §7 |
| 7 | 多段拼接用 whisper 连续转写出字幕 → 时间轴重叠 | 分块静音被当成句间停顿。改**逐块切片单独转写 + 块内偏移**（`srtsplit.py`） |
| 8 | 有 BGM 时 `silencedetect` 找不到语音间隙 | 阈值调到 -50dB 也无效，改逐块转写 |
| 9 | 字幕被 whisper 输出成繁体、且换行处多出逗号 | 用「whisper 时间戳 + 原稿文本」对齐，按标点断行、标点留在上一行尾 |
| 10 | 烧字幕位置压到嘴 | libass 默认 `PlayResY=288`，`MarginV` 按 288 算：1280 高的竖版用 **32**（底部约 140px） |
| 11 | 提交前没清队列，旧的 killed 任务还在跑，白等 10 分钟 | 提交前先查 `/queue`，有残留先 `POST /interrupt` |
| 12 | dry-run 也会真的入队执行 | 校验用 `/prompt` 提交后立即 `POST /queue {"delete":[id]}`；**但如果它已经启动，delete 无效**——一旦看到 GPU 99%，只能 `POST /interrupt` + `POST /queue {"clear":true}` |
| 13 | 跑完 TTS 显存不退，接着跑视频变慢 | `force_offload` 默认 False → 见 §8。改 True 或跑完调 `vram_free.py` |
| 14 | 任务正在跑时调 `/free` 释放量为 0 | 模型正在使用中卸不掉。`vram_free.py --wait` 会先等队列跑完再释放 |

---

## 11. 文件清单

| 文件 | 作用 |
|---|---|
| `h3c_run.py` | 主运行器：基底 → 改 5 处（模型/提示词/采样器/形象图/输出前缀）→ 提交 → 轮询 → 取片 → 打印 #312 摘要 |
| `w2api.py` | 通用 UI workflow → API prompt 转换器（用户给了新工作流时用它重转 `continuum_base.json`） |
| `continuum_base.json` | 转换好的基底（21 节点，参数与用户工作流逐项一致） |
| `prompt-template.txt` | 直播版 40 秒提示词模板（含画质 preamble + 版式固定段 + 4 chunk） |
| `srtsplit.py` | 逐块转写对齐出 SRT（多段拼接专用） |
| `sharpness.py` | 逐秒清晰度检测，判断分块是否发虚 |
| `vram_free.py` | 释放 ComfyUI 显存（TTS 跑完必用），`import` 或用 `--wait` |
| `tts.py` | VoxCPM2 批量配音 → wav，内置显存策略与 `--target` 精确对齐；`--reference` + `--auto-prompt` 做音色克隆 |
| `pipeline.py` | **一键成片**：文案 → 配音 → 自动配块数 → 音频直驱出片（日常入口） |
| `refs_index.py` | 扫参考音频库，whisper 转写 + 时长，输出 `out/refs_index.md` 索引表 |
| `vram_leak_test.py` | 连跑 N 次看显存是否递增（`--offload true/false`） |
| `vram_stair_test.py` | 长度阶梯实验，验证「只涨不跌」是否收敛 |
