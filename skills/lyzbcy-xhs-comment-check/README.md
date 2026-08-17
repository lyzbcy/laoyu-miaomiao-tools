# lyzbcy-xhs-comment-check 📕

> 小红书评论全自动检查 + 回复 · 定时运行 · 人设化回复 · 发送核验 · 中文报告

定时抓取小红书**消息通知页**的新评论,LLM 按你的人设逐条生成回复,**一次打包调用**生成全部回复(省 token),自动发送并核验,最后产出中文审计报告。服务器上无人值守运行,每天自动消化新评论。

## 为什么走"通知页"路线

小红书创作者后台**没有**抖音那种"未回复"筛选。本项目的解法(经真实账号长期验证):

- 打开 `www.xiaohongshu.com/notification?type=comment` → 切「评论和@」Tab 抓新评论
- 用**本地 md5 稳定 ID 记录已回过的评论**做去重(不依赖平台状态)
- 回复交互直接在通知页完成(点"回复" → 填入 → "发送" → **发送后核验**)

## 核心特性

| 特性 | 说明 |
|---|---|
| 🔒 防编造纪律 | 报告只来自本次真实抓取的 JSON,禁止引用旧报告/记忆 |
| 🧠 打包调用 | N 条评论一次 LLM 调用生成,人设 prompt 只发一次,**输入 token 省 ~68%** |
| ✅ 发送核验 | 点了"发送"≠发成功;核验回复框收起/正文出现才算 `replied` |
| 🛡️ 注入防护 | 命中恶意关键词(提示注入)的评论走机械模板,绝不进 LLM |
| 🕐 频率节流 | 内置 12h 节流 + 内存检查,cron 怎么触发都不会跑飞 |
| 📝 审计日志 | `logs/run-YYYY-MM-DD.log` 留 7 天,每次运行可追溯 |
| 🎭 persona 人设 | 身份/语气/兜底模板/垃圾词全在 `persona.json`,换账号不改代码 |
| 📱 noVNC 扫码登录 | 登录失效时起 noVNC 人工扫码(多道风控关卡都能人工过) |

## 快速开始

```bash
# 1. 安装依赖(需要 Python 3.10+)
pip3 install -r requirements.txt
python3 -m playwright install chromium

# 2. 配置人设
cp persona.example.json persona.json   # 按真实身份填写

# 3. LLM:默认从 ~/.openclaw/openclaw.json 读 ws-claw-corp 的 key
#    也可改 xhs_reply.py 的 llm_client() 换成任意 OpenAI 兼容接口

# 4. 首次登录(本机有显示器可去掉 xvfb-run)
xvfb-run -a python3 login_once.py     # 把生成的 login-qr.png 用手机扫

# 5. 试跑(只采集+生成计划,不发送)
xvfb-run -a python3 xhs_reply.py --dry-run --no-start-delay

# 6. 真实小批量
xvfb-run -a python3 xhs_reply.py --max-replies 3 --no-start-delay

# 7. 挂 cron(示例:每天 10:05/22:05)
# 5 10,22 * * * cd <skill目录> && /usr/bin/python3 run-check.py >> logs/cron.log 2>&1

# 单元测试
python3 -m unittest test_xhs_core -v
```

## 目录结构

```
lyzbcy-xhs-comment-check/
├── SKILL.md              # agent 工作流+纪律文档
├── run-check.py          # 主控:节流→内存→采集→生成→回复→核验→报告
├── xhs_core.py           # 纯逻辑层(解析/去重/过滤/打包prompt/格式包装)
├── xhs_reply.py          # 浏览器层(Playwright 通知页采集+回复+核验)
├── login_once.py         # 首次扫码登录(二维码截图)
├── adjust-check-freq.py  # 12h 频率节流
├── persona.example.json  # 人设样板(复制为 persona.json 填写)
└── test_xhs_core.py      # 单元测试
```

## 踩过的坑(都已在代码里修掉)

1. **去重 ID 别用 Python `hash()`**——字符串 hash 带随机盐,重启进程后全部失配 → 重复回复社交事故。用 md5。
2. **`max_tokens` 别设 300**——推理型模型(思维链占输出预算)会把 300 烧光导致 `content=''`(finish=length)。实测要 ≥2000;打包调用按条数×900 预算。
3. **`Page.evaluate` 只收一个 arg**——多参数要打包成单个对象。
4. **通知条目 innerText 混 UI 文本**——"评论了你的笔记4小时前"/"回复"按钮字会混进评论正文,必须清洗。

## 致谢

浏览器交互路线(通知页采集/回复选择器)移植自 [Fisher0012/xhs-auto-reply](https://github.com/Fisher0012/xhs-auto-reply)(MIT),在其基础上重写了工程骨架(主控/节流/核验/审计/打包调用/注入防护)。

## License

MIT
