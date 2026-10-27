# 五技能参考如何进入现有制作链

研究核对日期：2026-10-23。参考公开视频的部分播放帧及下列官方main；抽帧不能写成完整观看或听取。视频呈现“HyperFrames分镜→Whisper字级稿→video-use粗剪/调色→video-shotcraft镜头动效→Remotion渲染”，片尾留人类审美把关；另出现talkcraft字幕名称不一致。这是参考呈现，不是五个软件已经安装、接口已互通或收益已实测。

| 能力与官方入口 | 当前判断与本skill接法 |
| --- | --- |
| [HyperFrames](https://github.com/heygen-com/hyperframes) | 既可设计分镜也能完整渲染HTML视频；与Remotion选一主渲染，或只交付局部叠层，不强行中转 |
| 本地Whisper/字级边界 | 优先复用已安装模型/现有稿件；记录模型与选项，实际转换并校对后才声称字级适配可用 |
| [video-use](https://github.com/browser-use/video-use)、[SKILL](https://github.com/browser-use/video-use/blob/main/SKILL.md) | 0.11.0已安装固定版本原生EDL渲染与切点助手并实际调用，转写云路径未启用，见[upstream](../docs/upstream.md) |
| [video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft) | 0.11.0已安装选定原版组件/demo并实际通过Remotion调用；不分发/运行全套音频、图库或工具，见[upstream](../docs/upstream.md) |
| [Remotion](https://www.remotion.dev/) | 继续已有逐帧确定性合成与依赖复用；有真实验证的主链优先 |

官方[video-use转写代码](https://github.com/browser-use/video-use/blob/main/helpers/transcribe.py)当前默认`scribe_v1`，上传WAV至ElevenLabs并使用`ELEVENLABS_API_KEY`；没有现成Whisper backend参数。不能把演示中的Whisper、另一个工具的选项或模型可用性说成video-use已有本地后端。

[video-talkcraft README](https://github.com/Vincentwei1021/video-talkcraft/blob/main/README_EN.md)包含本地对齐及`--backend whisper`，属于另一工具；其[LICENSE](https://github.com/Vincentwei1021/video-talkcraft/blob/main/LICENSE)要求商业使用事先授权。授权未确认时不用于商业软件宣传，也不因视频名称相近而自动安装。外部仓库/许可证会变，决定接入前按当时版本复核；本次只参考方法，不附带第三方代码、音乐、人物或成片。

从参考中实际新增的是[字级剪辑计划、语义分镜及切点检查](../docs/editing.md)和[云转写免费用量准入](../docs/cloud-transcription.md)。离线fixture能验证算术、批准绑定、保留段映射和导出命令，不能证明真实字级准确、自动听音、口型、留存或省时收益。0.10.0已实际调用现有Remotion、FFmpeg与本地faster-whisper，完成生成素材的三镜头/EDL闭环，范围见[执行集成](../docs/integration.md)。这三类镜头与EDL均自研，没有执行video-shotcraft/video-use仓库代码。未来获准真实素材时再做同素材代表段落与A/B，记录实际成本和返工，再决定是否替换已有主链。


本轮只读源码审计另核对了[video-use render.py](https://github.com/browser-use/video-use/blob/main/helpers/render.py)和[shotcraft PageCam.tsx](https://github.com/Vincentwei1021/video-shotcraft/blob/main/assets/lib/PageCam.tsx)。video-use为[MIT](https://github.com/browser-use/video-use/blob/main/LICENSE)，shotcraft代码为[Apache-2.0](https://github.com/Vincentwei1021/video-shotcraft/blob/main/LICENSE)，音频各自授权；0.9–0.10未执行其代码；0.11.0经用户专项批准已执行固定版本的选定原版组件/render/timeline代码，未取用音频。官方目录/API读取曾受连接限制，后通过官方页面核对源码；未据此安装任何包。Remotion仍按安装包自身Free/Company License判断，合成评估不等于未来商业主体资格已审核。
