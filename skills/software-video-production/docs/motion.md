# 按信息关系选择动效

需要让差距、变化、因果或重点更易理解时读本页。默认组件鲜艳活泼，标题和卡片带弹性；可换明暗主题及强调色。先选信息关系，再选择组件；不用组件数量、动静次数或持续运动证明视频好看。已经清楚的画面可直接保持。

## 可调用组件与边界

使用现有 `render_shots.cjs`，实现位于 `assets/remotion-software/`；三类原有软件镜头与下列九类可选镜头共十二类。完整输入示例见 `scripts/fixtures/motion-shots.json`。本库自行实现，只参考公开案例的表达机制，未复制模板源代码或媒体。

| recipe | 说明关系 / 关键输入 | 不适合或需注意 |
| --- | --- | --- |
| `metric_compare` | 同一条件下的量级差距；`items:[{label,value}]`、`unit`、可选`maxValue` | 2–6项，共用从零起的尺度；不同单位/条件不混成同一组条形 |
| `trend_trace` | 按顺序揭示变化；`points:[{label,value,x?}]`、`unit`、`highlightIndex?` | 3–12点；不等间隔须给每点真实x值，省略x只表示顺序；连线不代表新增测量 |
| `target_gap` | 实际与目标差距；`actual`、`target`、`unit`、可选`maxValue` | 目标线固定，实际条形不弹过真实值；不伪造目标或使用不相容单位 |
| `evidence_focus` | 多项依据收拢到判断；`items:[{label,detail}]`、`result?` | 2–5项；`reduceDistractions`默认关闭，开启只降低其余项竞争，不创建空白或改音轨 |
| `causal_flow` | 触发与状态交接；`steps:[{label,detail}]` | 2–5步，是流程示意，不得用节点点亮冒充真实操作完成 |
| `task_router` | 一项输入的不同去向；`origin`、`routes:[{label,detail}]` | 2–4路；适合条件和任务分工，不用分叉路径伪造性能结论 |
| `claim_reveal` | 一句观点的强调与稳定阅读；`claim`、`support?`、`kicker?` | 重点句需短；辅助文字不能同抢主视觉，不是每句都要弹入 |
| `spotlight_roi` | 保留上下文并突出区域；`roi:{x,y,w,h}`、`image?` | ROI是展示画布的0–1归一坐标，图片等比包含并可能留边，须按展示位置校准；先栅格脱敏，不靠聚光遮私密文字 |
| `match_transition` | 由共享对象连接前后；`from`、`to`、`bridge` | 两段需真有语义关系；可独立片段或局部叠层，不宣称自动拼接任意两段素材 |

图表当前支持非负有限数值，默认从零起；不支持负值、对数轴、不确定性区间、多单位或任意图形。遇这些关系应换适合的图表/实现，不能为了套组件改数据。原始值和单位保留，动画仅揭示已有数据；弹性用于标题/卡片，不使量级条形或坐标过冲。

## 时间与阅读状态

各镜用自己的局部帧号。`frames`决定镜头长，`timing.startFrame`与`timing.settleFrame`可配置揭示开始和落定；未配置退场时保持结果，`timing.exitStartFrame`才显式开启淡出。这里是组件接口，不要求每镜经过相同阶段；通过实际读字和内容决定时长，不套固定秒数。全库无后台循环漂浮或自动音量门控。

`evidence_focus`可单独设置`focusIndex`、`focusStartFrame`和`claimStartFrame`。需要减量才设置`reduceDistractions:true`；用`prompt`保留问题或观看期待。默认关闭时可直接推进；没有继续观看的理由、没有帮助理解的停留就删短。重点进入后同样要给阅读时间，不马上抢入下一组动画。

## 来源、输入与运行

真实数据填`synthetic:false`及`dataEvidence:{reference,approved:true}`，记录公开或项目内来源，审核模型/单位/条件；这个声明不自动验证事实。真实截图仍必须提供已栅格脱敏的本地PNG/JPEG data URI及`privacyApproved:true`。示意图应明确其形态；合成测试始终保留标记，不当产品实测。

复制fixture至项目，补已有`runtime`、`browserExecutable`及新`output`目录，再运行：

```powershell
node scripts/render_shots.cjs "<项目>/shots-config.json"
node --test scripts/tests/test_motion_models.cjs
```

画布当前为可配置尺寸的9:16，逻辑布局720×1280；宽度至少360且宽高为偶数。未自动安装依赖，不拉外部字体/图片。输出为镜头视频；节目级声音、剪辑、隐私与封面仍按现有工作流。

## 参考与验收

参考了 RemotionLab 的[条形比较](https://remotionlab.com/showcase/dataviz-bar-chart)、[趋势描绘](https://remotionlab.com/showcase/dataviz-line-draw)、[实际与目标](https://remotionlab.com/showcase/dataviz-bullet)、[双侧比较](https://remotionlab.com/showcase/dataviz-comparison-split)等公开说明与代码结构，迁移顺序揭示、对应比较和稳定阅读机制。网页视频未完成原速视听，不声称复现其声画观感或验证其留存。

数值校验只验证配置与几何；还需查看真实编码的入场、中间与落定帧，检查手机阅读、转场和真实图表含义。节奏有疑虑时，以相同事实对比直接推进和减轻干扰的代表段；不按“安静段齐全”打分。用例和私人制作反馈留项目，不装入公开包。
