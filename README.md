# AI-Video

面向抖音的中文动画短视频制作技能。从主题、分镜与视觉方案开始，衔接已安装的视频技能，统一中文配音、字幕、预览检查和成片交付。

本仓库是代理技能与配套脚本，不是独立的视频生成服务。完整制作需要相应的画面工作流、素材和运行环境。

## 默认行为

| 项目 | 默认 |
| --- | --- |
| 视频 | 中文、9:16、1080×1920 |
| 配音 | edge-tts 云扬 `zh-CN-YunyangNeural` |
| BGM | 不添加；用户要求后才选曲和混音 |
| AI 科普片尾 | “关注我，掌握更多AI知识”，同步到旁白、分镜和字幕 |
| 字幕 | 随视频风格选择字体和字色，水平居中、无底色；需要衬底时用淡色半透明底 |
| 制作确认 | 首次先确认分镜、完整旁白、风格与时长，再正式配音、生成素材和渲染 |

用户本次要求覆盖默认。只要求方案时交付前期设计；已确认的方案或局部修订不重复索取同一批准。

## 可以做什么

- **知识图解**：用主体动作、图形和流程解释抽象概念。
- **角色情景**：先检查角色资产、动作与连续性，再制作动态分镜和动画。
- **3D 演示与生成式镜头**：按题材调用对应工作流，统一剪辑、声音和字幕。
- **修订已有视频**：定位受影响镜头，更新配音、时长、字幕和后续时间轴。

画面能力由外部技能提供。Lottie 播放器不会自动创建角色表演；生成式镜头需要提供方与预算。现有配音脚本按单音色生成，多角色对白需要另行接入音色映射。

## 安装

把本仓库放到代理的技能目录中，目录名建议为 `ai-video`，确保 `SKILL.md` 位于该目录根部。

Windows PowerShell 示例，适用于尚未安装该技能的目录：

```powershell
git clone https://github.com/jingtll/AI-video.git "$env:USERPROFILE\.agents\skills\ai-video"
python -m pip install -r "$env:USERPROFILE\.agents\skills\ai-video\requirements.txt"
```

已有 `ai-video` 时先备份并比较本地改动，再更新。不同代理使用自己的技能目录设置；安装后刷新技能列表或开启新会话。

### 运行环境

- Python：配音与体检脚本；当前验证版本为 3.11.9。
- Node.js：中文字幕和外部工作流脚本；当前验证版本为 24.15.0。
- 完整 FFmpeg / FFprobe：需要 MP3 编码、解码和混音能力；建议加入 PATH。Windows 脚本也会查找 WinGet 安装的 Gyan.FFmpeg。
- `edge-tts==7.2.8`：已写入 [requirements.txt](requirements.txt)，配音需要联网。
- HyperFrames CLI：执行预览、检查和渲染；当前实际检查版本为 0.8.138。
- 可用的中文字体：例如 Microsoft YaHei、Noto Sans SC 或 PingFang SC。跨机器交付要验证字体或打包允许分发的字体文件。

字幕默认加载固定版本 GSAP 3.14.2，因此默认预览需要网络。离线项目可提供本地 GSAP 文件，配置方法见下文。

### 外部技能

本仓库只包含 ai-video，不复制其他技能或依赖包。

| 用途 | 所需或按需使用的技能 |
| --- | --- |
| 视频入口与工程 | `hyperframes`、`hyperframes-core`、`hyperframes-cli` |
| 知识图解及共有分镜解析 | `faceless-explainer` |
| 视觉、动作、现有模块 | `hyperframes-creative`、`hyperframes-animation`、`hyperframes-registry` |
| 动态分镜、角色与连续性 | `storyboard-previsualization`，以及实际角色动画资产 |
| 素材与混音 | `media-use`、`hyperframes-audio` |
| 3D、生成式镜头 | 对应 `threejs-*`、`ltx-2-video` |
| 已有工程与剪辑交接 | `remotion-best-practices`、`jianying-editor` |
| 其他配音提供方 | `azure-speech`、`text-to-speech` |

中文字幕 CLI 直接使用 `faceless-explainer` 的分镜与尺寸解析器，默认从同级技能目录寻找；也可以通过 `--faceless-dir` 显式指定。其他框架工程只有采用相同数据契约时才能直接复用这些脚本，否则先做结构适配。

## 使用示例

在支持技能的代理中调用 `$ai-video`，例如：

```text
$ai-video 做一个 45 秒抖音 AI 科普动画，讲清楚大模型为什么会幻觉。
用浅色手绘风，云扬配音，不加 BGM。先给我分镜、完整旁白和视觉方案。
```

