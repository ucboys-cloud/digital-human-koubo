---
name: digital-human-koubo
description: 用固定的数字人形象（白背心数字人 / 用户本人数字人 / 猫狗角色）做口播视频，先按内容推荐剪辑风格让用户选（小林式解说 / 网红花字口播 / 发布解读 / 保姆级教程 / 多主播多语言），自动套上从 MrBeast、MKBHD、影视飓风、Johnny Harris、Vox、半佛、差评等头部博主拆出来的 48 个包装组件（开场钩子、数字钉子、文字在人身后的景深字、证据截图、地图路线、弹幕、投票、复盘板…），再写稿 → 切段 → 生成 → 分片下载校验 → 逐段回听 → 对齐 → Remotion 剪辑出片。生成后端二选一：本地 ComfyUI H3 Continuum（长视频 / 直播感 / 不出网 / 不计费，见 references/local-h3-continuum.md）或 Renoise Grok Video 1.5 云端（先报价、用户确认才生成）。触发：用我的数字人讲这段、数字人口播、让白背心数字人说、用数字人 Skill、数字人带货 / 解读 / 教程 / 种草视频、做成小林说那样、加花字、加包装 / 加地图 / 加弹幕 / 开场加预告 / 文字放在人身后、做成 MrBeast 那种节奏、有哪些包装手法、用本地 ComfyUI 跑 / 用我的显卡跑 / 长视频 / 40 秒 / 1 分钟 / 直播感 / 保留直播界面。不用于：换一个全新形象（先按 references/new-avatar.md 做形象）、冒充真人。
---

# 数字人口播

形象、声音、提示词、切段规则固定在 `persona.json`；剪辑风格在 `references/style-menu.md`。每次照这里做，出来的就是同一个人、同一种风格。

## 红线
- **声音只留台词和画面内音效，严禁配乐 / BGM。** 两个后端都一样：`non_diegetic_music` 一律 `N/A`，prompt 里再写一句「不生成任何背景音乐、配乐、垫乐、伴奏、旋律或哼唱」。底噪、纸张、脚步、烛火这类画面内音效必须保留，那不算配乐。BGM 后期在剪辑软件里配。
- 生成花用户的 Renoise credits：create_tasks 之前先报「段数 · 秒数 · 预估 credits · 余额」，等用户在对话里明确同意。先拍第 1 段给用户确认音色，再批量。重拍也要先报价。（**本地 H3 不计费，不需要报价，但同样要先拍 1 段验证比例/语速/形象再量产**）
- 成片标「内容由 AI 数字人演绎」；场景、动物片段角上标「AI 生成」。
- 用户本人的形象（persona.json → other_hosts.me）只用在用户自己的片子里。
- 「小林式」只学结构和剪辑手法：不用真实创作者的脸、声音、布景和原句。
- 点名评价第三方产品的说法，要有出处或标「网友分析 / 个人体验」。展示素材只用用户自己的作品；带歌词字幕的片子不用。

## 流程

### 准备：先检查，有就跳过，缺才引导安装（每次新对话第一次用时做）
**原则：已经装好的一句话带过，不让用户重装；缺什么才给装法，装法给多种，先放用户当前用的那种。** 详细装法在 references/install.md。

1. **先定生成后端**（最关键的一个岔路，先问清再动手）：
   - 以下任一命中就走 **本地 H3 Continuum** → 读 `references/local-h3-continuum.md`，全程照那份做：
     要 30 秒以上长视频 / 要直播感或保留截图界面 / 不想花 credits / 本机有 ComfyUI、显存 ≥16GB / 要自定义音色和形象。
     自检：`curl -s http://127.0.0.1:8188/system_stats` 有返回即在跑；再确认 `Minimax-h3_Singularity_ref2va_*` 模型和 `comfyui-h3-continuum` 节点在。
     **提交前先看显存**：跑过 TTS（VoxCPM2 等）会残留 5–8GB 不退，先 `python scripts/local-h3/vram_free.py --wait` 再提交，否则 H3 拿不到够用显存会反复搬权重、明显变慢。详见那份文档第 8 节。
   - 要 15–30 秒单段、要 Grok 自带的表演和音色、本机跑不动 → 走 **Renoise 云端**，继续第 2 条。
