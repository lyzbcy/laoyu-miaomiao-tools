---
name: lyzbcy-wechat-autopublish
description: 全自动运营微信公众号。当用户提到公众号自动发布、定时发图文、自动发公众号、把草稿箱内容自动发布、公众号 cron 定时发文、freepublish、draft/add、stable_token、公众平台上架、一桐姐的公众号、每周自动发周报总结、每天自动发图 时使用。覆盖官方 API 发布、浏览器降级发布、定时调度与发布前人工确认全流程。
---

# lyzbcy-wechat-autopublish：微信公众号全自动运营

**使命：发布环节 100% 零人工。人的意志只体现在"发布前的一次确认"，确认之后的一切交给机器。**

## 架构（三个可拆分模块）

```
┌─────────────┐    ┌──────────────────────┐    ┌────────────────────┐
│  内容源模块  │ →  │      发布引擎         │ →  │   调度与确认模块     │
│ (可插拔适配器)│    │ scripts/wechat_api.py│    │ cron + AskUserQuestion│
│ 周报总结/每日图│    │ 三层降级 A→B→C       │    │ 发布结果回报         │
└─────────────┘    └──────────────────────┘    └────────────────────┘
```

**可拆分使用**：只想"自动发布"的用户（如一桐姐，内容自己生成）可只用发布引擎——
直接给 `article.json` 就能发；需要连内容一起自动生成的（如每周 AI 周报）才接内容源模块。

## 发布引擎：三层降级（核心决策表）

| 方案 | 通路 | 适用 | 实现 |
|------|------|------|------|
| **A：纯 API** | stable_token → uploadimg/add_material → draft/add → freepublish/submit → get 轮询 | **已认证**公众号（个人主体/未认证号无权限） | `scripts/wechat_api.py publish` |
| **B：浏览器** | API 只推草稿（`--draft-only`）→ 浏览器自动化进草稿箱点"发表" | 未认证账号 | `references/browser-playbook.md` |
| **C：人工兜底** | API 只推草稿 → 通知用户手动点发表 | A、B 都失败 | 绝不静默失败，明确告知卡点 |

判定：config.json 的 `publish_method` = `api` / `browser` / `auto`（默认，先 A 遇 48001 降 B）。

**事实依据**（已核实官方文档，勿凭旧经验）：
- mp.weixin.qq.com **不支持账密登录**，登录必须管理员/运营者扫码 → 浏览器方案靠**登录态持久化复用**（首次扫一次码，保存 storage_state，失效才需人再扫）。
- freepublish 仅限**已认证**公众号（2025-07 起个人主体、未认证账号权限被回收）。
- access_token 需要 **IP 白名单**；统一用 stable_token（force_refresh=false）避免互踢。

## 标准发布流程（agent 每次执行）

1. **读配置**：定位 config.json 的**绝对路径**（脚本 `resolve_config` 依次找：
   `--config` 显式路径 → `$WECHAT_AUTOUPLOAD_CONFIG` → skill 目录下 config.json；
   agent 拿不准就直接传 `--config <skill目录>/config.json`）。
   没有则引导用户按 `config.example.json` 创建，并把本机公网 IP 加入公众平台 IP 白名单。
2. **取内容**（仅当启用内容源模块）：按 `content_source.type` 走
   `references/content-sources.md` 的适配器（如读本周日报目录 → 起草周总结图文）。
3. **脱敏检查**（内容源产物必过）：剔除私有项目、密钥、内部链接、不可公开信息，仅保留可公开产出。
4. **用户确认（强制，不可跳过）**：用 AskUserQuestion 展示
   标题 / 摘要 / 封面 / 正文预览（或 dry-run 输出），问"是否发布？"，
   **同时必须问"是否群发"并提醒：群发每天只有 1 次配额**：
   - 默认/用户未明确回答 → **不群发**（`isFreePublish=true`，只进主页历史，
     不推送粉丝，不限次数）
   - 用户明确要群发 → 走推送（订阅号每日 1 次配额，接口 mass_send_left 可查）
   - 用户拒绝 → 按反馈修改后再次确认；明确放弃则记录到未发布归档。
   - 偷懒借口对照：*"内容看起来没问题就发了吧"* → 不行，确认是铁律；
     *"用户之前同意过类似的"* → 每一篇都要单独确认。
5. **干跑预览**：`python3 scripts/wechat_api.py publish --article article.json --config config.json --dry-run`
   把 steps 展示给用户看（需 config.json 已存在——占位 appid/secret 即可通过校验；
   dry-run 还会做封面等资源的存在性检查并告警）。
6. **正式发布**：去掉 `--dry-run` 执行。读 stderr 的 ✓/… 进度与 stdout 的 JSON 结果。
   - `publish_method` 由脚本**真正执行**：`auto` 遇 48001 会自动停在
     `{"status": "draft-ready-browser", ...}`——此时**草稿已入箱**，按返回 JSON 的
     `next` 字段行动（`publish_browser.py publish --title …`），
     **千万不要再跑一遍 --draft-only 或完整 publish（会重复建草稿）**。
   - 方案 B 的登录态失效 → 打开**有头浏览器**请用户扫码（一次性），保存登录态后续免扫。
   - A、B 均失败 → 方案 C：告知用户草稿已在草稿箱（附后台直链
     `https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2`），绝不静默吞错。
7. **回报结果**：成功 → 给出 `article_url` 永久链接**和 `publish_id`**（异步发布
   事后复查要用 `status` 子命令）；失败 → 给出 errcode + 中文排查提示（脚本已内置）。

