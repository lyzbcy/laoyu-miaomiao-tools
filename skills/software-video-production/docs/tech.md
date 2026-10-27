# 媒体与重建

FFmpeg/ffprobe探测方向、旋转矩阵、HDR色彩、时长与音轨。编码宽高不等于实际观看方向；HDR转SDR先用代表帧比对，不把某次色调映射参数当通用预设。

项目脚本保存相对素材引用或明确可配置根目录，记录源时间/PTS、文案/音色、遮罩、字幕、音乐与导出参数。新素材必须重建坐标和时间轴；复制脚本先检查输出目录。改文案使对应语音缓存失效，增减片头后复查首帧、首句和节拍。

源MOV与Source code ZIP分开核验，后者可能没有原片。原生UI不得超像素放大后声称原画；截图尺寸与录屏尺寸分别测。EOF和下一元素接入边界查闪空；冻结末帧只在该元素应继续显示时使用。

新增离线工具及fixture命令见[editing](editing.md)与[cloud-transcription](cloud-transcription.md)：EDL与字幕映射、切点审片导出、实际音频测量与额度算术。0.10.0的本地Whisper/Remotion与EDL实际执行入口见[integration](integration.md)；云服务上传/实时余额仍未接入。各工具能力重叠按[工具工作流](../references/tool-workflow.md)选择。

长过滤器或参数写独立文件，命令用参数列表避免PowerShell解释。媒体检查脚本见[media_check.py](../scripts/media_check.py)，只给技术结论，不代替事实、隐私和审美验收。

模型、依赖、源素材与可重建缓存分别登记。清理按授权保留重建必需资料；可恢复归档只转移占用，不宣称总空间减少。
