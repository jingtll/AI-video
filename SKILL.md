---
name: ai-video
description: 面向抖音的中文动画短视频制作与修订编排。用于知识图解、角色情景、3D 演示及生成式镜头的短视频；先确认分镜和视觉方向，再调用已安装的视频技能制作，统一中文配音、字幕和成片验收。默认云扬配音、9:16、无 BGM；只请求方案时交付前期设计。
---

# AI-Video — 中文动画短视频编排

负责简报、设计确认、工作流衔接、中文音频/字幕适配和交付验收。画面制作由已有视频技能负责；先读 `hyperframes` 入口，依据交付物选择工作流。用户指定已有框架或工程时沿用。技能编辑/评估属于技能维护，不触发视频制作流程。

## 默认与授权

- 默认中文、1080×1920、edge-tts `zh-CN-YunyangNeural`（云扬）、无 BGM。用户本次要求优先于既有项目、已记录偏好和默认值。edge-tts 需要联网，不能称为离线引擎。
- AI 科普类视频默认片尾加入“关注我，掌握更多AI知识”，同步写入旁白、字幕和分镜；用户明确取消或指定其他结尾时遵循用户要求。字幕默认适配视频风格、水平居中、无底，必要时使用淡色半透明底。
- 第一次制作先呈现分镜、旁白全文、视觉方向和预期时长，等用户确认后才做正式 TTS、素材生成和渲染。用户已批准同一方案时继续执行；只做方案的请求到前期交付为止。
- 局部文案/动作修改按用户指令执行；题材、整体风格或叙事结构发生变化时先更新受影响方案。已授权的修改不重复索取同一批准。
- 指定曲目不可获得时让用户选择换曲或取消；音色切换依照用户选择。付费生成/大模型下载遵循对应技能的明确授权规则。

## 按需读取

| 当前任务 | 读取与分工 |
|---|---|
| 新建视频或选择画面工作流 | `hyperframes/SKILL.md`，然后读本技能 `references/routing.md` |
| 知识图解 | `faceless-explainer`；读其 story-design、visual-design 和 `hyperframes-creative/references/story-spine.md` |
| 角色、空间动作、生成式镜头，或需要验证剪辑节奏 | `storyboard-previsualization`：镜头动作、连续性与动态分镜 |
| 动效与角色动作 | `hyperframes-animation`；角色用其 `adapters/lottie.md`，3D 用 `adapters/three.md` |
| 命名效果、图表、角色块、转场 | `hyperframes-registry`，先检索现有模块再设计 |
| 配音/字幕 | `references/voice.md`；其他提供方按 routing.md 接入 |
| 抖音构图、节奏、移动端验收 | `references/douyin.md` |
| 用户要求 BGM | `references/music.md`；素材获取用 `media-use`，已放置声音混音用 `hyperframes-audio` |
| 导出剪映工程或继续人工剪辑 | `jianying-editor` |
| 已有 Remotion 工程 | `remotion-best-practices`，保持该工程的预览和导出流程 |

`faceless-explainer` 面向文字、抽象图形、图解和数据可视化。角色剧情或镜头生成由 `hyperframes` 选择匹配路线；中文版音频/字幕适配是能力，不强制改变画面工作流。

## 0. 确定制作状态

先读既有 `BRIEF.md`、`STORYBOARD.md` 和项目配置，复用已确认决定。全新任务遵循 HyperFrames 的 intent-interview，检查偏好和配方，再从用户输入提取主题、观众、一个核心信息、题材、时长、参考、交付形式、声音及预算；只补问无法合理推断的关键缺口。按入口路由表匹配后读取 `references/routes/<workflow>.md`，核对契约，再把锁定简报交给该工作流。

进入正式 HyperFrames 制作时按入口要求运行 `npx hyperframes usage --json`，里程碑复查；不可用或 unknown 时如实记录，不猜测余额。技能安装/更新遵循 skill-lifecycle 与 plugin-installation：插件包由插件管理器更新，独立技能按对应授权处理；已有更新授权不重复询问，缺失工作流不能凭记忆冒充已安装。

简报采用 HyperFrames 的 brief-format：`workflow / flow / storyboard / destination / aspect / language / message / audience / length / voice / style_preset`。默认 `storyboard: yes`；额外制作偏好写入 Notes。声音约束包括 `bgm: none`；分镜的音乐字段用 `music: none`。按 brief-contract 记录允许的偏好键。

**完成条件：** 能说明谁看、看完懂什么、采用哪条画面路线；既有批准和当前修改范围清楚。

## 1. 前期设计与确认

