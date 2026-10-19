---
name: lyzbcy-video-publish-assistant
description: 在已登录浏览器中准备抖音、B站、小红书和YouTube投稿，上传成片、设置文案封面与声明、保存并回读草稿，交接用户发布。
metadata:
  version: 1.2.0
  source: https://raw.githubusercontent.com/lyzbcy/laoyu-miaomiao-tools/main/skills/lyzbcy-video-publish-assistant/SKILL.md
  files:
    - CHANGELOG.md
    - SKILL.md
    - references/automation.md
    - references/platforms.md
    - references/update.md
    - scripts/browser.py
    - scripts/prepare_upload.py
    - scripts/profiles.json
    - scripts/publish.py
    - scripts/update_skill.py
    - scripts/youtube.py
    - update.json
---

# 多平台投稿

每天首次使用从本skill目录后台执行 `python scripts/update_skill.py --background`，直接继续任务；失败沿用旧版。细节见[更新机制](references/update.md)。

把已采用成片准备成可审核的稿件。默认保存草稿，脚本无公开发布命令；保持用户指定账号、平台与内容范围。用户已手动接管的稿件以现场修改为准。

## 执行与恢复

1. 用manifest记录最终视频、SHA256、独立比例封面、各平台文案与声明；先核对实际账号。封面创意未通过时先处理封面，已有合格素材不重新生成。
2. 读取[脚本工作流](references/automation.md)及可用kimi-webbridge skill；优先复用脚本、同一session与run-dir。没有桥接可用现有浏览器工具，不索取Cookie、不下载新浏览器/模型。共享浏览器会话串行操作，切页后重新定位。
3. 先inspect后操作。上传尝试预先入账；超时先回读文件、进度和稿件，不能靠重传来测试。选择器变化按当前DOM修复定位，局部修复单步续跑，不反复prepare覆盖已完成内容。
4. 封面选入后等待实际预览变化，查看平台裁切下的主句、人脸与比例，再记录review-covers。这是Agent视觉检查点。文本、话题实体、分区和声明以实际回读为准；AI问句按当前原文与内容判断。
5. 保存后重开对应稿件，核对标题、正文、标签、声明、双比例封面及上传/保存状态。verify不代替视觉检查。YouTube另核对类型、实际视频ID、私享状态与版权检查；处理中保留pending断点。

## 用户同时编辑

回读出现非本轮修改时，先暂停该稿件的写入并保留现场；可继续只读检查或处理别的平台。需要辨别归属时问用户，不能先恢复manifest。用户确认手动修改后记录保留字段，旧manifest仅为历史输入；不再运行text/topics/prepare覆盖该稿件，后续写入前重新读取现场。此处是操作约束，现有脚本不保证自动识别人类改动。

出现提交/发布线索时核对状态，避免重复投稿。用户明确说已经发布，按“用户确认已发布”收尾，不要求重新上传、不把人工发布计为脚本成果。

## 交接与证据

逐平台列账号、稿件入口、封面比例、保存/重开结果和剩余事项。文件选入、上传、草稿、审核与公开发布分开；用户确认与独立核验分开。平台版权检查当前无问题不能保证未来无主张，不自动争议或改用户选曲。

截图失败可保留实时DOM回读的字段证据，明确未完成的视觉检查；文字回读不能补算封面已看过。运行资料、账号、截图和私有稿件链接留项目，不进入技能包。平台适配线索见[platforms](references/platforms.md)；不为填满表单开启无关推广、同步、活动或地点。只有建议的平台不算支持。

修改技能时同步所维护的源码、安装副本与本地分发包；远端发布另需任务授权。网页定位的本次补救未经合并和验证，不宣称脚本已自动支持。