2. **Renoise MCP**（只在走云端时）：直接调 `get_account`。
   - 成功 → 只说一句「Renoise 已连接，余额 X 积分」，接着干活。
   - 工具不存在 / 未连接 → 停下引导安装。用户还没有 Renoise 账号时，注册链接一律给 https://renoise.ai/mcp?utm_medium=xcom&utm_source=official（原样给出，保留 utm 追踪参数，不要改写成 renoise.ai 首页）。然后把用户当前客户端的装法放第一个并标「推荐」，下面列出其他方式（Claude 桌面端/网页连接器、Claude Code 插件、Codex `codex mcp add`、OpenClaw、Cursor 等通用远程 MCP 配置、renoise.ai/plugin 官网），让用户自己挑。装完让用户重开对话或重连，再调一次确认。
   - 报工具被关闭 → 不是没装，让用户去连接器设置里打开；报授权过期 → 重新登录授权，不用重装。
3. **本机环境**（要剪辑、或走本地 H3 时都要）：`bash scripts/doctor.sh`。有的打 ✓ 不提；缺的它会按 macOS / Windows / Linux 列出多种装法。系统软件让用户自己装，Python 包可以在用户同意后帮装。本地 H3 还需要 ffmpeg、whisper.cpp + 模型、numpy/opencv — 见 references/local-h3-continuum.md 第 0 节。
4. **数字人形象**：persona.json 的 reference_material 能用就直接用；当前账号用不了（换了账号、素材过期、别人的包）→ 按 references/new-avatar.md 用用户自己的照片重做。走本地 H3 时直接给一张图即可（正脸、闭嘴、光线均匀；做竖版就给竖向图，横图会被裁掉两肩）。

### 0. 看内容 → 推荐风格 → 让用户选
按 `references/style-menu.md`：
1. 一行诊断（内容类型、有没有可展示的素材、适合的平台和时长）。
2. 推荐 2 个风格并说理由，把 `assets/styles/` 里对应的预览图发给用户。
3. 一次问完：风格 · 比例和时长 · 花字强度（克制 / 标准 / 热闹）· 主播（白背心 / 用户本人 / 两人接力 / 动物）。每题第一个选项是推荐项。Claude Code 用 AskUserQuestion，其他工具列编号。
4. 用户回「你定」就按推荐，并说一句按了什么。结果写进 `brief.json`，后面每一步按它来。

| 风格 | 比例 | 时长 | 剪辑实现 |
|---|---|---|---|
| A 小林式解说 | 16:9 | 3–20 分钟 | finance-explainer skill 的引擎（episode.json 拍表） |
| B 网红花字口播 | 9:16 | 30–120 秒 | `templates/huazi-916`（edit.json 驱动，三档花字） |
| C 发布解读 | 16:9 | 30–90 秒 | 参考实现 `templates/reference/launch-169` |
| D 保姆级教程 | 16:9 | 3–8 分钟 | 参考实现 `templates/reference/tutorial-169` |
| E 多主播多语言 | 16:9 | 3–7 分钟 | 参考实现 `templates/reference/multihost-169` |

### 1. 写稿 → script.json
按选定风格的稿子写法（style-menu.md 里每种都有）。每段一句或两句，标 `shot`：`full`（全屏出镜）/ `pip`（画中画讲解）/ `vlog`（随意自拍口吻）/ `depth`（要做「文字在人身后」的段：中景、头顶两侧留背景）。英文缩写、网址写成好念的样子。外语段直接写目标语言的台词。

**排字按后端算，两个后端语速差一倍，别套错：**

| 后端 | 语速 | 10 秒段的字数 | 40 秒的全片字数 |
|---|---|---|---|
| 本地 H3 | 默认 2.6 字/秒；写了「语速偏快」实测 **3.58 字/秒** | **30–33 字** | **120–146 字** |
| Renoise Grok | 约 5.4 字/秒 | 40–55 字 | — |

