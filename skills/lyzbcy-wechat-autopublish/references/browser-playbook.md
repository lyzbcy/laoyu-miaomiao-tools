# 浏览器发布操作手册（方案 B：未认证账号 / API 无权限时的降级）

**前提**：内容已经用 `wechat_api.py publish --draft-only` 推进草稿箱（API 推草稿不需要认证，
只有"发布"这一步才需要）。本手册解决"把草稿箱里的草稿点发表"。

> ⚠️ 如果你是从 `publish_method=auto` 的 **48001 自动降级**过来的：完整 publish 链路里
> `draft/add` 已经成功，**草稿已在箱内，直接从下面第 2 步开始**（不要重复 --draft-only，
> 会建出第二份草稿）。

> ✅ **2026-08-14 真机实测通过**（macOS + Edge + kimi-webbridge）：登录态 cookie 存活时
> 打开 mp.weixin.qq.com **直接进后台**（无需扫码）；草稿箱、发表按钮均可用下述选择器定位。
> 以下「实测情报」小节的选择器/URL 均来自该次实测，DOM 改版时以语义步骤为准。

## 实测情报（选择器与 URL，2026-08-14 核对）

| 目标 | 定位方式 |
|---|---|
| 草稿箱页面 URL | `https://mp.weixin.qq.com/cgi-bin/appmsg?begin=0&count=10&type=77&action=list_card&token=<TOKEN>&lang=zh_CN`（`<TOKEN>` 从登录后任一后台页 URL 里取；也可点侧边栏「草稿箱」） |
| 草稿卡片 | `.weui-desktop-card.weui-desktop-publish` |
| 「发表」按钮 | 每张卡片右下 `a.weui-desktop-link_send-multi`，文案「发表」，**无需 hover 即在 DOM 可见**；不可点时带 `weui-desktop-link_disable` 类 |
| 后台首页特征 | URL 含 `/cgi-bin/home` 且带 `token=` 参数（判断登录态是否有效） |
| 列表筛选 | 顶部有「文章 / 视频」tab 与「输入标题/关键词」搜索框 |

## 登录现实（必读，勿凭旧经验）

- mp.weixin.qq.com **没有账密登录**，只能管理员/运营者**微信扫码**（手机相机扫真二维码，长按识别无效）。
  （表情开放平台 sticker.weixin.qq.com 支持账密——那是另一套系统，别混淆。）
- 因此自动化策略是**登录态持久化复用**：首次人工扫一次码 → 保存 storage_state/cookie →
  之后自动化直接复用；登录态失效（数小时到数天，无官方保证）才需要人再扫一次。
  （实测：日常使用的浏览器里 cookie 可存活数天以上，直接进后台。）
- 风控提示：不要高频自动化操作，动作间留 1~2 秒，每步用截图验证。

## 实现一：agent + 浏览器桥（agent 在场，推荐）

用你运行环境的浏览器自动化能力（ZCode 的 browser-use、kimi-webbridge、Playwright 等）
按以下步骤操作，**每一步都要截图确认后再进行下一步**：

1. **恢复登录态**：导航到 `https://mp.weixin.qq.com/`。
   - 直接进入后台（URL 含 `/cgi-bin/home` 且带 `token=`）→ 登录态有效，继续。
   - 看到二维码页 → 登录态失效：恢复之前保存的 storage_state/cookie 后刷新重试；
     仍失效 → **打开有头浏览器**，请用户现在扫码，扫码成功后**立即导出并保存登录态**
     到 skill 目录 `state/`（gitignore；Playwright 存 storage_state，浏览器桥场景
     直接复用用户日常浏览器的 cookie 更省事）。
2. **进草稿箱**：导航到「实测情报」表里的草稿箱 URL（token 取当前页面 URL），
   或点侧边栏「草稿箱」。按标题匹配 `--draft-only` 输出的那篇（顶部有搜索框可精确定位）。
3. **点发表**：目标草稿卡片右下「发表」（`a.weui-desktop-link_send-multi`，注意跳过
   带 `weui-desktop-link_disable` 的）→ 弹出确认框（可能要求选择群发/发布、勾选确认）→
   截图给用户过目（这一步即使有 auto_confirm 也要留截图证据）→ 点「发表/确定」。
4. **验证**：等待跳转或出现"发表成功"；截图存档到 `state/logs/`（文件名含日期）。
5. **失败处理**：出现人机验证/异常 → 截图 → 停止重试 → 通知用户人工处理（方案 C）。

> 💡 **kimi-webbridge 通路**（用户本机在用）：daemon `http://127.0.0.1:10086`，
> `navigate/snapshot/click/screenshot` 等 action（详见其 SKILL.md）。snapshot 的
> 可访问性树可以直接按文案定位「草稿箱」「发表」，比 CSS 选择器更抗改版。

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

## ⚠️ 2026-08-14 真机实测补充：未认证号的「发表」双重墙

对**未认证个人号**真机实测（Edge + kimi-webbridge，发表成功一篇验证）：

1. **「发表」按钮反自动化**：synthetic `el.click()`、CDP `Input.dispatchMouseEvent`
   （含完整 moved→pressed→released 序列）、DOM 事件链（mouseover→mousedown→mouseup→click）
   全部无法触发——平台对发表动作做了真实交互验证（疑似 isTrusted 检测）。
   → 自动化只能走到"草稿入箱+定位到发表按钮"，**最后一下必须人点**。
2. **发表确认扫码**：人点「发表」后，平台弹出管理员扫码确认（每次发表都要）。
   GitHub 上两个主流自动发布项目（WeChatMediaPlatformAutomation/puppeteer、
   blog-auto-publishing-tools/selenium）同样是人工扫码，**无合法绕过方案**。
3. **出路对照**：
   - 已认证号：走方案 A（freepublish API），完全无扫码无浏览器——首选
   - 未认证号：接受"发布前扫一次码"（比全手动仍省 90% 工序），或走深水区 ↓
   - 深水区（自担风险）：用 cookie+token 直调后台内部 CGI（appmsgpublish 模式，
     参考 mp 后台自己的请求）。⚠️ 非公开接口、违反平台协议、有封号风险；
     需先在浏览器 Network 里抓一次真实发表的请求格式。
4. 分担扫码：后台「设置→安全中心」可添加**长期运营者**微信号，运营者也能扫码。

## 方案 C：人工兜底话术

> 草稿已放进草稿箱：《{title}》。自动发布通道本次不可用（原因：{errcode/登录态失效}）。
> 请打开 https://mp.weixin.qq.com → 草稿 → 找到该草稿点「发表」。预计 1 分钟。

任何时候都**不允许**静默失败或假装发布成功。
