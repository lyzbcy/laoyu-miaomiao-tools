# 可运行集成：镜头、字级稿与实际剪辑

本页说明自研路径；原版选定组件与助手见[upstream](upstream.md)。示例环境、执行结果和批准范围均属于当次验收，不代表当前设备已安装或当前任务已有额外授权。

**实际调用的上游是已安装Remotion、faster-whisper及本机FFmpeg/Windows语音；镜头和EDL实现为自研，不是已经安装/运行video-shotcraft或video-use。** 现有Python/FFmpeg主工程仍可继续使用，按任务选择；HyperFrames不强制加入第二条渲染链。

## 已有依赖与本次验证范围

此前合成验收环境：Node24、Remotion/bundler/renderer4.0.536、React19.3.1、FFmpeg/ffprobe9.0.1、Python3.12、faster-whisper1.2.1及既有离线base模型、NumPy、Edge。本次未安装依赖、下载模型或执行新取来的仓库代码。

`produce.py demo`仅生成自己的UI、中文词语与音频，使用Windows已有System.Speech和.NET Framework编译器编译自编`SyntheticSpeech.cs`。普通用户环境需有可用语音/默认音频信息；本次沙箱账号缺少默认设备信息，使用获准的本机用户环境后成功。没有改变PowerShell执行策略、安全设置或配置任何凭据。其他系统没有此组件时停止，使用自有/已有授权音频与下面的独立入口，不自动安装语音软件。

Remotion路径和浏览器路径必须明确存在；脚本不运行npm/npx、不下载浏览器。离线画面只接受代码生成UI，或明确批准、预先栅格脱敏的PNG/JPEG data URI；不拉取外部图片、字体或登录资料。Remotion自身许可与第三方素材许可独立，商业使用前按主体资格核对；本轮属于合成评估。[上游与许可审计](../references/tool-workflow.md)不等于执行许可。

## 一个入口到合成样片

在skill目录执行（输出必须是新目录）：

```powershell
python scripts/produce.py demo --runtime "E:/共享/tools/视频制作/runtime/remotion" --browser "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --output "<项目>/synthetic-demo-v1"
```

默认720×1280/30fps，也支持`--width 360`或1080。实际执行：9个本地TTS词文件→按音频实长生成词范围和三镜头时长→Remotion各渲染前后对照/局部放大/步骤递进→拼接并加入合成口播→登记源哈希与隐私→批准删除两段**生成的静音尾部**→实际EDL切片/拼接→BGM duck/mix→剪后字幕最后烧录→尺寸/帧率/音轨/解码与切点材料检查。

输出包括3个`shots/*.mp4`、`shots-config.json`、`project.json`、`rollback-project.json`、`rollback-edl.json`、完整源片、口播与原创合成和弦、`edited/final.mp4`、ASS/SRT、分片、两侧帧/音画窗口、接触表和`acceptance.json`。原片不变，撤销批准后可重新剪出完整长度。TTS词范围是各独立音频片段边界，包含尾静音；不是强制对齐真值，也不用于声称真实字幕已自动精准校准。

本轮串联样片源长17.033秒，删除0.6秒后16.433秒；3个镜头实际渲染、3个保留段、9个源词、3组字幕、2个拼接点，720×1280/30fps、完整解码与音轨/字幕边界通过。BGM duck后非零。此数据只证明这组生成输入的技术闭环；没有真人耳听、真实素材审美/留存提升结论。

## 镜头可独立调用

```powershell
node scripts/render_shots.cjs "<项目>/shots-config.json"
```

配置可从demo实际生成的`shots-config.json`复制：顶层runtime/browserExecutable/output/width/height/fps和shots数组；每镜需id、recipe、title、frames。`recipe`支持`before_after`、`detail_zoom`、`step_progression`，实际组件在`assets/remotion-software/entry.jsx`。前后对照可传beforeImage/afterImage，其他镜头可传image；都须为预先栅格脱敏的本地PNG/JPEG data URI且privacyApproved=true。非合成素材需synthetic=false，脚本强制要求真实图片，不能以生成UI冒充产品。title/note/result/contentLabel按事实填写。

当前实现为固定9:16布局、可配置文案/时长/图片的基础软件镜头，局部放大位置需按实际图片再调整/审片；不是shotcraft全套调校卡库、2.5D PageCam、3D运镜或其图库效果已复现。缺少图片时生成的是明确标识的合成工作台，不可当真实产品功能证据。

## 本地转写到EDL

```powershell
python scripts/local_transcribe.py "<项目>/audio.wav" --model-path "<已存在的faster-whisper模型目录>" --source-id source --output "<项目>/transcript-v1.json"
```

这是实际faster-whisper调用：CPU/int8、local_files_only=True，用已有FFmpeg解码为16k单声道float32，避免本机PyAV接口版本差异；不下载模型、不调用云服务。输出words可放入项目字表，另保留模型/源哈希和机器段落。校正误识别与时间后再批准删段，不能按概率或停顿自动认定可删。实际对本轮合成口播调用返回16个机器时间项，分词粒度与9个输入词不同；未评准确率。Scribe仍只有[预检/人工余额快照契约](cloud-transcription.md)，没有实际上传/余额查询适配器，免费余额unknown时保持阻塞。

## EDL实际剪出视频

```powershell
python scripts/render_edl.py "<项目>/project.json" --output "<项目>/output-v1" --width 720 --height 1280 --fps 30
# 撤销批准的同一源项目，实际重新输出完整长度：
python scripts/render_edl.py "<项目>/rollback-project.json" --output "<项目>/rollback-output" --width 720 --height 1280 --fps 30
```

沿用[editing](editing.md)源清单/words/candidates格式。额外源门禁：synthetic生成源，或privacy.rasterized=true、approved=true且redacted_sha256等于实际源哈希；真实素材不得伪标synthetic。哈希/时长改变、字内切点、重叠删除、字幕越界、缺必要音轨或帧网格不一致均停止。当前拒绝不落在目标fps帧网格上的剪点，调用方需回源明确调整，脚本不静默改变时间。

可选`bgm:{path,gain}`，路径相对项目；有BGM请求就检查原支路和duck后支路非静音。片段用统一尺寸/帧率及PCM音频保留接缝，再拼接，字幕最后按剪后时间烧录；6ms边缘淡化只防数值突变，不证明无听感问题。音量输出为mean dBFS，不能当LUFS；响度另用media_check，真人正常速度听审仍必需。当前不支持多轨任意叠层、变速、交叉淡化映射或自动调色。

实际隐私安全、语义、读字、口型、混音和审美必须按[交付](delivery.md)检查；自动门禁和切点截图不能替代这些判断。合成测试通过后，正式成片仍应使用当前任务允许的素材检验代表片段；同素材A/B按当前目标与资源选择，未实际比较不宣称收益。
