# 创作台（LaoyuCreatorStudio）

视频制作工具链的单一家园：画布、剪辑时间线、打标与 BGM 知识库由创作台内置提供。各项目不再保存画布副本，历史项目里的副本视为过时，复用前先与当前创作台版本对照。

## 安装与运行识别

- 安装目录 `%LOCALAPPDATA%\Programs\LaoyuCreatorStudio\<版本>\`，运行数据与项目在 `%LOCALAPPDATA%\LaoyuCreatorStudio\`；`projects\` 属本机运行数据，不进入技能或公开包。
- 服务只绑定 `127.0.0.1`。默认端口见 `%LOCALAPPDATA%\LaoyuCreatorStudio\server.log` 首行（0.1.9-dev 为 18765），端口不同时以实际为准。先 `GET /health` 核对 `app`、`version` 再调用其他接口；本页接口摘要按 0.1.9-dev 记录，版本不同可能有差异，细节以安装内 `resources/app/src/server.mjs` 为准。

## 接口摘要（0.1.9-dev）

- `GET /health`、`GET /logs`：版本与运行日志。
- `GET/POST /api/projects`：列项目、新建项目（标题必填）。
- `/api/project/<id>/{board,workspace,editor,media}`：读写画布与剪辑稿、上传/取本机素材。画布与剪辑稿按 `revision` 乐观并发，冲突返回 409；先取当前再改，不自造 revision。
- `POST /api/bgm/titles`、`/api/bgm/database`：BGM 标题索引与打标库。
- `GET /api/knowledge`、`POST /api/knowledge/source`、`/api/knowledge/curation`：打标知识图谱与洞察回写；图谱带 revision，回写必须匹配当前 revision。
- `GET /api/market`、`POST /api/market/submission`：技能市场目录与提交校验。
- `GET /api/agent/diagnostics`、`POST /api/diagnostics`、`POST /api/feedback`：诊断与反馈。

## 与本技能的关系

创作台在本机的 `~/.codex/skills`、`~/.agents/skills` 下识别已收录的官方技能。市场目录里的公开版 zip 与源码、静默更新清单使用同一版本，不是另一份需要单独维护的内容。

## 边界

本页只记录调用与识别，不代替实际操作验收；不自动安装、升级或拉起创作台，不经创作台自动发布。发布仍按交接规则交 `lyzbcy-video-publish-assistant` 并按本次授权执行。接口能力或版本演进以当次实际版本核验为准，发现偏差先改本页再复用。
