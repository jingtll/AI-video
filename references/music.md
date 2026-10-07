# 可选 BGM 与最终声音验收

默认无 BGM。用户选择后才读取音乐来源或运行本节混音；云扬默认不因 BGM 选择改变。

## 选曲

media-use 负责素材检索、复用和来源记录。可选择用户提供的音频、许可适合本次发布的素材库曲目，或 synth_bgm.py 生成的原创和弦垫乐。点名曲目拿不到时让用户决定换曲或取消。

素材记录曲名、页面、许可、下载/验证日期与本地文件。平台曲库的可用范围与外部素材许可分别核实；不宣称“免费”意味着无版权或任何发布场景都可用。

~~~bash
python "<AI_VIDEO_DIR>/scripts/pick_bgm.py" a.mp3 b.mp3
python "<AI_VIDEO_DIR>/scripts/synth_bgm.py" --out assets/bgm/synth.mp3 --dur 60 --mood bright
~~~

pick_bgm 的密度、动态和亮度指标是候选筛选辅助，选曲仍要匹配故事和实际听感；不自动以方差最低作为最佳。合成垫乐是可选能力，不把同一种和弦进行套在所有题材上。

## 混音

已放置音轨优先读 hyperframes-audio，确认预览/渲染一致。原技能曾遇到音轨配置正确但成片缺 BGM 的经验，应记录 CLI 版本和最小复现；不推断所有当前版本的 track 11 都不可用。

采用现有后混路线时，渲染阶段不同时加入同一首 BGM，防止重复叠加：
~~~bash
python "<AI_VIDEO_DIR>/scripts/mix_bgm.py" --video renders/video.mp4 --bgm assets/bgm/bgm.mp3 --out renders/video_bgm.mp4
~~~

mix_bgm 使用旁白音轨侧链压缩 BGM、淡入淡出、amix normalize=0 和视频 stream copy。它需要输入视频已有音轨；无旁白/BGM-only 视频使用所选框架的音频组装流程。后混输出成功不等于声音已验收，保留原文件直到验证完成。

## 最终成片声音检查（纯旁白也执行）

~~~bash
ffmpeg -v error -i renders/video.mp4 -f null -
ffmpeg -i renders/video.mp4 -af "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json" -f null -
~~~

第二条仅分析/试处理到 null，不修改成片；记录 JSON 中 input_i / input_tp / input_lra。-16 LUFS、-1.5 dBTP 是可选项目目标，不标为抖音官方要求。若调整响度，明确目标并输出新文件，再次测量与试听。

旁白窗口和气口窗口的 volumedetect 可用于比较混音前后相对音量。原经验值约 -24dB/-30dB 不是通用合格线；窗口接近静音只能提示进一步检查，不能单凭一个值证明底乐必定缺失。

完整试听开头、最密集旁白、动作音效、气口和结尾；确认无削波、重复配乐、人声被遮蔽、异常静音或切尾。验证最终交付的文件，再在交付信息写明“无 BGM”或所用曲目和验收状态。
