# 扩展平台脚本与耗时收敛

X正文中的表情可能渲染为img[alt]，innerText会漏字。x-confirm在克隆节点中还原img的alt和br换行，再做全文匹配；不改真实页面，不放宽文案或账号匹配。离线复现见tests/test_x_readback.py。

扩展文章入口用find定位具体控件，上传前核对input的父级所属功能。支持.md的隐藏input也可能属于知识库附件；文档导入必须从实际“导入”菜单进入。SPA点击后等待目标状态，不把立即回读未变化当作失败重试。知乎AI声明在草稿重开后可能恢复默认，提交前同表单复核，发表页再核验。富文本转换后的外链须读回实际href，尤其含下划线的视频ID。

恢复已有矩阵先运行 `python scripts/matrix_resume.py PRIVATE_MATRIX.json`。已发布不重传；旧稿合集/活动审核只查询元数据。只有队列要求读回时才打开平台，成功项不重复截图或全页扫描。

`python scripts/extension_steps.py ACTION --plan PRIVATE_PLAN.json --journal PRIVATE_JOURNAL.json` 提供本次实操抽出的参数化步骤：

| ACTION | 用途 | 后续 |
|---|---|---|
| x-inspect | 当前原生编辑器文案、Ready、AI与视频状态 | 只读 |
| x-prepare | 空编辑器就绪后，按哈希一次选入视频并插入正文 | 等Ready；设置并核对原生AI标记 |
| x-submit | 核验采用文案、视频Ready与AI标记后直接提交 | 等请求完成，去本人主页x-confirm |
| x-confirm | 主页按完整文案、原生视频、账号status链接、AI标签确认 | 写终态，后续禁止提交 |
| channels-upload | 通过实际Shadow DOM文件input选入视频 | 封面、声明、活动、提交仍按扩展手册 |
| channels-order | 已打开更改排序弹窗，真实拖动、核验、保存 | 重开合集确认持久化 |
| article-check | 核对原生视频号ID与正文完整性 | 不代表发表/手机播放已验证 |
| wechat-confirm | 当前首页唯一已发表行＋永久链接＋已打开公众文章账号/标题/本期视频交叉核验 | 审核中只返回待查，不提交 |

计划为本项目私有JSON，必填 `session`、`tab_id`。上传/提交填写绝对 `video`、`video_sha256`；X另填 `text`、`account`、`ai_disclosure`。X提交须 `confirmed_this_video: true` 和等于母版哈希的 `authorized_sha256`，仅在用户已授权该对象时登记。公众号核验填 `body`、`native_video_id`；排序填逐期唯一文字 `episode_labels` 和从本次弹窗快照取得的 `save_order_ref`。不把旧tabId、账号、ref或真实文案写入包内。

`wechat-confirm`计划填`tab_id`（已打开的公众号首页）、`article_tab_id`（从本条已发表行实际永久链接打开的公众文章）、`title`、`account`、`draft_id`，以及`native_video_nonce`或该公众组件的`native_video_id`。首次查首页若仍审核中，无需打开临时文章。提交账本须已有`submission_attempted`；确认过程仅切换已观察标签并读DOM。管理页与公众号组件的export字符串本次曾不同，保留实际组件ID，用已绑定的nonce及完整描述确认同片，不能只拿两段不同入口字符串推断错片或同片。此脚本不等于手机完整播放验收。

脚本在外部操作之前持久化尝试，失败也不丢断点；新计划不能继承旧授权。失败先读当前对象，不能删账本重跑。网页控件仍可能变动，这些是已验证路径的参数化抽取，离线防重回归通过不等于本轮又做了一遍真实发布。七平台全自动编排、视频号全部投稿步骤和公众号免扫码尚未实现。

同一异常采用“原入口一次＋新页一次＋一份诊断”收敛；人工也复现无响应后，不再轮换多套鼠标/键盘反复试。登录/安全验证立即交用户，利用等待时间处理其他平台。X已知草稿恢复问题可按扩展手册，在核对未发布并保留原草稿后走新编辑器直接提交，不默认继续保存再重开。用户接管编辑后保持只读，用户确认已发表时标 `published_user_confirmed`；只补结果读回，不再提交。

本次2小时10分钟包含七平台三期核查、缺片补发、封面/合集/活动操作、X多次恢复试验及公众号等待。没有逐步骤起止日志，不能编造分钟拆账。后续任务在日志记录动作起止、结果、重试原因和实际等待；收尾给耗时最多的步骤，不能承诺未经实测的总时长。
