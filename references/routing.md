# 动画路线与技能衔接

ai-video 管中文与抖音制作偏好，HyperFrames 入口管工作流选择。已有工程先续作；新建任务只做一次入口路由。读匹配的 hyperframes/references/routes/<workflow>.md，确认契约后进入该工作流，不用“动画”一词直接强制 faceless-explainer。

| 主要画面 | 工作流与能力 | 开始前验证 |
|---|---|---|
| 抽象概念、流程、图解、数据 | faceless-explainer + hyperframes-animation + hyperframes-registry | 视觉比喻能解释真实机制；有对应模块则复用 |
| 吉祥物、角色动作、情景剧情 | 由 HyperFrames 路由；通常 general-video + storyboard-previsualization + Lottie 适配器 | 角色资产、姿态/动作库、人物与道具连续性 |
| 3D 原理、空间关系、产品演示 | 通常 general-video + Three.js 适配器；加载用到的 threejs-* 技能 | 模型来源、渲染性能、镜头调度、确定性 seeking |
| AI 生成的人物、环境或电影感片段 | storyboard-previsualization + ltx-2-video；生成素材后导入时间轴统一剪辑 | 当前模型/服务能力、预算、连续性参考、重试上限 |
| 已有 React/Remotion 工程 | remotion-best-practices | 工程依赖、预览与导出约定，复用当前实现 |
| 剪映草稿和人工精修 | jianying-editor | 实际剪映版本、草稿可打开、素材路径和导出状态 |

Lottie 是角色资产的播放与时间轴适配，不负责凭空创造骨骼表演。优先复用用户资产或许可明确的动作文件，搜索 lottie-character-walk 等模块。角色自己的动画负责肢体和脚步，GSAP 负责舞台位置，两者速度要匹配。

复杂 3D 按需读取 threejs-fundamentals、loaders、animation 等，不一次加载全部技能。生成式镜头仅处理适合生成的镜头；可靠的字幕、数字、品牌文字与转场在合成阶段制作。

## 声音提供方

默认 edge-tts 云扬。这条路线需要网络，但无需 HeyGen 登录。预检先验证当前 edge-tts 支持 WordBoundary。生产依赖固定版本，更新后回归测试再推进。

用户要求更细的情绪/停顿控制时，读取 azure-speech（SSML）或 text-to-speech（ElevenLabs）评估可用能力；用户未选择时沿用当前音色，不自动切换。

多角色对白先锁定“角色 → 提供方与音色”，分角色合成后统一合并词时间戳。现有 gen_narration.py 是单音色旁白适配器，不把它描述成已支持自动多角色对白。没有提供方时间戳时做实际对齐，不能均匀估算后声称是词级时间戳。

## 工作流交接

1. 锁定 BRIEF.md 的 workflow、flow、storyboard 和声音约束。
2. 按所选工作流完成设计、构图和媒体准备。
3. edge-tts 接管 TTS 阶段；输出 audio_meta.json 的共有 frame-keyed shape。
4. 只有采用同一 SCRIPT/STORYBOARD/audio_meta 契约的工作流才能直接接本技能脚本。其他工程先做结构适配，不改名冒充兼容。
5. 中文字幕用 captions_zh.mjs；继续所选工作流的组装/验证/预览/导出步骤。

角色生成、付费服务和大模型下载的授权来自对应技能与用户本次指令。先给出具体镜头、模型、预算及输出计划，再执行其授权范围。
