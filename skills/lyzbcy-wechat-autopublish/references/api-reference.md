# 微信公众号发布 API 速查（skill 内置脚本的依据）

> 全部结论经官方文档核实（2026-08）。旧版 `doc/offiaccount/...` 路径已迁移到
> `doc/service/...` 与 `doc/subscription/...`，下文给的均为可访问地址。
> 本文件是参考资料；实际调用**一律通过 `scripts/wechat_api.py`**，不要手搓 curl。

## article.json 字段

| 字段 | 必填 | 限制 | 说明 |
|---|---|---|---|
| `title` | ✅ | ≤32 字 | 标题 |
| `author` |  | ≤16 字 | 作者 |
| `digest` |  | ≤120 字 | 摘要（不填则取正文前 54 字） |
| `content_html` / `content_html_file` | ✅ 二选一 | ≤2 万字符 | 正文 HTML；文件路径相对 article.json 所在目录 |
| `thumb_image` | news 必填 | ≤10MB，jpg/png | 封面图路径。建议 900×383（2.35:1）；画布 900×500 展示时裁切 |
| `content_source_url` |  | ≤1KB | "阅读原文"链接（普通外链在正文内不可点击，只能放这里） |
| `article_type` |  | `news`(默认)/`newspic` | newspic=图片消息，需 `image_list`（本地图片路径数组，≤20 张） |
| `need_open_comment` / `only_fans_can_comment` |  | 0/1 | 评论开关 |

## 链路与接口（脚本已封装，按序调用）

### 1. stable_token（推荐，替代旧 /cgi-bin/token）
`POST https://api.weixin.qq.com/cgi-bin/stable_token`
```json
{"grant_type":"client_credential","appid":"...","secret":"...","force_refresh":false}
```
- `force_refresh=false`：有效期内重复获取**不互踢**、到期前 5 分钟自动续期。
- `true`：强刷（旧 token 失效），每天限 20 次、间隔 ≥30s。
- ⚠️ 调用方公网 IP 必须在 公众平台→设置与开发→基本配置→**IP 白名单** 里（errcode 40164）。

### 2. 正文图上传（返回 URL，无 media_id）
`POST /cgi-bin/media/uploadimg?access_token=TOKEN`（multipart 字段 `media`）
- 仅 jpg/png，≤1MB；返回 `{"url":"http://mmbiz.qpic.cn/..."}`
- **正文所有 `<img src>` 必须是 mmbiz.qpic.cn**：外链图会被脚本自动下载→校验→上传→替换。
- 返回的 URL 只能用于 content，不能当封面。

### 3. 封面上传（返回 thumb_media_id）
`POST /cgi-bin/material/add_material?access_token=TOKEN&type=image`（multipart `media`）
- image ≤10MB（bmp/png/jpeg/jpg/gif）；返回 `{"media_id","url"}`
- 永久素材 URL 仅腾讯域内可用；图文/图片素材上限 10 万张。

### 4. 新建草稿
`POST /cgi-bin/draft/add?access_token=TOKEN`
```json
{"articles":[{"title":"...","author":"...","digest":"...",
  "content":"<p>HTML，图须 mmbiz.qpic.cn</p>",
  "thumb_media_id":"...","need_open_comment":0,"only_fans_can_comment":0}]}
```
- 返回 `{"media_id":"草稿ID"}`；**草稿被发布/群发后即从草稿箱移除（一次性）**。
- content 白名单清洗：仅内联 `style`，`<style>`/script/iframe 被剥离；
  `<a href>` 仅允许指向公众号图文/小程序，普通外链不可点击。

### 5. 发布（⚠️ 仅已认证公众号）
`POST /cgi-bin/freepublish/submit?access_token=TOKEN` body `{"media_id":"草稿ID"}`
- 返回 `{"publish_id":"..."}`；**errcode=0 只代表提交成功，结果是异步的**。
- 未认证/个人主体 → errcode 48001，走浏览器方案（browser-playbook.md）。

### 6. 轮询终态
`POST /cgi-bin/freepublish/get?access_token=TOKEN` body `{"publish_id":"..."}`
- `publish_status`：0 成功（含 `article_detail.item[].article_url` 永久链接）
  1 发布中 2 原创校验失败 3 常规失败 4 平台审核失败 5 成功后删文 6 封禁；
  失败时 `fail_idx` 给出失败条目序号。

## 发布(freepublish) vs 群发(mass/sendall)

| | 发布 | 群发 |
|---|---|---|
| 推给粉丝 | ❌ 只进主页历史 | ✅ 像消息推送 |
| 频次 | 每天可用，不占群发配额 | 订阅号 1 次/天、服务号 4 次/月 |

## 官方文档索引

- 草稿：https://developers.weixin.qq.com/doc/service/api/draftbox/draftmanage/api_draft_add.html
- 正文图：https://developers.weixin.qq.com/doc/service/api/notify/message/api_uploadimage.html
- 永久素材：https://developers.weixin.qq.com/doc/subscription/api/material/permanent/api_addmaterial.html
- 发布：https://developers.weixin.qq.com/doc/subscription/api/public/api_freepublish_submit.html
- 发布状态：https://developers.weixin.qq.com/doc/subscription/api/public/api_freepublish_get.html
- token：https://developers.weixin.qq.com/doc/subscription/api/base/api_getaccesstoken.html
- 错误码：旧版 Global_return_code 页已下线；errcode 含义可在公众平台后台
  「设置与开发→接口权限」或微信开发者社区搜索 errcode 值，本 skill 脚本已内置常见码的中文提示
