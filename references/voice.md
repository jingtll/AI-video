# 中文配音与音频元数据

## 契约

SCRIPT.md 的缩进口播是 TTS 输入；Frame 编号连接分镜、音频和字幕。标题推荐半角括号，解析器兼容全角；Line 编号不需要与 Frame 编号相同。空文本、重复 Frame、无有效脚本会立即失败。

若 STORYBOARD.md 存在，预检核对其有口播镜头与脚本镜头集合。无口播镜头不出现在 SCRIPT.md；兼容标准 voiceover/vo/voice_over/narration 字段。纯无声/无口播项目按画面工作流跳过此适配器。

~~~json
{
  "bgm": null,
  "bgm_pending": false,
  "voices": [{
    "frame": 1,
    "path": "assets/voice/01.mp3",
    "duration_s": 3.5,
    "audio_duration_s": 3.0,
    "tail_pad_s": 0.5,
    "source_text": "这一行是当前旁白。",
    "voice": "zh-CN-YunyangNeural",
    "rate": "+8%",
    "words": [{"id": 0, "text": "这一行", "start": 0.1, "end": 0.8}]
  }],
  "sfx": []
}
~~~

words.start/end 使用秒、镜头内相对值；字幕生成器加分镜起点。duration_s=最终音频解码长+tail_pad_s；尾气口是镜头保留时间，不宣称是音频文件里额外合成的呼吸声。新增字段与上游组装器兼容。

## 生成与修订

~~~bash
python "<AI_VIDEO_DIR>/scripts/gen_narration.py" --project . --check-only
python "<AI_VIDEO_DIR>/scripts/gen_narration.py" --project . --segmented --gap 0.32 --tail-pad 0.5
python "<AI_VIDEO_DIR>/scripts/gen_narration.py" --project . --frames 2,3 --segmented --extra-split "这个地方，"
python "<AI_VIDEO_DIR>/scripts/qa_narration.py" --project .
~~~

--check-only 不调用网络、不创建音频，检查脚本/分镜集合、镜头选择和已有元数据编号。全量/局部更新保留 bgm/sfx 字段，移除不在当前口播脚本中的遗留 voices 条目；旧音频文件不删除。重复 voices 报错，不静默折叠。成功前在临时目录制作，TTS 或解码失败时保留原有音频和元数据。捕获到文件替换失败时回滚已更新文件；若回滚也失败，报出保留原文件的备份目录并停止。多文件更新不保证断电或进程被强制结束时的原子性。

edge-tts 使用 WordBoundary；缺失时停止。不要只检查是否输出了 mp3。依赖版本固定，当前回归环境是 Python 3.11、edge-tts 7.2.8；requirements.txt 可用于复现，安装/升级不是每次制作的默认步骤。

## 分段时间轴

压缩音频的容器时长不足以作为拼接依据。每段解码为 24kHz、mono、s16 PCM，在采样域裁头尾、插零填充停顿和拼接，再编码一次。偏移按实际插入采样数计算，最终文件重新解码测长。音频来源可能是 CBR 或 VBR，不以“edge 一定输出 VBR”作为依据。

尾部静音判断使用样本绝对值；正负振幅均视为信号。当前样本阈值是简单裁剪辅助，不代替完整音频 VAD。词时间戳来自提供方，需实际试听核验；不能宣称所有编码和提供方误差都为零。

## 体检

| 检查 | 默认 | 修改方式 |
|---|---|---|
| 语速 | 3.0–5.6 中文字/秒，拉丁/数字按词计 | --min-rate / --max-rate；属于制作启发 |
| 镜头尾气口 | 至少 0.35s | --min-tail；生成时改 --tail-pad 并重新同步 |
| 最长无停顿 | 最多 6.5s | --max-run；生成时句读拆分 |
| 停顿阈值 | 大于 0.25s 视为一次气口 | --pause-threshold |
| 完整性 | 音频/脚本镜头集合相同，无重复/遗留 | 修复脚本或重生成 |
| 实际音频 | 文件存在、在项目中、能解码且非空 | 重新生成 |
| 时间戳 | 非空、有限、有序、无明显重叠，不超出实际音频 | 检查提供方和合并偏移 |
| 时长与版本 | 元数据与解码长误差不超过 0.08s；有 source_text 时与当前脚本相同 | 重生成，再同步分镜 |

退出码 0 表示通过，1 表示镜头质量失败，2 表示输入/契约错误。两种非零都阻止制作链继续。legacy 元数据没有 source_text 时不能证明脚本版本一致，要试听或重新生成后获得版本关联。

阈值适合讲解起点；搞笑、角色对白和有意悬念可以按项目调整并记录依据。不靠不断提高阈值掩盖听感问题。

## 与上游共享

audio.mjs sync-durations 可以读取外部 voices。audio.mjs generate/fetch-sfx 从引擎 sidecar 重建 audio_meta，不自动保留本技能的外部配音。SFX 在中文配音前获取；后来补 SFX 时只合并该数组并体检。

音频改变后同步分镜，重建镜头动作、字幕和后续起点；禁止只替换 mp3 却继续使用旧 data-duration。
