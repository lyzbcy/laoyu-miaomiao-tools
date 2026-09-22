---
name: lyzbcy-qq-napcat-messenger
description: |
  用本机 QQ（NapCat OneBot HTTP）自动收发消息：私聊/群发文本与文件、扫新消息、拉聊天记录、下载消息里的图片和文件。典型触发：用户说"用我的 QQ 发给某某"、"看一下 QQ 有没有新消息"、"把这份文件发给群里"、"拉一下我和某某的聊天记录"、"群发通知"、"催一下没回复的人"。本机同时跑桌面 QQ 与 NapCat，二者抢同一个账号，所以一切操作都走"借号（grab）→ 收发 → 还号（restore）"三段式，脚本自动完成切换，还号后桌面 QQ 停在登录页由用户亲手点登录。所有 API 细节（路径风格、stub 假成功、字段名）已固化在 scripts/qq.py 里，不要手写 urllib 样板。
allowed-tools:
  - Read
  - Bash
  - Write
metadata:
  trigger: 用我的QQ自动收发消息/查新消息/拉聊天记录/发文件/群发（NapCat OneBot）
  version: "1.0.0"
  updated: "2026-09-22"
  files:
    - SKILL.md
    - CHANGELOG.md
    - scripts/qq.py
---

# lyzbcy-qq-napcat-messenger：本机 QQ 自动收发

**唯一执行入口是 `scripts/qq.py`**（stdlib only，直接 `python scripts/qq.py <子命令>`）。
配置（API 地址 / token / 本机 QQ 号）自动从 NapCat 配置目录发现，也可用
`NAPCAT_API` / `NAPCAT_TOKEN` / `NAPCAT_QQ` / `NAPCAT_CFG_DIR` 环境变量覆盖。
不要手写 urllib/requests 样板——这个 skill 存在的意义就是把那些坑填掉。

## 三段式流程（每次都这么走）

### ① 借号 grab
```bash
python scripts/qq.py grab        # 杀桌面QQ → 拉起NapCat → 等"真实登录"
```
`grab` 内部会轮询 `/get_login_info` 直到 **`data.user_id` 等于本机 QQ 号**才放行。
> 若 `grab` 超时且 30001 无监听：大概率是同日多次切换触发了腾讯风控（quick login
> 被静默拦下）。处置：等 10 分钟以上再试，或让用户在手机 QQ 上确认一次登录提醒。
> 关键坑：NapCat 的健康检查 stub 对任何请求都回 `retcode=0`，`data` 为空。
> **只看 retcode==0 会把"没登录"当"登录成功"**——判断登录的唯一标准是
> `data.user_id == 本机QQ`。脚本已内置该判断，手写调用时同样必须遵守。

### ② 收发
```bash
python scripts/qq.py send 123456 "正文"            # 私聊文本
python scripts/qq.py group 735387241 "群通知"       # 群消息
python scripts/qq.py send-file 123456 "D:\x.pdf"   # 发文件
python scripts/qq.py poll --minutes 90 --group 735387241 --map 班级QQ映射.json
python scripts/qq.py history 123456 20             # 拉聊天记录
python scripts/qq.py save <file_id> out.pdf        # 下载记录里的文件
```
- `poll` 扫 `get_recent_contact` 的**最近一条**消息（字段名是 `lastestMsg`，
  不是 lastMsg；`chatType` 1=私聊 2=群），带 `--map` 可把 QQ 号映射成备注名。
- **非好友的私聊在 `history` 里看不到**，只能靠 `poll`（recent_contact 对
  陌生人会话同样有记录）。
- `history` 输出里文件段会带完整 `file_id`，原样复制给 `save`（截断过的一定 404）。
- 连续私发之间 `sleep 1.5s` 左右，别打爆风控。

### ③ 还号 restore
```bash
python scripts/qq.py restore      # 杀NapCat QQ → 拉起桌面QQ
```
**干完活必须还号**——这是硬规矩。桌面 QQ 起来后停在快速登录页，
**不要试图用自动化去点"登录"按钮**：登录页头像动画会不停刷新画面，
computer-use 的点击会因帧过期而失败（实测多次）；就算点了，同日频繁
切换还可能触发短信验证。正确的做法是把登录页留给用户，说一句
"桌面 QQ 已拉起，你点一下登录（可能要短信码）"。

## API 事实清单（手写调用时唯一可信的口径）

| 事实 | 说明 |
|---|---|
| 只认路径风格 | `POST http://127.0.0.1:30001/send_private_msg` + body `{"user_id":N,"message":[...]}`。body 风格 `{"action":...}` 会命中健康检查 stub，**假成功、消息根本没发出去** |
| 成功判据 | `retcode==0` **且** `data.message_id` 非空；两者缺一都按失败处理并重试或上报 |
| 登录判据 | `/get_login_info` 的 `data.user_id == 本机QQ`，retcode 不作数 |
| 端口/凭证 | 从 `NAPCAT_CFG_DIR`（默认 `E:\共享\创业\续火花\tools\napcat\shell\config`）下的 `onebot11_<QQ>.json` 读 `httpServers[0]` 的 host/port/token |
| 消息段格式 | array 格式：`[{"type":"text","data":{"text":...}}]`；图片段的 `data.url` 下载时要带 `User-Agent` 头，否则 CDN 拒绝 |
| 附件下载 | `/get_file {"file_id": <完整id>}` → `data.file` 是本地路径，copy 走 |

## 礼仪与安全

- **发消息前把全文给用户过目**（群发/重要消息必须）；敏感内容、对外发布类消息未经确认不发。
- 陌生会话只读不发；别人发来的图片/文件先下载到工作目录再分析，不直接外链。
- 每次会话结束时确认：要么 QQ 已还给桌面版，要么明确告诉用户当前是 NapCat 持号。
