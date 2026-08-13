# 内容源适配器（可插拔模块）

发布引擎只认 `article.json`。内容源模块的职责是**产出这个文件**。
每个人想发的东西不一样——只做适配器规范，不做死板流水线。

config.json 里声明：

```json
"content_source": {
  "type": "weekly_report",
  "reports_dir": "/Users/you/Documents/日报",
  "report_glob": "*.md",
  "desensitize": true
}
```

`"type": "none"`（或不配 content_source）= 只用发布引擎，用户每次自己给 article.json
（一桐姐模式：她的生图管线产出入参，本 skill 只管发）。

## 内置适配器

### weekly_report（捞鱼自用：每周六 10:00 发本周 AI 学习与产出）

cron 触发后 agent 的工作单：
1. 读 `reports_dir` 下**本周**（上周六至今天）的日报文件。
2. 归纳：本周学了哪些 AI 相关内容、产出了哪些项目/工具。
3. **脱敏（默认开启，铁律）**：
   - 只保留可公开项目；工作/客户相关内容一律剔除；
   - 出现代码片段时检查无密钥、token、内部 URL、真实姓名/手机号；
   - 涉及他人的一律匿名化或删除；拿不准的 → 放进"待用户确认清单"。
4. 写 article.json：
   - `title`：`AI 周报｜{M月D日}：{一句话主题}`（≤32 字）
   - `digest`：本周 1~2 句总结（≤120 字）
   - `content_html`：分节（本周学了什么 / 做了什么 / 下周计划），
     图片若有须先转本地文件由引擎上传；正文 ≤2 万字符
   - `thumb_image`：可复用固定封面或用生图工具产一张 900×500 jpg
5. 走 SKILL.md「标准发布流程」第 4 步起（用户确认 → 发布）。

### daily_image（一桐姐模式：每天发 AI 生图）

上游生图管线把图放到一个目录，适配器产出：
```json
{"article_type":"newspic","title":"{日期主题}","content":"<p> </p>",
 "image_list":["/path/to/today/01.png"]}
```
（newspic 图片消息无需封面；title 是必填。）

### custom（自定义）

任何脚本/流程只要产出合法 article.json 即可接入。
字段规范见 `references/api-reference.md`。

## 写新适配器的检查单

- [ ] 产出的 article.json 能过 `wechat_api.py publish --dry-run`
- [ ] 脱敏开关生效（`desensitize: false` 必须是用户亲手改的）
- [ ] 失败有明确出路（残留素材、部分上传是可接受的——素材可复用，草稿一次性）
- [ ] 标题/摘要字数限制在生成端就控制住