本地 H3 提速的写法 —— 把语速写进**音色描述**，不要单列「语速要求」段：
> 声音清亮偏柔，带一点书卷气，**语速偏快、接近资讯口播，字字清楚不含糊，句子之间几乎不留空隙**（S1）。

排完自检 `字数 ÷ 3.58 ≤ 每段秒数`，每段留 1–2 秒气口。密度不够会很拖（40 秒只讲 90 字＝按「正常对话」档在念），太满会被截尾。换新音色时先跑 1 段 10 秒标定实测语速，再定全长。

### 2. 切段（+ 云端要报价）
- **本地 H3**：段数 = 总时长 ÷ 每段秒数，直接在采样器节点 `H3ContinuumSamplerV39` 上设（`chunks` / `chunk_seconds`），`chunk_seconds` 只能 4.0–30.0。不计费、不用报价，但仍要先跑 1 段验证。接着按 references/local-h3-continuum.md 第 4 节写分段 prompt（`[Chunk N]` 独占整行）。
- **Renoise 云端**：`python3 scripts/build_tasks.py script.json tasks.json --purpose "teaching a beginner tutorial step by step"`
→ 打印段数、秒数、预估 credits。full 段 720p（17/秒），pip 段 480p（10/秒）。拿 `estimate_cost` 核一次，报给用户等确认。用户本人或动物主播用 persona.json → other_hosts 里的提示词模板。

### 3. 生成
- **本地 H3**：
```bash
python scripts/local-h3/h3c_run.py --image 形象图.png --text-file 提示词.txt \
  --chunks 4 --seconds 10 --width 864 --height 1280 --size-source Manual \
  --prefix koubo/xxx --out out/xxx.mp4
```
提交前先看它打印的 `#312` 摘要（段数/每段秒数/尺寸/步数）；先查 `/queue` 有残留就 `POST /interrupt`，否则会白等。**第一次一定要先跑 1 段 5–6 秒**（约 2 分钟）验证比例、形象、语速、界面，再跑全长。
  - **用户给了现成音频（要直接对口型，不是当音色参考）**：加 `--drive-audio 配音.wav`。音频总长必须 = `chunks × chunk_seconds`，脚本会自动校验并提示改法；成片音轨就是这段音频本身（实测 r=1.0），台词 `<d>` 留着不会念两遍。详见 references/local-h3-continuum.md §5.5。
- **Renoise 云端**：tasks.json 每 10 个一批 create_tasks → wait_tasks。要进场景（直播间、门店、街景）时先用 GPT Image 2.5 合成开场画面（人物参考图 + 场景描述，2k 约 23 积分），再把这张图当 Grok 的参考图。

### 4. 取片
- **本地**：`h3c_run.py` 自己从 `/history` 把 mp4 拉回来，不用下载器。
- **Renoise 云端**（美国 CDN 很慢，必须这样下）：download_results 拿链接 → 整理成 `urls.txt`（每行 `<taskId>.<ext> <url>`）→ `python3 scripts/rangedl.py`：每个文件 6 段 Range 并发、断点续传、下完 ffmpeg 解码校验。

### 5. 回听 + 抽帧 + 质检
- **本地 H3**：
```bash
ffmpeg -y -v error -i out.mp4 -ar 16000 -ac 1 out.wav
whisper-cli -m "$WHISPER_MODEL" -l zh -nt -np out.wav      # 台词是否一字不差、有没有截尾
python scripts/local-h3/sharpness.py out.mp4               # 分块有没有发虚，最低值 <100 就重跑
python scripts/local-h3/srtsplit.py out.wav 台词.txt out.srt  # 多段拼接专用，别用连续转写
```
  **必须抽帧看**：界面文字（状态栏/弹幕）有没有被念成乱码、人物跨段有没有换脸、比例有没有被拉长。