先写方案，再初始化正式项目。新项目可在独立前期目录准备文档；`hyperframes init` 只对空目标目录执行，之后复制已确认的前期文档。已有工程直接续作。

- 视觉设计读取 `hyperframes-creative` 的 house-style、video-composition，再选择符合题材的预设。配色、字体、字幕避让区统一写入 `frame.md`；CJK 字体实际可用性需要验证。
- `STORYBOARD.md` 使用当前 storyboard-format 必填字段。每个镜头有稳定数字编号、叙事作用、主体动作、观众焦点、时长、声音、连续性锚点、素材来源和验收标准。时间窗口写在镜头正文中，避免用会被解析成新镜头的 `## Scene N` 标题。
- 旁白是 `SCRIPT.md` 中 4 空格缩进的文本；推荐标题 `## Line 1 — Hook (Frame 1)`。适配器兼容全角括号；重复编号、漏缩进和空脚本会报错。无口播镜头不写脚本段落。
- 主体动作承担解释：例如缓存用“第一次到仓库取物，第二次从身旁抽屉取同样物品”，而不是只出现定义和箭头。每个镜头明确发生的变化及其作用。
- 事实、数据和具体产品机制按来源核实。科普与剧情采用各自叙事结构；AI 科普结论之后自然接入“关注我，掌握更多AI知识”，在方案中列出片尾旁白和画面并计入时长，避免重复添加。其他题材按内容需要决定 CTA。
- 给用户呈现“时间 / 旁白 / 画面与动作 / 叙事作用”的表格，附风格与时长说明，获得首次方案确认。

**完成条件：** 方案获得确认；只请求前期设计时交付上述文档并停止。

## 2. 动态分镜与初始化

对于角色、复杂镜头或节奏风险，按 `storyboard-previsualization` 用粗图、占位动作和临时声音做动态分镜。已经确认的布局可复用；简单图解可以用低成本时间轴预览。临时声音与正式配音区分标记。

按已选工作流初始化：
```bash
npx hyperframes init "<proj>" --non-interactive --example=blank --skill=<workflow>
```
将确认的简报、分镜、脚本和设计写入项目。记录 CLI 和依赖版本；按步骤 0 的安装/更新规则确认工作流可用。读取对应工作流的阶段要求，不重复做其入口访谈。字幕默认加载固定版本的 GSAP CDN，因此预览/渲染也需要网络；离线工程把已验证的 GSAP 文件放入项目，并设置 captions.gsap_src，不能把缺失运行依赖当成验收通过。

后续相对路径均以项目根目录为工作目录。`<AI_VIDEO_DIR>` 为本技能真实安装目录，`<FACELESS_DIR>` 为 faceless-explainer 安装目录，命令使用绝对技能路径。

**完成条件：** 项目与锁定方案一致；动态分镜能说明动作、焦点、切镜和停顿为何成立。

## 3. 中文配音与时长同步

edge-tts 路线替代工作流自身的 TTS 阶段，其他阶段继续按所选工作流执行。
```bash
python "<AI_VIDEO_DIR>/scripts/gen_narration.py" --project . --check-only
python "<AI_VIDEO_DIR>/scripts/gen_narration.py" --project . --segmented
python "<AI_VIDEO_DIR>/scripts/qa_narration.py" --project .
node "<FACELESS_DIR>/scripts/audio.mjs" sync-durations --audio-meta ./audio_meta.json --storyboard ./STORYBOARD.md
```

逐条检查退出码，非零停止，不靠终端最后一行判断。先完成脚本预检再请求 TTS；音频在临时目录合成和校验，成功后替换。分段合成在 PCM 域拼接；最终文件解码后记录真实时长。字幕需要 WordBoundary；缺少时间戳表示字幕数据缺失，不表示配音静音。

`--gap / --tail-pad / --rate` 是可调制作参数；默认停顿只是讲解起点，不是所有题材的固定节奏。阈值和角色多音色路线见 voice.md。

SFX 由 `media-use` 获取。如果调用上游 `audio.mjs fetch-sfx`，在本技能配音之前执行；它从引擎 sidecar 重写元数据，不保留外部 voices。已有配音后新增 SFX，只合并 sfx 字段并重跑体检，不能整体覆盖 audio_meta。

**完成条件：** 有口播镜头与音频一一对应，实际文件和时间戳有效，体检退出码 0，分镜时长已同步。

## 4. 动画制作

按选定工作流构建镜头。使用确定性、可 seek 的时间轴，遵守 `hyperframes-core`；复杂动作读相关 runtime 适配器。角色表演依赖实际动画资产/骨架或生成镜头，先验证可用性。

