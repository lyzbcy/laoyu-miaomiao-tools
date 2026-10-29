# 执行与断点

脚本仅使用现有登录浏览器和真实页面控件，不用私有投稿API，不下载浏览器或模型。同一任务一个session，四平台串行；换视频换run-dir。CLI默认只准备，`mode: prepare`本身不授权公开。

```powershell
python scripts/prepare_upload.py /project/upload-manifest.json --output /project/preflight.json
python scripts/publish.py /project/upload-manifest.json --platform douyin --session video-task --run-dir /project/run --step open
python scripts/publish.py /project/upload-manifest.json --platform douyin --session video-task --run-dir /project/run --step prepare
```

顺序：upload → text → declaration → topics → settings → covers → save → reopen → verify。YouTube在保存前额外检查版权/转码。正常运行只输出绿灯摘要；黄灯保存pending断点并退避，红灯一份诊断后停止。恢复同一命令会跳过done步骤，不清空视频input测试上传。

封面画布/缩略图变更已检测后，Agent按每种比例看一次实际预览，再执行：

```powershell
python scripts/publish.py /project/upload-manifest.json --platform douyin --session video-task --run-dir /project/run --step review-covers --evidence /project/run/douyin-cover-3x4.jpg
```

## manifest

```json
{
  "video":"final.mp4", "video_sha256":"actual-sha256",
  "covers":{"4:3":"cover43.jpg","3:4":"cover34.jpg","16:9":"cover169.jpg"},
  "mode":"prepare",
  "platforms":{
    "bilibili":{"title":"标题","description":"简介","topics":["AI编程"],"activity_topics":["已选定的一个活动话题"]},
    "youtube":{"title":"标题","description":"说明","topics":["Animation"],"made_for_kids":false,"ai_disclosure":false,"category":"科学和技术","language":"zh-Hans","visibility":"private"}
  }
}
```

`activity_topics`可省略，最多一个。遇活动专用错误时走活动选择并回读，不能把该词改成普通字符串后声称成功；第二个受限词明确记入omitted。活动选择DOM未出现或不唯一即红灯，不能猜候选。

YouTube `context`读取当前AI问句，内容判断先于 `declaration`；普通合成旁白或卡通不自动等同逼真误导修改。Shorts/普通视频以页面实际类型、视频ID及缩略图比例判断。

## 用户授权的正式发布

```powershell
python scripts/publish.py /project/upload-manifest.json --platform youtube --session video-task --run-dir /project/run --step review-plan
python scripts/publish.py /project/upload-manifest.json --platform youtube --session video-task --run-dir /project/run --step submit --authorization /project/authorization.json
python scripts/publish.py /project/upload-manifest.json --platform youtube --session video-task --run-dir /project/run --step confirm
```

`review-plan`只生成未批准的模板。用户授权已在当前会话明确给出且具体成片/文案/封面已可审时，可记录该授权；否则给出实际预览后询问。不要把过往影片的同意迁移到新片。

```json
{"approved":true,"platforms":{"youtube":{"review_fingerprint":"review-plan返回值","visibility":"public"}}}
```

指纹覆盖当前视频哈希、该平台文案和全部封面哈希，改任一项即失效。草稿核验和封面验收未绿不提交；点击前记录submission_attempted。不明结果续查confirm；即使指令重试也不重复点击。`submitted`只证明受理，`published/public`需对应终态证据。

## 改动与诊断

确认用户在编辑后将state的`human_takeover`设true；禁止继续text/topics/prepare覆盖，读当前现场并保留其字段。换文案会使旧核验失效，不能拿旧manifest恢复现场。封面检查证据单独按指纹保存，普通inspect不覆盖它。

定位变化只修当前适配/本地profiles后单步继续。页面被关闭或登录失效只报当前平台红灯，不新建相同投稿。转码黄灯不采屏、不重新上传；跨平台继续独立工作。


## 1.3.2：只读预演与账号/可见性证据

`--step dry-run` 只做本地文件/指纹检查，不选择浏览器tab、不上传、不改稿、不提交；有submission_attempted时返回confirm_only。dry-run通过不代表登录、封面裁切或真实发布通过。

manifest可设置 `required_description_prefix`（本次用户要求的精确开头）及平台项 `expected_account_markers`（从用户选定账号得到的公开昵称/ID标记）、`visibility`。不要把某一期署名、品牌、数字或账号写成全局默认。B站至少有一项实际普通标签或活动标签；无关推荐标签不能代替稿件定位。

配置账号标记后，先回读当前已登录账号、公开范围和实际正文，形成项目私有JSON：`platform`、`account_text`、`visibility`、`description`。这些值须来自刚读取的UI，不从cookies或历史账号推断。执行 `--step check-context --evidence 项目/context.json` 记账；这不是提交授权。记录绑定稿件tab、视频和文案，1小时后、证据变化或身份/公开范围变化需重读。该门禁与dry-run已离线回归；本期不为测试门禁另发帖子。旧manifest仍兼容，未配置标记时Agent也必须执行skill规定的账号回读。