```text
$ai-video 分镜已确认。把第 2 镜头旁白改短一点，保留其他设计，继续制作。
```

完整制作流程与完成条件见 [SKILL.md](SKILL.md)。工作流选择见 [路线与技能衔接](references/routing.md)。

## 配音与字幕脚本

这些命令操作具体视频项目，不是在技能仓库中直接生成视频。先准备项目的 `SCRIPT.md`、`STORYBOARD.md` 与已确认的设计。

脚本口播采用 4 空格缩进，Frame 编号与分镜对应：

```markdown
## Line 1 — 开场 (Frame 1)
    大模型为什么会一本正经地说错话？
```

下列 PowerShell 变量分别指向技能目录、外部技能目录和视频项目；执行时替换项目路径：

```powershell
$aiVideoDir = "$env:USERPROFILE\.agents\skills\ai-video"
$facelessDir = "$env:USERPROFILE\.agents\skills\faceless-explainer"
$videoProject = "D:\Videos\my-ai-video"

python "$aiVideoDir\scripts\gen_narration.py" --project "$videoProject" --check-only
python "$aiVideoDir\scripts\gen_narration.py" --project "$videoProject" --segmented
python "$aiVideoDir\scripts\qa_narration.py" --project "$videoProject"
node "$facelessDir\scripts\audio.mjs" sync-durations --audio-meta "$videoProject\audio_meta.json" --storyboard "$videoProject\STORYBOARD.md"
node "$aiVideoDir\scripts\captions_zh.mjs" build --project "$videoProject" --faceless-dir "$facelessDir"
```

每一步退出码为 0 后再执行下一步。配音可用 `--frames 2` 局部更新；`--rate`、`--gap`、`--tail-pad` 可调。体检失败会阻止后续步骤，详情见 [中文配音与时长契约](references/voice.md)。

生成音频在临时目录校验后发布。捕获到文件替换失败时回滚；回滚也失败时保留备份并报告位置。多文件更新不保证断电或强制结束进程时的原子性。

### 字幕配置

在视频项目根目录创建 `ai-video.config.json`，下面是浅色画面的起始配置：

```json
{
  "captions": {
    "theme": "light",
    "font_family": "Microsoft YaHei",
    "font_size": 64,
    "background": "transparent",
    "top": 1382,
    "width": 778,
    "max_units_per_line": 12,
    "max_lines": 2
  }
}
```

省略 `left` 时按画布和字幕区域宽度水平居中。`theme: light` 默认深色字，`theme: dark` 默认浅色字；`color` 可以覆盖字色。需要淡色衬底时可用 `background: "rgba(255,255,255,.16)"`。

制作代理会根据 `frame.md` 将字体、颜色等映射到配置；字幕脚本本身不解析设计文档。具体位置需避让主体与平台 UI，上述坐标不是抖音官方安全区。

使用项目内 GSAP 时，设置 `captions.gsap_src: "assets/vendor/gsap.min.js"` 并提供对应文件；生成器会核对文件并计算完整性哈希。更多参数见 [抖音字幕与验收](references/douyin.md)。

## 验收与测试

在 HyperFrames 工程中检查布局、运行状态和真实画面。浏览器字幕检查必须满足 `window.__aiCaptionQA.ready === true` 且 `errors` 为空；随后按手机观看尺度回放，检查行宽、字体、遮挡与音画同步。导出后还要检查 MP4 解码、音轨和完整听感。

在本仓库根目录运行离线回归：

```powershell
python -X utf8 -m unittest discover -s tests -v
node --test tests/test_captions.mjs
```

测试覆盖脚本契约、音频解码与时间戳、局部更新、发布失败回滚、字幕分组、实际宽度布局逻辑以及居中/透明底/主题配置。TTS 网络边界使用测试替代数据，不等同于在线配音服务验证。生成字幕的实际预览已通过 HyperFrames 严格检查；角色、3D、生成式镜头仍按各自工程验收。

`evals/evals.json` 提供代表性简报及期望行为，不是自动运行的端到端视频测试。

## 目录

```text
SKILL.md              代理入口与完整制作流程
requirements.txt      Python 配音依赖
references/           路线、配音、字幕与音乐参考
scripts/              配音、体检、字幕及可选音乐工具
tests/                离线回归与隔离预览样例生成器
evals/                技能行为评测简报
```

音乐默认关闭；只有明确需要时使用音乐工具，素材获取、许可记录和混音验收见 [音乐参考](references/music.md)。本仓库不包含第三方技能、角色资产、生成的视频或字体文件。