在分镜中安排整个镜头的动作发展，避免全部内容开头出现后无意义停滞；必要的理解停顿可以保留。采用 `animation-map.mjs` 辅助检查运动空档，再判断其叙事作用。

faceless 路线使用其 frame-packets builder；以实际 UTF-8 字节限制为准，规则数量不保证包大小。单帧子代理按当前可用并发容量分波派发；无子代理能力时串行执行相同角色规范。共享素材和注册模块由编排器先准备，失败只重派受影响镜头。

**完成条件：** 镜头实现已确认的动作、连续性与视觉规范；音频改变引起的时长和动作节拍变化已重建。

## 5. 中文字幕与组装

使用本技能的中文适配器，不调用上游英文分组器：
```bash
node "<AI_VIDEO_DIR>/scripts/captions_zh.mjs" build --project . --faceless-dir "<FACELESS_DIR>"
```
输出兼容的 `caption_groups.json` 和 `compositions/captions.html`。中文不插词间空格，中文标点参与断句；字幕按行宽预算、停顿、时间和镜头边界分组，不推算不存在的逐字时间戳。

生成字幕前，按 `frame.md` 的实际视频风格自动写入项目 `ai-video.config.json` 的 `captions`：字体、字号、颜色随主视觉协调，浅色画面用深色字，深色画面用浅色字，默认无底；需要底色时使用淡色半透明底。省略 left 时字幕区域自动水平居中，文字始终居中；纵向位置避让主体和平台 UI。可调整行宽和显示时长，示例见 douyin.md。适配器不直接解析设计文档或继承英文 preset skin，由制作代理完成样式映射，再用真实画面验证对比度。已有项目未被明确选定的旧黑底/偏左样式应更新为当前默认；用户明确指定的样式保留。

继续执行所选工作流的组装、转场和验证步骤。faceless 路线：
```bash
node "<FACELESS_DIR>/scripts/assemble-index.mjs" --storyboard ./STORYBOARD.md --hyperframes .
node "<FACELESS_DIR>/scripts/transitions.mjs" inject --storyboard ./STORYBOARD.md --hyperframes .
node "<FACELESS_DIR>/scripts/transitions.mjs" verify --storyboard ./STORYBOARD.md --index ./index.html
```

**完成条件：** 镜头数与分镜一致；voice 数等于有口播镜头数；字幕和音轨存在且时间吻合。无口播项目按所选工作流跳过中文配音适配。

## 6. 预览与验收

```bash
npx hyperframes lint
npx hyperframes check --timeout 15000
npx hyperframes snapshot --at <关键时间>
```

打开实际预览，读取 `window.__aiCaptionQA`：必须 ready=true 且 errors=[]；这是实际字体宽度检查。检查每个镜头的中点、首个动作、最终揭示、转场前后和晚入场元素，按 douyin.md 叠加 UI 遮罩，在手机尺寸实时回放。

lint/check 错误必须定位和修复。仅凭错误落在转场/入场时间内不能豁免；需要豁免时，在 `QA.md` 记录时间、截图、回放结果和原因。未通过的检查不能写成通过。

**完成条件：** 中文字形、字幕行宽、焦点、连续性、音画同步和手机可读性均有证据；完整实时回放没有解释不清的停滞或遮挡。

## 7. 导出与交付

按所选框架导出；HyperFrames：
```bash
npx hyperframes render --skill=<workflow> --quality delivery --output renders/video.mp4
ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,r_frame_rate:format=duration -of json renders/video.mp4
ffmpeg -v error -i renders/video.mp4 -f null -
```

确认最终 MP4 可解码，视频规格符合简报，有声项目存在音轨，首尾和各镜头衔接正常。完整听成片；响度/真峰值测量见 music.md，适用于纯旁白版。只有用户要求 BGM 才取曲、混音，混后重新检查导出文件。

交付 MP4、实测时长/规格、BGM 状态、字幕与配音状态、镜头修改入口及 QA 结果。封面/发布文案按简报交付；不自动发布。

## 修订与验证

定位镜头及依赖：仅文案/动作修改复用其他镜头；配音变更需重算受影响镜头时长、字幕和后续起点；增删镜头、全局风格或核心设定变化，重建实际受影响范围。重新组装、预览和导出，不强制局部重做或全量重做。

修改本技能后先运行离线回归测试，再用代表性简报验证路由和确认行为：
```bash
python -m unittest discover -s "<AI_VIDEO_DIR>/tests" -v
node --test "<AI_VIDEO_DIR>/tests/test_captions.mjs"
```
