# Windows 运行环境与诊断

## 机器配置保留在本机

`runtime.local.json`与`QQ_SKILL_LOCAL_CONFIG`指定文件不进发行ZIP，也不由静默更新覆盖。
例（使用本机真实路径；账号、token和缓存不得提交到公共仓库）：

```json
{
  "qq": "123456789",
  "node_dir": "C:/Users/USER/AppData/Local/LaoyuQQ/napcat/v4.18.41",
  "cfg_dir": "C:/Users/USER/AppData/Local/LaoyuQQ/napcat/v4.18.41/napcat/config",
  "desktop_qq": "C:/Program Files/Tencent/QQNT/QQ.exe"
}
```

环境变量优先，再采用本机配置；桌面QQ路径未配置时查询安装注册表。
已配置Node目录时默认使用其中`napcat/config`；无Node配置时兼容原有Shell配置目录。
首次没有配置也可以执行`doctor`或`--version`，不会在导入阶段崩溃。

## 官方 Node 包安装

```bash
python scripts/qq.py setup-runtime --qq 123456789
# 需要代理时显式指定；不改系统代理
python scripts/qq.py setup-runtime --qq 123456789 --proxy http://127.0.0.1:7890
python scripts/qq.py doctor
python scripts/qq.py grab
```

安装实时查询`NapNeko/NapCatQQ`稳定发布，绑定固定版本的
`NapCat.Shell.Windows.Node.zip`下载URL、大小及官方SHA256，不使用第三方镜像。
完整校验、路径检查、核心文件检查均通过后才启用；旧运行包保留。
默认缓存位于本机`LOCALAPPDATA/LaoyuQQ/napcat`，不在同步目录复制登录缓存。
`--cache-dir`可指定位置；`--version vX.Y.Z`明确选择官方历史稳定版，不冒充最新版。
同版本已安装时检查官方目标标记及核心文件；未知/残缺同名目录保留并报错，不覆盖数据。

账号配置已存在则复用，不改token；首次配置只监听127.0.0.1并随机生成token。
安装保存Node目录及账号到本机配置。首次无快速登录缓存时仍需本人扫码/手机确认；
无头启动不绕过登录，检查本机日志中的二维码位置，不自动处理验证码。

## 排查顺序

1. `--version`核对skill版本；仓库release标签和skill版本不是同一编号。
2. `doctor`核对模式、核心文件、API、实际/目标账号。`ready=false`不是“已登录”。
3. Node早退：查看`.runtime.boot.log`中的第一条错误和退出码；定位到缺失DLL再检查对应运行库，不能见超时就重装依赖。
4. API可达但账号不符：停止发送，指定`NAPCAT_QQ`并选对应配置，不修改桌面小号自动登录。
5. 注入模式挂起、但无核心初始化日志/API：一次诊断后使用官方Node包；不反复快速登录或改用桌面自动化。
6. API已连、发送超时：先`history`查是否已送出，避免重发。
7. `restore`停止专用Node进程树并恢复实际桌面QQ路径；其他Node服务不受影响。

## 修复证据的边界

同一目标账号，旧桌面注入链未建立OneBot API；仅更新Shell仍未解决。
官方Windows Node包初始化、登录与OneBot收发成功，说明可工作路径已实测，
并不证明旧链卡住的具体内部函数、某个QQ版本或某个缺失依赖。
此前吞连接错误、桌面路径写死、代理污染和重复等满180秒，都是诊断/编排缺陷。
公开回归用离线夹具，不含真实账号、联系人、聊天、材料文件或凭证。

参考：[官方 Shell 安装](https://napneko.github.io/guide/boot/Shell)、
[官方发行包](https://github.com/NapNeko/NapCatQQ/releases)。