初次open遇已知账号主页可导航到profiles中的上传入口；已上传、已固定tab或用户关闭稿件时不另建稿。跨平台查看管理页不能抢走同域草稿：后续写操作只attach已保存tabId，并核对域名。非预期域名或关闭页为红灯。

抖音新稿保存会去掉段落换行；旧稿可能保留换行及段首星号。仅兼容这两种已观察到的序列化，不吞掉其他字符或内联空格，也不跳过规定首句核验。B站最终提交是已观察到的唯一span控件；所有普通tap仍禁止最终发布。

提交前写入attempted。不明结果先按精确标题、时长、时间/作品ID查管理页；查重0且同草稿仍在、确认未接受后才依据新证据单步恢复，历史不删除。成功后只confirm，不用prepare重传。结果记录须区分submitted、审核中、已发布和外部可访问；小红书管理页出现但外部300031时只报告已观察到的差异，不猜原因或重发。


## v1.3.3 入口与恢复补充

先执行（`SESSION`在本次任务保持不变）：

```powershell
python scripts/bridge_check.py --session SESSION
```

只检查既有 daemon/extension，并列出现有标签；不会 attach、focus、navigate 或启动/升级。`open`命令也执行这个预检，`dry-run`仍不连桥接。Edge登录态通过Kimi Browser Extension复用，账号仍须从本次平台页面核验。

小红书重名话题在平台项增加 `"topic_ids":{"电脑技巧":"OBSERVED_TOPIC_ID"}`。ID必须来自本次候选行的公开DOM `data-impression.tagTarget.value.tagId`，不存在或重复时报错并列候选；不要默认选热度最高或第一行。修正文案manifest后按同一run-dir续跑。

小红书正式提交后：

```powershell
python scripts/publish.py MANIFEST --platform xiaohongshu --run-dir RUN_DIR --session SESSION --step confirm
python scripts/publish.py MANIFEST --platform xiaohongshu --run-dir RUN_DIR --session SESSION --step confirm_published
```

第一条区分提交回执（submitted）；第二条只改变管理页筛选，检查已发布tab、唯一标题、与锁定视频时长误差≤1秒、本次尝试时间至当前时间、24位noteId和published通道。时间字段来自提交前落盘的带时区 `submission_started_at`；时长来自锁定本地视频的ffprobe结果。缺失/歧义维持黄灯，不反向触发submit。

平台时间仅精确到分钟；同一分钟的列表记录必须额外匹配本次成功回执公开链接绑定的noteId，否则脚本保持黄灯（minute_precision_requires_bound_note_id），不把同标题同时长旧稿判为成功。confirm从当前成功页唯一可见公开链接提取ID，不猜测或从列表反向绑定。此项不声称外部公开页可访问。只有后续查询，禁止为了验证再次投稿。

## 合集附加记录（人工UI路径）

合集创建与关联尚无CLI入口。用户要求时按[平台合集路径](platforms.md#合集播放列表独立于作品发布)执行，将目标名称、本次创建尝试、实际观察ID、关联作品、保存重开、合集公开/审核状态留在同一run-dir；同名歧义先核验，不自动重复创建。

视频提交后查询即可，不为验证合集重复submit。合集审核中仍报告视频实际终态，合集作为独立待办。一次公开投稿不能证明所有访客可播放，也不能证明合集审核已通过。

## 低开销恢复入口

```powershell
python scripts/run_status.py MANIFEST --run-dir RUN_DIR
```

纯本地、紧凑JSON，只返回各平台下一步，不连接浏览器、不输出完整页面或整个state。校验实际视频哈希与平台文案指纹；发生变化时先处理差异，不能复用旧核验。与当前ID绑定的public/published回执直接done；提交尝试后只建议confirm，上传结果不明不建议重传；封面裁切仍保留人工验收。它给建议，不代替正式submit授权门禁，也不自动扩大平台适配范围。

人工核验的终态可在state保存 `terminal_review`：status、实际作品id、video_sha256、copy_sha256、证据文件绝对路径evidence及evidence_sha256。只有指纹和证据文件均匹配才复用；这表示Agent已读UI的核验，不冒充脚本自动识别。证据变化即重新查询。

固定已验证控件、标签输入、裁切切换等走适配器；成功只保存最小回读与门禁，绿色不重试，处理等待只读局部状态。失败保留一次局部诊断，在同一稿件单步修复；页面语义变化可需要Agent介入，不能承诺任意平台零探索或固定token成本。统计时分开页面字符、调用数、实际token与端到端成本，没有实测不报节省比例。

done仅表示本次固定稿件的最近一次核验，不是实时或永久公开保证。用户要求复查、平台权限变化或改稿时仍须查询；新一次发布任务使用独立run-dir，不能把别次运行的缓存当本次完成。

恢复时可同时输出收尾未决项：`python scripts/run_status.py MANIFEST --run-dir RUN_DIR --closeout-ledger LEDGER`。四平台done不会掩盖归档或清理仍待处理；status是本地检查，不会重复打开网站。
