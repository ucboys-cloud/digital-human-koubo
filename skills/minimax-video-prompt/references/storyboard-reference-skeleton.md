# storyboard reference skeleton

> 2026-09-18 从 SKILL.md 迁出的示例 / 工具模块（规则句仍留在 SKILL.md 正文）。
>
> ⚠️ **2026-10-09 修正**：首帧行原写 `is fully referenced`——那是**单一场景图当第一帧**才用的写法。开发板/分镜图/宫格图当参考时必须用 `storyboard reference` 句式 + 显式声明「不是第一帧」，否则模型会把整张开发板复刻成视频开头几帧。本骨架已改正，勿回退。

---

## 分镜参考图固定骨架模板

> 原 SKILL.md 行 1739-1767

**经实战验证的固定骨架**（2026-08-22 中文信息增量版式，9 条已验证）：

```text
For the target video, <Picture 1> is a storyboard reference for [Shot 1] through [Shot N], defining their layout order, character design, costume, hairstyle, face, age, body proportions, and overall anime film style. <Picture 1> is not the first frame of the video; the target video begins directly with Shot 1 itself.

[reference generation]
<Picture 1> 是动画开发板参考图，用于提供 [角色/场景描述]、服装、发型、配饰、分镜顺序、景别、构图和镜头运动规划。
开发板中的角色设计表、分镜网格、红色边框、蓝色运镜箭头、镜头编号、时间标注、手写文字和纸张背景只作为制作参考，不进入最终视频画面。蓝色箭头仅用于辅助判断镜头运动方向，最终镜头运动以以下文字描述为准。不要把开发板直接生成成静态分镜图。
<Picture 1> is a storyboard reference for [Shot 1] through [Shot N], defining their viewpoint, subject placement, shot order, visual style, and camera movement planning.

8K RAW 超高清，原创 [题材] 动画短片《[片名]》，16:9 横屏，总时长 [N] 秒。保持参考图中的 [锁定元素] 一致。[角色] 是全片仅有的主要角色，不新增主要人物。画面保持 [色调1] 与 [色调2] 之间的色彩变化。

机位始终位于 [主体] 身后或侧后方，不跨越运动轴线。[位置/视线规则]。

integrated_multimodal_description:

[Shot 1] [锁定初始状态]。她/他 [做了什么]，状态如何变化。镜头 [运镜]。声音：[对位声音]。

[Shot 2] At 00:02.000, [承接上一镜结束状态]，[新动作]。镜头 [运镜]。声音：[对位声音]。

...
[Shot 8] [宽景 / 情绪镜]。

overall_soundscape: 不生成背景音乐，背景音乐后期统一添加。声音按画面事件分时进入：[按镜列出对位声音]。
non_diegetic_music: N/A

全程无字幕、无文字覆盖、无水印、无社交平台界面。允许出现 [对白 / 独白 / 无]。参考图中的 [板上元素清单] 不进入视频画面。只生成连续的动画电影镜头，不生成静态开发板。
```
