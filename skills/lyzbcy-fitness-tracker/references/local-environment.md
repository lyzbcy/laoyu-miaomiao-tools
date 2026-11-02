# 公共代码与本地增量环境

所有安装使用同一公开版本。不要为某台服务器维护另一份业务代码、修改受管源码或在SKILL.md写账号路径。

1. 首次使用运行 `python scripts/fitness.py environment`，获取实际workspace及LOCAL.md位置。
2. 数据目录优先级：命令行 `--workspace/--data-dir` > `FITNESS_HOME` > skill根目录私有 `runtime.local.json` 的 `workspace` > `~/.lyzbcy-fitness`。
3. `config.json`保留训练计划、个人PR、品牌等；同目录`runtime.local.json`递归增量覆盖配置。只覆盖指定字段，原账本、动作库、配置不迁移、不重写。
4. 本机偏好/已授权博客地址可写入数据目录`LOCAL.md`。Agent在开始任务时读取它；它不能替代本次用户授权、伪造结果或扩大消息发送范围。

skill根目录的定位文件（此处是假路径，实际值只放本机）：

```json
{"workspace":"/your/private/fitness"}
```

数据目录的增量环境示例：

```json
{
  "nutrition_dir":"/your/private/nutrition",
  "blog":{
    "enabled":true,
    "repo":"/your/blog/repository",
    "remote":"origin",
    "branch":"main",
    "schema":"jekyll-v1",
    "data_path":"_data/fitness.json",
    "github_ssh":true,
    "include_notes":false,
    "include_preferences":false,
    "include_nutrition":false
  }
}
```

`days-v1`是轻量列表；`jekyll-v1`兼容完整健身看板，包含overview/sessions/personal_records/muscle_balance/volume_trend/exercises/cardio/nutrition_link。选择格式不会创建/更改看板帖子。原有训练数据格式直接读取，无须转换账本。公开字段详见博客说明；原始备注、偏好和营养数据须分别明确启用才导出。

`github_ssh`只对当前Git子进程配置GitHub SSH重写，不改全局Git配置或仓库远端。认证使用本机现有密钥/凭据，不写进环境JSON或公开包。

更新器和打包器均排除运行定位、LOCAL.md、训练账本、个人配置和输出；下一版升级仍保留本机环境。旧版1.1.0迁移时，先备份旧skill及入口，记录账本/配置/动作库哈希，在外部数据目录设置上述增量环境，再安装公共包。用 `publish_dashboard.py --dry-run`核对原博客兼容性，用 `fitness.py finish --date YYYY-MM-DD --no-publish`验证已收工日期（只生成图片），不伪造收工、不做测试推送。
