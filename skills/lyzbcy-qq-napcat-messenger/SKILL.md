---
name: lyzbcy-qq-napcat-messenger
description: |
  用本机 QQ 的 NapCat OneBot HTTP 登录态收发私聊、群聊和文件，查询聊天记录并下载附件。适用于“用我的QQ回复某人”“把资料发给某人”“查看QQ消息”。Windows优先使用专用Node运行包，借号→核验→收发→还号；已有连接直接复用，账号严格匹配。只用脚本，不用computer use代替；收发结果必须回读核验。
allowed-tools:
  - Read
  - Bash
  - Write
metadata:
  version: "1.1.0"
  updated: "2026-10-29"
  files:
    - SKILL.md
    - CHANGELOG.md
    - CONTRIBUTORS.md
    - scripts/qq.py
    - scripts/runtime_setup.py
    - scripts/update_skill.py
    - references/runtime.md
    - references/community-contribution.md
    - update.json
---

# QQ 自动收发 · 正式版 1.1.0

执行入口 `python scripts/qq.py <子命令>`，Python 标准库。收发只走此脚本，
不手写 HTTP 样板，也不改用 computer use。下载包不含 QQ 登录数据、token、聊天内容或 Node 大包。

## 首次与每日入口

每天首次使用先后台执行 `python scripts/update_skill.py --background`；失败沿用当前版本，不等它完成。
先运行 `python scripts/qq.py doctor`，报告 skill 版本、启动模式、运行包完整性、API及实际/目标账号，绝不打印token。

- 已有 `runtime.local.json` 或环境配置：直接沿用，不让用户重复扫码，不覆盖设置。
- 首次部署、或旧注入模式启动失败：按[运行环境与诊断](references/runtime.md)运行
  `python scripts/qq.py setup-runtime --qq QQ号`，安装官方 Windows Node 包。
- `setup-runtime` 每次从官方 GitHub 发布源重新绑定版本、资产及 SHA256，完整验证后安装；
  保留旧运行包和现有账号配置，不改桌面 QQ 安装。网络需要代理时显式传 `--proxy`。

## 三段式流程

### 1. 借号并核验

```bash
python scripts/qq.py grab
python scripts/qq.py whoami
```

`grab` 先复用已登录的**目标账号**；需要启动时优先本机配置的 Node 包。
显式账号只读取对应 `onebot11_QQ号.json`，多个账号未指定时停止，不猜“小号/主号”。
登录唯一判据为 `data.user_id == 目标QQ`；`retcode=0` 加空数据不是成功。
发送前再次校验实际账号。**不更改自动登录设置，不把启动失败直接认定为账号风控。**

### 2. 读取与发送

```bash
python scripts/qq.py history QQ号 20
python scripts/qq.py poll --minutes 90
python scripts/qq.py send QQ号 "正文"
python scripts/qq.py send-file QQ号 "D:\资料\文件.xlsx"
python scripts/qq.py group 群号 "通知"
python scripts/qq.py save 完整file_id "D:\资料\附件.pdf"
```

- 先确认收件人及本次授权；正文给用户过目，敏感内容未经确认不发。
- 用户明确要求“直接发送已有资料”时，不擅自改成代填或让对方补表；只发相关文件，不把整目录或凭证一并上传。
- 文本成功要求 `retcode==0` 且非空 `message_id`；文件要求非空 `file_id`。
  发完用 `history` 回读，核对发送者、收件人、文件名/大小和正文（含用户指定落款）。
- 若发送结果不明，**先查记录，避免重发**。这不是自动循环聊天或群发授权。
- 私发之间间隔约1.5秒；陌生会话只读不发。`history`对非好友不完整时使用`poll`读取最近消息。
- `poll` 使用 `lastestMsg` 和 `chatType`；文件ID保留完整。文件名兼容 `file_name/name/file`。

### 3. 还号

```bash
python scripts/qq.py restore
```

停止**专用运行包**的Node进程树，再拉起本机实际安装的桌面QQ；不结束其他Node程序。
核验账号已释放和桌面QQ进程已启动。登录按钮/验证码留给用户，不自动点击。
任务结束必须还号；若用户明确要求继续持号，记录实际持有者，不谎称已经还号。

## 启动失败时只诊断一次

启动器提前退出立即报告退出码；登录默认45秒上限，保留最后连接错误。
Node日志位于本机skill目录的`.runtime.boot.log`，可能包含敏感数据，禁止随公开包或报告外传。
旧注入模式无API、无日志时，检查运行包/启动链并切官方Node方式，不连续重复180秒借号。
已知“旧注入卡住而Node成功”只证明启动链差异，**不等于证实QQ版本不兼容、缺依赖或小号抢登**。

## 配置与收尾

本机文件`runtime.local.json`（不进下载包/更新清单）保存`qq/node_dir/cfg_dir/desktop_qq`。
环境变量优先：`NAPCAT_QQ/NAPCAT_NODE_DIR/NAPCAT_CFG_DIR/DESKTOP_QQ/NAPCAT_API/NAPCAT_TOKEN`。
显式`NAPCAT_SHELL`保留旧注入模式；本机OneBot请求绕过系统代理，外网下载代理独立配置。

完成并核验还号后给一次实际结果小结；用户确认完成后再按
[可选贡献约定](references/community-contribution.md)评估脱敏经验，未经同意不公开私聊/账号资料。

可复用请求：
```text
用 QQ skill 读取我和【联系人】的最近私聊，复用本机已配置的目标账号。
按本次授权发送【资料/正文】，不要重复填表；末尾加【落款】。
发送后回读核验并还号。启动失败先doctor，不连续重试，也不用computer use。
```
