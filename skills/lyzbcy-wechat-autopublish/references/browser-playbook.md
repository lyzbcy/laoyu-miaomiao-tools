# 浏览器发布操作手册（方案 B：未认证账号 / API 无权限时的降级）

**前提**：内容已经用 `wechat_api.py publish --draft-only` 推进草稿箱（API 推草稿不需要认证，
只有"发布"这一步才需要）。本手册解决"把草稿箱里的草稿点发表"。

> ⚠️ 如果你是从 `publish_method=auto` 的 **48001 自动降级**过来的：完整 publish 链路里
> `draft/add` 已经成功，**草稿已在箱内，直接从下面第 2 步开始**（不要重复 --draft-only，
> 会建出第二份草稿）。

## 登录现实（必读，勿凭旧经验）

- mp.weixin.qq.com **没有账密登录**，只能管理员/运营者**微信扫码**（手机相机扫真二维码，长按识别无效）。
  （表情开放平台 sticker.weixin.qq.com 支持账密——那是另一套系统，别混淆。）
- 因此自动化策略是**登录态持久化复用**：首次人工扫一次码 → 保存 storage_state →
  之后自动化直接复用；登录态失效（数小时到数天，无官方保证）才需要人再扫一次。
- 风控提示：不要高频自动化操作，动作间留 1~2 秒，每步用截图验证。

## 实现一：ZCode / browser-use（agent 在场，推荐）

用浏览器自动化 skill（如 browser-use:control-browser）按以下步骤操作，
**每一步都要截图确认后再进行下一步**：

1. **恢复登录态**：导航到 `https://mp.weixin.qq.com/`。
   - 看到二维码页 → 登录态失效：恢复之前保存的 storage_state（cookie）后刷新重试；
     仍失效 → **打开有头浏览器**，请用户现在扫码，扫码成功后**立即导出并保存 storage_state**
     到 skill 目录 `state/mp_storage_state.json`（gitignore）。
   - 直接进入后台首页 → 登录态有效，继续。
2. **进草稿箱**：侧边栏「内容与互动 →草稿」（旧版叫「素材管理/新建图文」）。
   URL 一般为 `https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_list`…找到目标草稿
   （按标题匹配 `--draft-only` 输出的那篇）。
3. **点发表**：目标草稿右下角「发表」按钮 → 弹出确认框（可能要求选择群发/发布、
   勾选确认）→ 截图给用户过目（这一步即使有 auto_confirm 也要留截图证据）→ 点「发表/确定」。
4. **验证**：等待跳转或出现"发表成功"；截图存档到 `state/logs/`（文件名含日期）。
5. **失败处理**：出现人机验证/异常 → 截图 → 停止重试 → 通知用户人工处理（方案 C）。

## 实现二：独立部署 Playwright 脚本（无 agent 环境，如一桐姐的服务器）

```bash
pip3 install playwright && python3 -m playwright install chromium
# 首次：有头模式人工扫码，保存登录态
python3 scripts/publish_browser.py login --state state/mp_storage_state.json
# 之后：无头使用登录态，把最新一篇指定标题的草稿点发表
python3 scripts/publish_browser.py publish --title "今天的图" --state state/mp_storage_state.json
```

`scripts/publish_browser.py` 提供上述 login/publish 子命令（--help 看全参）。
⚠️ 后台 DOM 会改版：脚本里的选择器是"尽力而为"，失败时按「实现一」的语义步骤
人工/agent 操作，并顺手把新选择器更新进脚本。

## 方案 C：人工兜底话术

> 草稿已放进草稿箱：《{title}》。自动发布通道本次不可用（原因：{errcode/登录态失效}）。
> 请打开 https://mp.weixin.qq.com → 草稿 → 找到该草稿点「发表」。预计 1 分钟。

任何时候都**不允许**静默失败或假装发布成功。
