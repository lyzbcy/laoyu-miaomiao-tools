# 浏览器操作流程与实测边界

## 选择连接方式

优先用当前环境已提供、能读取页面状态的浏览器工具。在 Windows 本机装有 Kimi WebBridge 时，先运行 `kimi-webbridge status` 确认 daemon 与扩展都已连接，再按已安装的 WebBridge 文档使用其 `navigate` / `find_tab`、`snapshot`、`click`、`fill`、`upload`。同一任务沿用同一个 session；如果用户已打开目标页面，可以借用活动标签。不要凭猜测构造元素选择器：先读 `snapshot` 的控件名称和引用，页面变化后重新读取。没有控件引用时才只读检查 DOM 属性。

Windows 下若通过 WebBridge 本地 HTTP 端点调用，含中文的 JSON 请求写进一次性 UTF-8 文件再交给 `curl.exe --data-binary @文件`，调用后删掉请求文件；直接把中文 JSON 放在 PowerShell 命令参数里曾出现编码问题。不要把账号 Cookie、完整页面或私人评论写进持久日志。

2026-09-28 的一次操作中，Kimi WebBridge 的 `upload` 因扩展未开启 **Allow access to file URLs** 而失败，当时由用户自行上传。2026-09-29 已实测出不依赖该扩展权限的上传路线：在用户明确授权具体文件与小红书目的页面后，由本机临时 HTTP 桥把文件交给页面，页面用 `File` + `DataTransfer` 写入真实文件控件并触发 `input` / `change`。约 3.77 MB 的 ZIP 成功完成代码部署，最终管理卡片显示对应版本“审核中”。

### 文件上传的降级顺序

1. 先用浏览器工具原生 `upload`。成功后直接进入结果核验。
2. 如果只因文件 URL 权限失败，而工具支持在当前页面执行 JavaScript，使用 `scripts/local_file_bridge.py`。它只监听 `127.0.0.1`，只允许指定 Origin，使用随机路径，并在文件被取走后自动停止。
3. 启动示例：`python scripts/local_file_bridge.py --file "D:\\deliverable.zip" --origin https://creator.xiaohongshu.com --port 18766`。读取脚本打印的 `url`、`filename` 和 `content_type`，不要猜随机 URL。
4. 在小红书页面执行下面的表达式，把三个占位值替换成脚本输出和当前控件选择器：

```javascript
(async () => {
  const response = await fetch('BRIDGE_URL');
  if (!response.ok) throw new Error(`local file HTTP ${response.status}`);
  const file = new File([await response.blob()], 'FILENAME', {type: 'CONTENT_TYPE'});
  const input = document.querySelector('input[type="file"][accept*=".zip"]');
  if (!input) throw new Error('target file input not found');
  const transfer = new DataTransfer();
  transfer.items.add(file);
  input.files = transfer.files;
  input.dispatchEvent(new Event('input', {bubbles: true}));
  input.dispatchEvent(new Event('change', {bubbles: true}));
  return {name: input.files[0]?.name, bytes: input.files[0]?.size};
})()
```

5. 写入控件只是开始。继续读取页面，直到上传区出现文件名和“部署成功”或明确错误。上传组件消费文件后，`input.files` 可能重新变成空；这不代表失败，应以组件状态为准。
6. 若点击“重新上传”没有反应，先确认目标标签页在前台。WebBridge 支持 CDP 时可调用 `Page.bringToFront`，再发送鼠标点击；不要反复盲点。
7. 原生上传与本地桥都不可用时，才把单个文件选择步骤交给用户，用户完成后从当前表单继续。

本地桥不是用来跳过登录、验证码、实名认证或 HTTPS 安全警告，也不能扩大上传授权。图标上传如果进入裁剪器，还要继续核对裁剪结果；ZIP 成功经验不能自动推导为所有自定义上传组件都成功。

## 小工具发布或重传

入口曾为 `https://creator.xiaohongshu.com/new/red-app`，具体导航以当前页面为准。

1. 查看小工具卡片、现有版本和审核状态；若有“重新上传”，从该卡片进入，避免新建重名工具。
2. 在表单中逐项核对名称、简介、图标、场景标签、所需权限、版本号和 ZIP。重传时有些字段会保留，不能因为页面已显示旧值就跳过核对。
3. ZIP 上传后等待代码部署结果，再检查版本号、图标和权限是否仍正确。部署成功只表示代码上传通过，不等于内容审核通过。文件控件变空时同时检查上传组件文字，不要仅凭 `files.length` 判错。
4. 在用户授权范围内提交，随后查看管理页确认是“审核中”“已通过”还是“未通过”。记录平台显示的原文理由；笼统的“内容未通过平台综合审核”不足以判断具体违规点。
5. 用户自行上传文件后，重新读取表单状态，从上传结果处接续，不重复上传或替换用户刚传的文件。

最近一次实践核对并提交了约 3.77 MB 的离线运行包：`index.html`、`app.js`、16 张 WebP 背景，总计 18 个条目；检查了 ZIP 完整性、图片可解码、JS 语法和三种手机尺寸下的关键交互。表单显示代码“部署成功”后才点击发布，随后管理卡片显示 `V1.0.5`、`审核中`、`发布新版本成功`。这个清单是该项目的实例，不是所有小工具的固定格式。

## 笔记与评论

笔记发布入口曾为 `https://creator.xiaohongshu.com/publish/publish`。发布前检查图、标题、正文、话题与“小工具”等组件；发布后返回笔记管理页核对状态和链接。小工具须审核通过才可能在笔记发布页挂载，不能仅凭工具 ZIP 已上传就声称已关联。

评论操作应先到当前平台界面查看目标笔记与评论。此前通知页 `https://www.xiaohongshu.com/notification?type=comment` 可用于查看评论通知，但页面结构会变。逐条记录能确认的评论内容、所属笔记和是否已有回复；先拟有上下文的回复，再按用户的本次授权发送并核验可见。遇到无法确认目标、评论重复或页面风控提示时停在当前条，不批量重试。
