# 已批准的原版上游接入

0.11.0真实调用原版源文件，执行前逐文件SHA256校验。自研的是适配/验收入口，不再把它称作原版实现；0.10.0的自研镜头/EDL链仍保留。

| 已安装来源 | 固定commit | 本次原版实际调用 |
| --- | --- | --- |
| [video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft) | `43bd349a136651865ecfa6ea1cf012f6e957d304` | PageCam、Caption、DigitRoll、BeforeAfterSliderScrub、BeatStepListThemeCycle及其本地fixture依赖 |
| [video-use](https://github.com/browser-use/video-use) | `43cfc566833548093455c9d4a46bd69913b7e552` | helpers/render.py原生EDL切片、concat、字幕最后合成及loudnorm；helpers/timeline_view.py的切点画面/波形 |

历史验收安装位置为`C:/Users/Administrator/.codex/skills/video-shotcraft`和同级`video-use`，是本机示例，不可假定其他设备存在；执行前检查实际路径及固定版本。仅选择取件：前者152个文本文件约1.02MiB，后者6文件约87KiB。没有取音频、原视频、Gallery大预览、模型、node_modules或安装器；不是全部工具/图库都可运行。调用所需源码保持原始字节，许可证MIT/Apache-2.0随安装保留；第三方音频许可不因代码许可而自动覆盖。

上游原始入口留在各目录`UPSTREAM-SKILL.md`；实际`SKILL.md`只加本机范围说明，先读`LOCAL-SCOPE.md`。尤其video-use默认推荐云转写、聊天贴密钥、自动装依赖与额外代理，这些不覆盖用户约束：不索要聊天密钥、不写.env、Scribe仍按[额度/上传准入](cloud-transcription.md)，本次不上传/付费/新依赖/新代理。既有明确合成策略批准不重复索取。

## 一个命令调用原版组件与原生EDL

先用[integration](integration.md)的`produce.py demo`生成自己的合成fixture，或复用已生成且哈希相符的fixture。然后：

```powershell
python scripts/produce_upstream.py --runtime "E:/共享/tools/视频制作/runtime/remotion" --browser "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --shotcraft "C:/Users/Administrator/.codex/skills/video-shotcraft" --video-use "C:/Users/Administrator/.codex/skills/video-use" --fixture-project "<生成素材目录>/project.json" --output "<项目>/upstream-acceptance-new"
```

此验收入口拒绝非synthetic源标记，并校验fixture文件哈希。它生成自己的高分辨率界面，真实import安装目录里的原版TSX组件/demo，通过已有Remotion输出三段，再配本地生成口播，转换为video-use原生sources/ranges与type=word转写schema，执行原版main及两个切点的原版timeline_view。没有调用Scribe；word schema不代表转写服务被调用。

`render_upstream_shots.cjs`可独立读取生成的`shots-config.json`调用原版镜头。配置给出已有runtime/browser、shotcraftRoot、publicDir、output及synthetic=true；当前验收布局按上游原生1920×1080编排，渲染1280×720/30fps。UI和原版demo都标记为合成验收。原版demo的模拟前后状态/模糊、作者标识及主题文案不能冒充真实产品事实；正式软件片需用真实脱敏界面并按自己的受众重新构图，不直接搬demo发布。

## 原生EDL与Windows适配

`upstream_native.py --worker render --root <video-use目录> -- <原生edl.json> -o <新输出.mp4> --build-subtitles --draft --fps 30`实际加载并执行该固定版本的原版main；不是自研render_edl替代。原生EDL为sources字典、ranges源区间、grade、overlays和total_duration_s。输入须先按本skill检查源哈希、删段批准、字边界和隐私；直接调用上游助手不会替你实施这些项目门禁。

适配层只在Windows把Path字符串转为正斜杠，避免FFmpeg字幕滤镜解释反斜杠；为原版切点绘图增加已安装的Windows字体候选。源文件未修改。原版`render.py --help`也已直接运行。所有原生调用命令、返回码与日志随验收输出保存，执行前按`assets/upstream-pins.json`拒绝缺失/改动/越界源码。

实际合成结果：3×6秒原版组件视频拼成18秒，删除两段生成静音尾部共0.6秒；原版助手生成3片段、6组SRT、2张切点画面/波形图。视频流17.400秒/522帧，容器与AAC音轨17.434667秒，视频start_time=0.033333秒。保留这约一帧边界差异记录，不能称作零偏差或耳听同步已过。完整解码、尺寸、帧率、字幕边界和音轨通过。`--draft`只证明技术剪点，未验证1920正式档质量或两遍响度路径。

## 未接通与验收边界

Scribe余额/上传适配仍未接，免费剩余unknown；HyperFrames、Manim、talkcraft、抓取/发布器、新模型/依赖未安装。此次没有测试原版overlays的PTS分支、真实多take选材、自动调色、真实素材隐私、原速主观听审或审美/留存收益。切点波形和loudnorm不冒充耳听；官方组件运行不等于成片自动好看。

历史验收授权只覆盖当时的固定版本、选定资源和合成测试，不自动扩展到后续任务。按当前用户指令及授权处理实际素材、新依赖、下载、上传和费用；不自动执行上游setup。
