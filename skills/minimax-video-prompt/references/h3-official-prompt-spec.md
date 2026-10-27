# MiniMax H3 官方 Prompt 规范（HuggingFace docs 精华提炼）

来源：https://huggingface.co/MiniMaxAI/MiniMax-H3/tree/main/docs
- VIDEO_PROMPT_WRITING_GUIDE_base_en.md（T2VA/I2VA/FL2VA/L2VA）
- VIDEO_PROMPT_WRITING_GUIDE_ref_en.md（全参考模式）

## 一、任务类型（4+1 种）

| 类型 | 含义 | 参考图角色 |
|---|---|---|
| T2VA | 纯文生视频 | 无 |
| I2VA | 首帧图生 | Picture 1 = 0.00s 首帧 |
| FL2VA | 首尾帧 | Picture 1 = 开头，Picture 2 = 结尾 |
| L2VA | 尾帧 | Picture 1 = 最后一帧（推断前序状态） |
| Ref（全参考） | 多素材混合 | Subject/Picture/Video/Audio 四类标签 |

## 二、Prompt 三段式结构（base 模式）

```text
# Part 1（仅 I2VA/FL2VA/L2VA 需要，T2VA 直接进 Part 2）
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.

# Part 2 三个核心字段
integrated_multimodal_description: [Shot 1] ... [Shot 2] At 00:03.500, ...

overall_soundscape: 环境音+物理动作音+非语言人声（1-4 句）

non_diegetic_music: BGM（角色听不到，只有观众能听到；1-3 句）
```

## 三、镜头格式规范

- `[Shot 1]` 无时间戳；后续 `[Shot 2] At MM:SS.mmm`（严格递增）
- 切镜用语：`the camera cuts to` / `the shot transitions to` / `the shot switches to`；用户明确要求时才用 cross-dissolve/fade/wipe
- 仅距离/角度微调 → 用镜头运动而非切镜

## 四、镜头运动三要素（Motion Type + Amplitude + Speed）

| 维度 | 可选值 |
|---|---|
| 运动类型 | Zoom In/Out、Push In/Out、Pan Left/Right、Truck Left/Right、Tilt Up/Down、Pedestal Up/Down、Arc Shot、Tracking Shot、Static Shot、Shake Slightly/Strongly、POV、Roll Clockwise/Counterclockwise |
| 振幅 | with small amplitude / with large amplitude（中等省略） |
| 速度 | at slow speed / at fast speed（正常省略） |

写法示例（自然句，不堆标签）：
```text
The camera pushes in with small amplitude at slow speed toward the folded letter in her hands.
```

## 五、说话人 ID + 台词系统（关键）

- 发声者用稳定 ID `(S1)` `(S2)`，跨镜头不变；齐声用 `(S1,S2)`
- 首次出现给足身份信息：角色类型/年龄/性别/是否出镜/音高/音色/语速/口音
- 台词格式：`<d>[Language] 原文</d>`——**原文逐字保留，不翻译不改写**
- **台词版式（2026-10-04 实测定稿）**：`<d>` **另起一行、行首即标签**；delivery 独立成一行、冒号收尾（`S1 林婉台词（轻蔑、句尾下压）：`）；`</d>` 之后只跟画面动作。禁把标签揉进叙述句（如「…的语气说 `<d>…</d>`」），禁在 delivery 行用「说」字
- 画外音：`says in an off-screen voiceover` + 紧接声明"lips remain completely closed"
- 跨镜头台词：`<scenetrans>`；被视频结束截断：`<cutoff>`
- 画面内可见文字：英文双引号包裹，如 `A red neon sign reading "营业中"`

## 六、全参考模式（Ref）六段式

```text
subject_definitions: 定义每个参考标签（Subject/Picture/Video/Audio）
summary: [任务类型] 一句话总结
retention_analysis: 每个标签的保留关系
detailed_description: 逐镜头主描述（350-500 英文词）
overall_soundscape: 环境音
non_diegetic_music: BGM
```

四类标签：
| 标签 | 含义 |
|---|---|
| `<Subject N>` | 可复用可见内容（人/物/场景/服装/风格/动作） |
| `<Picture N>` | 具体帧锚点（首帧/关键帧/尾帧/分镜参考） |
| `<Video N>` | 整视频关系（编辑源/续写起点/节奏结构） |
| `<Audio N>` | 音频（复制/参考音色/参考BGM风格） |

任务类型前缀（可 + 组合）：
`[keyframe completion]` / `[reference generation]` / `[video editing]` / `[video continuation]` / `[audio reuse]` / `[audio reference]`

保留关系标记：
- 可见内容：`fully_preserved` / `partially_preserved` / `attribute_transfer` / `weak_reference`
- 音频：`fully_copy` / `partially_copy` / `reference` / `weak_reference`

## 七、声音三层分工（重要借鉴）

| 层 | 归属字段 | 内容 |
|---|---|---|
| 台词+同期声 | multimodal/detailed description | 对白、演唱、画面内声音事件 |
| 环境音+动作音 | overall_soundscape | 风/雨/脚步/布料/碰撞/呼吸/笑声 |
| BGM | non_diegetic_music | 只有观众听到，写明乐器+速度+动态，不用抽象情绪词 |

## 八、风格声明（[Shot 1] 开头）

Cinematic / live-action / 2D-animated / 3D CG / claymation / watercolor / vintage film

## 九、与中文模板的对应关系

| 中文模板（minimax-video-prompt） | 官方规范 |
|---|---|
| 人物设定段（10 项） | subject_definitions + (Sx) 首次身份 |
| 分镜头（起止秒+景别+运动） | [Shot N] At MM:SS.mmm + 镜头运动三要素 |
| 台词 {} 包裹 + 语气标注 | <d>[语言] 原文</d> + (Sx) + delivery 描述 |
| BGM+音效混写 | 分三层：description / soundscape / music |
| 音色适配指南 | (Sx) 首次出现时给 pitch/timbre/rate |
