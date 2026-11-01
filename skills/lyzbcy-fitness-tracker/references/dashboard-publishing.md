# 可选博客发布

默认 `blog.enabled=false`，此时不调用Git、不发送数据。图片生成与当前对话附件交付不要求启用博客。

用户明确要求把训练聚合数据发布到自己的仓库时，在私有数据目录的config.json填写：

```json
{
  "blog": {
    "enabled": true,
    "repo": "/用户自己的本地博客Git仓库",
    "remote": "origin",
    "branch": "main",
    "data_path": "fitness/fitness.json"
  }
}
```

使用现有Git认证，绝不把token写进公开配置。分支和remote应由用户预先配置并同步好；脚本不创建/更换远端，不切分支，不修改全局Git配置。

`fitness.py finish` 先生成图片，再尝试发布，失败会返回 `blog.status=failed` 而保留图片。也可单独执行 `python scripts/publish_dashboard.py --workspace /用户私有数据目录`。

发布器只写data_path指定的JSON（格式 `schema_version:1, days:[...]`），包含日期、训练日、容量、组数、次数、时长及计时口径；不带原始备注/个人配置。不自带针对特定博客的页面，需将此数据接入用户自己的可视化模板，不能直接替换任意旧版看板schema。

目标文件有未提交改动、仓库已有暂存内容、当前分支不符或本地历史领先/落后远端时拒绝发布，避免夹带其他工作。成功创建提交但push失败时，在私有 `publish-state.json` 留下本次提交指纹；仅当HEAD、repo、remote与branch仍一致时重推本次提交，不重复生成提交。仓库变化后停止，交由用户核对。

`status=pushed`仅表示Git推送成功，页面部署仍为`unverified`；若需要确认上线，继续检查用户自己的部署系统。推送失败不影响训练记录与总结图片，模型仍要把图发给用户并报告真实状态。
