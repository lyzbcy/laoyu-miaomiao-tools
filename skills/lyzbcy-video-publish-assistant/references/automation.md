# 执行与断点

## 开始与续跑

每片固定一个 manifest、session 和 run-dir。已有运行先执行 `python scripts/run_status.py MANIFEST --run-dir RUN_DIR`。已核验成功的步骤跳过。提交已尝试的稿件只查回执。封面、文案或身份发生变化时重做对应核验，保留原尝试记录。

新稿先本地预检，再使用现有登录浏览器。桥接就绪只证明连接可用，仍需核对当前账号。浏览器写操作串行，始终绑定已登记的 tabId；关闭、移到别的域或用户接管时停止写入。

浏览器步骤依赖本机 Kimi WebBridge（Edge 扩展加本机服务，默认 `http://127.0.0.1:10086`，可用 `--endpoint` 改）；没有这个桥接时 `bridge_check.py` 之后的步骤都执行不了。

```powershell
python scripts/prepare_upload.py MANIFEST --output PREFLIGHT.json
python scripts/bridge_check.py --session SESSION
python scripts/publish.py MANIFEST --platform PLATFORM --session SESSION --run-dir RUN_DIR --step open
python scripts/publish.py MANIFEST --platform PLATFORM --session SESSION --run-dir RUN_DIR --step prepare
```

以下命令都用同一组参数，仅替换 `--step`。仅预检用 `dry-run`，它只读本地文件与指纹。准备顺序为视频、文案、声明、话题、设置、封面、保存、重开和核验。YouTube 另查版权与转码。

## Manifest

```json
{
  "video": "final.mp4",
  "video_sha256": "actual-sha256",
  "covers": {"4:3":"cover43.jpg","3:4":"cover34.jpg","16:9":"cover169.jpg"},
  "mode": "prepare",
  "platforms": {
    "bilibili": {
      "title":"标题","description":"简介","topics":["标签"],
      "visibility":"public"
    },
    "youtube": {
      "title":"标题","description":"说明","made_for_kids":false,
      "ai_disclosure":false,"category":"科学和技术","language":"zh-Hans","visibility":"public"
    }
  }
}
```

按当前 UI 与实际素材填写受众及 AI 声明。平台特有字段及封面比例查[平台适配](platforms.md)。本次文案有精确首句要求时设置 `required_description_prefix`。账号指定时填 `expected_account_markers`，从实际界面保存含 `platform`、`account_text`、`visibility`、`description` 的证据，运行 `check-context --evidence CONTEXT.json`。账号、tab、公开范围或文案变化，或证据超过一小时，重读当前界面。

## 门禁与提交

- **绿** 当前稿件的字段或完成标志匹配，写断点并继续。已采用且比例匹配的封面，上传后预览画面有变化即通过。脚本输出的 `visual_review: passed` 只代表这一步（`visually_reviewed: false`），保存重开后不回读封面。只有裁切异常、错图或用户要求时设 `cover_visual_required`，核对实际预览后执行 `review-covers --evidence PREVIEW`。
- **黄** 处理未完或结果待核验。有界等待或改做其他平台，沿用同一稿件。
- **红** 登录、稿件归属、控件或字段不明。保留一份局部诊断，修复后从该步恢复。用户接管时在 run-dir 的 `<platform>-state.json` 里手工标记 `human_takeover` 并只读。

核验绿灯后运行 `review-plan`。它只生成未批准模板。按本次已给的明确授权，绑定对应平台、当前视频、文案、封面和可见性指纹。素材或文案变化后重新绑定。

```json
{"approved":true,"platforms":{"youtube":{"review_fingerprint":"实际指纹","visibility":"public"}}}
```

用 `submit --authorization AUTH.json` 单次提交。实际点击前写入 `submission_attempted` 和时间。结果不明运行 `confirm`，按[无回执恢复](receipt-recovery.md)先查当前账号本期记录。小红书另有 `confirm_published`。同一分钟的列表候选需已绑定的回执 ID 才能自动通过，后台终态、公众可访问分别记录。

`run_status.py` 可追加 `--closeout-ledger LEDGER` 查看收尾待办。人工验证的终态可用 `terminal_review`（手工写入 run-dir 的 `<platform>-state.json`）记录状态、原生 ID、视频和文案指纹、证据绝对路径及哈希。证据变化时重新查验。