- **Renoise 云端**：`python3 scripts/assemble.py script.json ids.json --out 成片_完整版.mp4`（ids.json = {段 id: taskId}）：whisper 逐段转写比对文稿、只保留到说完后 0.25 秒、拼接、loudnorm -16。
- whisper `--prompt 原文` 会让个别段漏掉前半句，用中性提示「以下是普通话的句子。」。外语段按语言转写；日韩阿拉伯语不要加 `-ml 1`（会把多字节字符截断成乱码）。
- **每段抽 4 帧看一眼**：Grok 横屏口播偶尔自己烧字幕（提示词写了也挡不住），有就重拍那段。本地 H3 反过来的风险是「界面文字被抹掉」或「弹幕糊掉」，同样抽帧看。
- Grok 有时漏念开头的语气词：没影响意思就按实际口播改字幕，别为这个重拍。

### 6. 对齐 + 剪辑
**先判断要不要这一步**：本地 H3 出的 30–60 秒单机位口播，本身已经是成片（人物、台词、字幕都有），**默认不用再进 Remotion**，加包装会压掉直播感。用户明确要花字/包装/地图/弹幕组件时才往下走。

`python3 scripts/align.py script.json --out <工程>/src/tl.json` 出逐字时间轴，然后按 brief.json 的风格剪：
- **B 花字口播**：`bash scripts/new_edit.sh huazi-916 <工程>` → 写 `src/edit.json`（关键词、表情、卡片、作品展示、号召，字段见 references/huazi.md）→ `python3 scripts/check_edit.py <工程>/src` → 抽帧 → 渲染。
- **A 小林式**：`bash ~/.claude/skills/finance-explainer/scripts/setup_engine.sh <工程>`，按那边的拍表和画面语法做；数字人口播片段放进 host.json。
- **C / D / E**：`bash scripts/new_edit.sh reference/<目录> <工程>`，换 tl.json，按段重写 Scene（templates/reference/README.md）。
- **包装（每种风格都做）**：按 `references/packaging-presets.json` 里这个风格的默认包装排——开场 30 秒按 open 顺序、正文保证 stimulus_every_s 秒内有一个新视觉事件、讲到 per_beat 里那类内容就用对应组件、recurring 全片挂着。组件写进 `pack` 数组（字段见 references/packaging.md），手法依据见 references/packaging-playbook.md。用户点名要的手法（「加地图」「开场加预告」「加弹幕」「换成 MrBeast 那种」）在默认基础上加减。用户问「有哪些包装」先发 `assets/packaging/图鉴.jpg`。景深字（文字在人身后）要先跑 `scripts/cutout_video.py` 抠像，见 references/packaging.md。
- 声音：数字人视频轨一定 `muted`，人声单独铺一条；多段 Grok 原声用 `python3 scripts/voicefx/unify.py <输出目录> <片段…>` 统一频谱 + 同一个小房间混响（复用旧段时加 `--ref 旧片段目录`，场景/动物片段加 `--scene`）。BGM 压在人声下约 20 dB。
- 抽帧检查一定看过渡的中间帧和零间隔衔接处（上一条的尾巴会盖住下一条）。

## 参考
- **references/local-h3-continuum.md：本地 ComfyUI H3 Continuum 全流程**（环境、节点参数、字数密度、提示词格式、禁配乐、直播截图保留界面、采样步数、12 条踩过的坑、耗时表）。走本地必读。
- references/install.md：Renoise MCP 和本机环境的多种装法（只在缺的时候用）
- references/style-menu.md：五种风格、内容诊断、怎么问用户、brief.json
- references/packaging.md：47 个包装组件的用法和参数（pack 写法、9:16 自动适配）
- references/packaging-playbook.md：头部博主实测结论（节奏、开场公式、字幕、声音、号召、红线），完整报告在 references/research/
- references/packaging-presets.json：五种风格各自的默认包装
- references/huazi.md：花字模板 edit.json 字段、九种卡片、三档强度、写法习惯
- persona.json：白背心数字人 + 其他主播（用户本人、橘猫店长、柴犬主播）、提示词模板、动作库、多语言实测
- references/voice.md：换声音（MiMo 克隆 / 音色设计）
- references/new-avatar.md：从一张照片做新形象
- references/edit-styles.md：各剪辑工程的入口文件和声音统一做法
- assets/styles/：五种风格的预览图（给用户选的时候发）
- assets/packaging/：包装组件图鉴（47 格总览 + 每个组件一张）
