# 浏览器操作与原稿恢复

用于已登录公众平台的图文编辑、视频号引用和发表。复用当前连接工具与登录态，无需为富文本路线先配置官方API。

## 定位与编辑

先查现有标签和项目账本，核对账号、标题、草稿ID及attempt。失效tabId先列标签，必要时从可访问网页恢复连接，再开本任务页，不重启整个浏览器。点击可能打开会话列表之外的新页；用全局标签的目标URL与打开来源定位，再接管一个正确编辑器，不连续点击制造重复稿件页。

API已建草稿或管理页有本稿时直接恢复；列表缓存旧值先查询/刷新，不重传或新建同名文章。编辑器未保存先保全正文。富文本粘贴可能异步生效，等待实际段落出现，不把立即回读的占位文字当失败重贴。

文件input按所属功能限定：正文图片上传器不是封面上传器。合集创建、文章关联、保存持久化和公开/审核分别记状态。重开检查AI来源/合集回退、简介重复。contenteditable的Ctrl+A替换不可靠时，显式选择目标节点内容，再用原生insertText或受支持粘贴替换，读回完整结果，不反复追加。

历史定位线索`a.weui-desktop-mass-appmsg__title`、`.publish_hover_content`、`#activity-name`、`#js_name`、`mp-common-videosnap`只作查找依据，先观察当前DOM。后台token只在私有操作使用。

## 发表、扫码与恢复

废止固定等待几秒、连续点两次发表的旧序列。按当前弹窗和明确后置状态推进；synthetic click或原生指针能否生效以本次UI为准，不凭单次旧观察宣称永久反自动化或免验证。

- 未授权群发：最终弹窗关闭群发通知，读回“未开启群发通知”；重新打开后再次核对。
- 外部最终提交前持久化attempt。后续“继续发表”等确认按实际语义单次推进并分别记账；不明结果不能清账本重试。
- 微信验证保留同一稿件与窗口，交管理员/运营者完成；登录二维码不等于本篇发表验证，不绕过验证。
- 元素截图空白时检查图片加载并核对局部/全页截图，不能凭截图文件存在就让用户扫描。不要下载远程媒体绕过展示限制。
- 用户完成验证后只读记录；审核中待查。只有唯一已发表行、永久链接、公众页面账号/标题和本期视频交叉核对后才记published。tempkey临时预览地址不是永久链接。

## 离线核验输入

从实际当前UI采集私有JSON，不导出请求头、Cookie或框架内部状态。article_review.py只校验已观察证据，不代替浏览器读取。

PLAN.json：

```json
{"account":"示例公众号","title":"示例文章","native_video_nonce":"example-current-video","video_description":"本期视频说明"}
```

OBSERVATION.json：

```json
{"account":"示例公众号","rows":[{"title":"示例文章","status":"已发表","url":"https://mp.weixin.qq.com/s/example-permanent"}],"article":{"url":"https://mp.weixin.qq.com/s/example-permanent","title":"示例文章","account":"示例公众号","videos":[{"nonce":"example-current-video","description":"本期视频说明"}]}}
```

也支持native_video_id；优先用本篇已绑定nonce和完整说明核对，不把上期ID套到本期。不同入口export字符串可能不同，不能只靠两段字符串相同/不同判断同片。无视频文章不传视频期望。手机完整播放需另行实测。

独立Playwright部署可参考publish_browser.py --help，但它不是本轮富文本、视频号组件和管理员验证的通用一键实现。仅维护本skill时，不打开发表器或发测试文。