## 定时调度

**运行环境有 CronCreate 工具（如 ZCode 客户端，推荐——保留确认环节）**：
用 CronCreate 设 cron，prompt 必须自包含，例如每周六 10:00（`0 10 * * 6`）：

> 读取 <skill目录>/config.json，按 lyzbcy-wechat-autopublish skill 的"标准发布流程"执行：
> 从 content_source 配置的日报目录整理本周总结 → 脱敏 → AskUserQuestion 向用户确认 →
> 确认后调用 scripts/wechat_api.py publish 发布并回报 article_url 与 publish_id。

若当前环境没有 CronCreate 工具，告诉用户在 ZCode 客户端里设置，或改用下面的系统 crontab。

**系统 crontab（无人值守，跳过确认需显式授权）**：只有当 config.json 里
`"auto_confirm": true` 时才允许纯脚本定时直发；否则必须走带 agent 的通路。
可直接粘贴的完整行（按需改路径与时间）：

```cron
# 每周六 10:00 发周总结（先确保 auto_confirm 已由用户亲手开启）
0 10 * * 6 cd /path/to/lyzbcy-wechat-autopublish && /usr/bin/python3 scripts/wechat_api.py publish --article article.json >> state/logs/cron.log 2>&1
```

## 脚本速查（scripts/wechat_api.py，零第三方依赖）

`--config` 可省略：脚本自动依次找 `$WECHAT_AUTOUPLOAD_CONFIG` → skill 目录下 config.json。

```bash
# 联调：测 appid/secret/IP白名单
python3 scripts/wechat_api.py token --config config.json
# 一条龙发布（干跑不触网；需 config.json 存在，占位值即可）
python3 scripts/wechat_api.py publish --article article.json --config config.json --dry-run
# 正式发布 / 只推草稿（未认证号走浏览器或人工发布的前置）
python3 scripts/wechat_api.py publish --article article.json --config config.json
python3 scripts/wechat_api.py publish --article article.json --config config.json --draft-only
# 查询发布终态
python3 scripts/wechat_api.py status --config config.json --publish-id PUB_XXX
# 测试套件（本地 fake server，不触网）
python3 tests/test_wechat_api.py
```

正式发布的返回值：`{"status":"success","article_url":…,"publish_id":…}` 或
`{"status":"draft-ready-browser","next":"…浏览器指引…"}`（browser/auto 降级时，草稿已入箱）。

article.json 字段与全部 API 细节见 `references/api-reference.md`；
浏览器发布操作手册见 `references/browser-playbook.md`；
内容源适配器写法见 `references/content-sources.md`。

## 常见错误速查

| errcode | 含义 | 处理 |
|---|---|---|
| 40164 | IP 不在白名单 | 微信开发者平台→开发设置→IP 白名单 加本机公网 IP |
| 40001/40014 | token 失效 | 脚本已自动重取一次；仍失败则核对 AppSecret |
| 48001 | 无 freepublish 权限 | 未认证号 → 走方案 B 浏览器发布 |
| 40009 | 正文图 >1MB | 压缩图片（转 jpg 质量 80）后重试 |
| 40005 | 图片格式不支持 | 正文图仅 jpg/png |
| 45009 | 接口日限额 | 次日再试或后台申请提额 |
| ret=2（err_msg 空） | session 缺 publish scope（深水区直调 operate_appmsg 时） | 用户扫码登录时未触发「账号选择/允许切换」。**解法：退出登录 → 重新扫码 → 手机上选择目标公众号**（微信号绑定多账号时出现选择页；旧版为登录页「允许切换登录我的其他公众号」复选框）。无代码绕法——agent 检测到此错误必须**明确提醒用户重新登录**，不要反复重试参数 |

## 安全红线

1. **凭据永不进 git**：config.json、storage_state.json、state/ 目录一律 gitignore。
2. AppSecret 只保存在 config.json，**绝不**写进对话输出、commit、日志。
3. 发布前确认不可跳过（除非 config 显式 `auto_confirm: true` 且用户亲自写入）。
4. 草稿一旦发布即从草稿箱消失（官方一次性语义），失败重试前先 `status` 查询，避免重复发布。

## 首次设置清单（新用户引导）

1. **微信开发者平台**（developers.weixin.qq.com → 控制台，微信扫码登录）→ 开发设置：
   拿 AppID/AppSecret，配 IP 白名单（本机公网 IP）。
   > ⚠️ 2025-12-01 起「开发接口管理」已从公众平台迁移至微信开发者平台（真机实测确认），
   > 公众平台后台只剩迁移公告；两个平台登录态不通用，开发者平台需单独扫码。
2. 复制 `config.example.json` → 同目录 `config.json`，填入 appid/secret，选 publish_method。
   若公众号未认证（选 browser/auto），额外安装浏览器依赖：
   `pip3 install playwright && python3 -m playwright install chromium`。
   ⚠️ 浏览器扫码登录时，手机上若出现**账号选择页务必选择目标公众号**（旧版为登录页勾选
   「允许切换登录我的其他公众号、服务号、小程序」复选框）——漏掉这步 session 会缺
   publish scope，直调接口一律 `ret=2`，且只能重新登录解决。
3. `token` 子命令验证通过。
4. 用自带的 `article.example.json` + `body.html` + `cover.png`（skill 目录里有最小样例）
   跑 dry-run → 用户确认 → 真发一篇测试文验证全链路（标题类似"自动发布测试"）。
5. 配置 cron（见"定时调度"）。
