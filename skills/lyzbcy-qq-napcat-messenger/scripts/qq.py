#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qq.py — NapCat OneBot HTTP QQ 收发助手
skill: lyzbcy-qq-napcat-messenger 的唯一执行入口（stdlib only，Windows 友好）

子命令：
  grab                借号：杀桌面QQ → 拉起 NapCat → 等登录（验证 data.user_id）
  whoami              显示当前登录账号（区分健康检查 stub 与真实登录）
  send <qq> <text>    发私聊文本
  group <gid> <text>  发群消息
  send-file <qq> <path> [name]          发文件
  poll [--minutes N] [--group GID] [--map a.json]   扫最近消息（默认90分钟）
  history <qq> [count]                  拉某人聊天记录（好友可见全部字段）
  save <file_id> <out>                  下载聊天中的文件（file_id 用 history 里的完整值）
  restore             还号：杀 NapCat QQ → 拉起桌面 QQ（登录按钮留给人点）

配置自动发现：NAPCAT_CFG_DIR（默认 NapCat shell/config）下 onebot11_<QQ>.json
取 host/port/token。环境变量 NAPCAT_API / NAPCAT_TOKEN / NAPCAT_QQ 可覆盖。
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

VERSION = "1.1.1"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Private machine configuration is kept outside distributed skill source.
LOCAL_CONFIG_PATH = os.environ.get("QQ_SKILL_LOCAL_CONFIG", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime.local.json"))
LOCAL_CONFIG = {}
LOCAL_CONFIG_ERROR = None
if os.path.isfile(LOCAL_CONFIG_PATH):
    try:
        with open(LOCAL_CONFIG_PATH, encoding="utf-8-sig") as f:
            LOCAL_CONFIG = json.load(f)
        if not isinstance(LOCAL_CONFIG, dict):
            raise ValueError('expected object')
    except (OSError, ValueError):
        LOCAL_CONFIG = {}
        LOCAL_CONFIG_ERROR = "本机runtime.local.json无效；保留原文件，先修复配置"
NODE_DIR = os.environ.get("NAPCAT_NODE_DIR", LOCAL_CONFIG.get("node_dir", ""))
if os.environ.get("NAPCAT_SHELL") and not os.environ.get("NAPCAT_NODE_DIR"):
    NODE_DIR = ""  # An explicit legacy shell override remains supported.
CFG_DIR = os.environ.get(
    "NAPCAT_CFG_DIR",
    LOCAL_CONFIG.get("cfg_dir", os.path.join(NODE_DIR, "napcat", "config") if NODE_DIR
                     else r"E:\共享\创业\续火花\tools\napcat\shell\config"),
)
NAPCAT_SHELL = os.environ.get(
    "NAPCAT_SHELL", os.path.dirname(CFG_DIR)
)
DESKTOP_QQ = os.environ.get(
    "DESKTOP_QQ", LOCAL_CONFIG.get("desktop_qq", r"C:\Program Files\Tencent\QQNT\QQ.exe")
)
if not os.environ.get("DESKTOP_QQ") and not LOCAL_CONFIG.get("desktop_qq") and os.name == "nt":
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\QQ") as key:
            uninstall = winreg.QueryValueEx(key, "UninstallString")[0].strip('"')
        DESKTOP_QQ = os.path.join(os.path.dirname(uninstall), "QQ.exe")
    except OSError:
        pass


def discover():
    """返回 (api_base, token, qq)。env 覆盖 > 配置文件发现。"""
    if LOCAL_CONFIG_ERROR:
        raise RuntimeError(LOCAL_CONFIG_ERROR)
    token = os.environ.get("NAPCAT_TOKEN")
    qq = os.environ.get("NAPCAT_QQ", str(LOCAL_CONFIG.get("qq", "")))
    if qq and (not qq.isascii() or not qq.isdecimal() or not 5 <= len(qq) <= 12):
        raise ValueError("目标QQ号格式无效")
    api = os.environ.get("NAPCAT_API")
    if not (token and qq and api):
        import glob
        cands = glob.glob(os.path.join(CFG_DIR, "onebot11_*.json"))
        if not cands:
            raise RuntimeError("找不到账号配置；先运行 doctor，再运行 setup-runtime --qq QQ号，或指定 NAPCAT_CFG_DIR=" + CFG_DIR)
        if qq:
            selected = os.path.join(CFG_DIR, "onebot11_%s.json" % qq)
            if not os.path.isfile(selected):
                raise RuntimeError("指定账号缺少配置: " + selected)
            p = selected
        else:
            if len(cands) != 1:
                raise RuntimeError("发现多个账号配置；请指定 NAPCAT_QQ，避免借错号")
            p = cands[0]
        with open(p, encoding="utf-8-sig") as stream:
            cfg = json.load(stream)
        servers = [s for s in cfg["network"]["httpServers"] if s.get("enable", True)]
        if not servers:
            raise RuntimeError("账号配置未启用 OneBot HTTP 服务")
        srv = servers[0]
        host = srv.get("host") or "127.0.0.1"
        host = {"0.0.0.0": "127.0.0.1", "::": "[::1]"}.get(host, host)
        if ":" in host and not host.startswith("["):
            host = "[" + host + "]"
        api = api or "http://%s:%d" % (host, srv["port"])
        token = token or srv.get("token", "")
        qq = qq or os.path.basename(p)[len("onebot11_"):-len(".json")]
    return api.rstrip("/"), token, int(qq)


API, TOKEN, QQ = None, None, None


def configure():
    global API, TOKEN, QQ
    API, TOKEN, QQ = discover()


def die(msg):
    print("❌ " + str(msg))
    sys.exit(1)


def call(ep, payload=None, timeout=15):
    """路径风格调用。返回 dict。注意：body 风格 {"action":...} 会命中健康检查
    stub（retcode=0 且 data 为空）——那是静默失败，本函数不使用该风格。"""
    if API is None:
        configure()
    req = urllib.request.Request(
        API + ep,
        data=json.dumps(payload or {}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + TOKEN,
        },
    )
    # Local OneBot must not be sent to an obsolete system HTTP proxy.
    host = urllib.parse.urlsplit(API).hostname
    opener = (urllib.request.build_opener(urllib.request.ProxyHandler({}))
              if host in ("127.0.0.1", "localhost", "::1") else None)
    open_url = opener.open if opener else urllib.request.urlopen
    with open_url(req, timeout=timeout) as r:
        return json.loads(r.read())


def ok(d, need_data=True):
    if d.get("retcode") != 0:
        return False
    if not need_data:
        return True
    return bool(d.get("data"))  # stub 的 data 为 {} / 空串


def stop_node_runtime():
    if not NODE_DIR or os.name != "nt":
        return
    expected = os.path.abspath(os.path.join(NODE_DIR, "node.exe"))
    # Match the dedicated runtime executable, never taskkill every node.exe.
    quoted = expected.replace("'", "''")
    command = ("[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
               "@(Get-CimInstance Win32_Process -Filter \"name='node.exe'\" | "
               "Where-Object {$_.ExecutablePath -eq '" + quoted + "'} | "
               "Select-Object -ExpandProperty ProcessId) | ConvertTo-Json -Compress")
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                            capture_output=True, text=True, encoding="utf-8", timeout=20)
    if result.returncode:
        raise RuntimeError("查询专用 NapCat Node 进程失败: " + result.stderr)
    pids = json.loads(result.stdout.strip() or "[]")
    if isinstance(pids, int):
        pids = [pids]
    for pid in pids:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(int(pid))], capture_output=True)


def kill_qq():
    stop_node_runtime()
    subprocess.run(
        ["taskkill", "/F", "/T", "/IM", "QQ.exe"],
        capture_output=True,
    )
    subprocess.run(
        ["taskkill", "/F", "/IM", "NapCatWinBootMain.exe"],
        capture_output=True,
    )


def start_napcat():
    if NODE_DIR:
        node = os.path.join(NODE_DIR, "node.exe")
        entry = os.path.join(NODE_DIR, "index.js")
        if not all(os.path.isfile(p) for p in (node, entry)):
            die("专用 Node 运行包不完整: " + NODE_DIR)
        # Node mode does not need a console for cached quick login. Keep logs local.
        log = os.path.join(os.path.dirname(LOCAL_CONFIG_PATH), ".runtime.boot.log")
        with open(log, "wb") as stream:
            return subprocess.Popen([node, entry, "-q", str(QQ)], cwd=NODE_DIR,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                                    stdout=stream, stderr=subprocess.STDOUT, close_fds=True)
    bat = os.path.join(NAPCAT_SHELL, "launcher-win10-user.bat")
    if not os.path.exists(bat):
        die("找不到启动脚本 " + bat)
    # CREATE_NEW_CONSOLE：NapCat 的快速登录依赖控制台交互，DETACHED 会导致卡死（实测）
    flags = 0x00000010  # CREATE_NEW_CONSOLE
    return subprocess.Popen(
        ["cmd", "/c", bat, "-q", str(QQ)],
        cwd=NAPCAT_SHELL,
        creationflags=flags,
        close_fds=True,
    )


def start_desktop():
    subprocess.Popen(
        ["cmd", "/c", "start", "", DESKTOP_QQ],
        shell=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def login_wait(timeout=45, process=None):
    """等真实登录：必须 data.user_id == 本机QQ。retcode==0 不算数（stub 同样返回0）。"""
    t0 = time.monotonic()
    last_error = "尚未连接"
    while time.monotonic() - t0 < timeout:
        if process is not None and process.poll() is not None:
            die("启动器已退出，exit=%s；运行 doctor，查看本机 .runtime.boot.log；不要循环重试" % process.returncode)
        try:
            d = call("/get_login_info", timeout=min(2, max(.1, timeout-(time.monotonic()-t0))))
            uid = (d.get("data") or {}).get("user_id")
            if uid == QQ:
                print("✅ NapCat 已登录: %d (%s)" % (uid, (d["data"].get("nickname") or "")))
                return True
            if uid:
                die("登录账号不匹配，actual=%s expected=%s；停止借号核对" % (uid, QQ))
            last_error = "API 返回空数据，尚未真实登录"
        except Exception as exc:
            last_error = clean_error(exc)
        time.sleep(min(1, max(0, timeout-(time.monotonic()-t0))))
    die("登录未完成（%ds），最后错误：%s。运行 doctor；注入模式无日志时改用 setup-runtime，不反复等180秒" % (timeout,last_error))


def clean_error(error):
    text = str(error)
    if TOKEN:
        text = text.replace(TOKEN, "[REDACTED]")
    return text[:300]


def doctor():
    result = {"skill_version": VERSION, "mode": "node" if NODE_DIR else "desktop-injection",
              "node_dir": NODE_DIR or None, "cfg_dir": CFG_DIR,
              "desktop_qq_exists": os.path.isfile(DESKTOP_QQ)}
    try:
        configure()
        result.update(expected_qq=QQ, api=API)
        data=call("/get_login_info", timeout=2)
        result["actual_qq"]=(data.get("data") or {}).get("user_id")
        result["ready"]=data.get("retcode")==0 and result["actual_qq"]==QQ
    except Exception as exc:
        result.update(ready=False,error=clean_error(exc))
    if NODE_DIR:
        result["runtime_complete"]=all(os.path.isfile(os.path.join(NODE_DIR,n))
                                       for n in ("node.exe","index.js","wrapper.node","napcat/napcat.mjs"))
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result


def require_login():
    data = call("/get_login_info", timeout=3)
    uid = (data.get("data") or {}).get("user_id")
    if data.get("retcode") != 0 or uid != QQ:
        die("发送前账号校验失败，actual=%s expected=%s；本次未发送" % (uid, QQ))


def seg_text(seg):
    t = seg.get("type")
    dd = seg.get("data") or {}
    if t == "text":
        return dd.get("text", "")
    if t == "image":
        return "[图片 %s]" % (dd.get("url") or dd.get("file") or "")[:120]
    if t == "file":
        fname = dd.get("file_name") or dd.get("name") or dd.get("file")
        return "[文件 %s | file_id=%s]" % (fname, dd.get("file_id"))
    if t == "reply":
        return "[回复]"
    if t == "at":
        return("[@%s]" % dd.get("qq"))
    return "[%s]" % t


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]

    if cmd in ("--version", "version"):
        print(VERSION)
        return
    if cmd == "doctor":
        doctor()
        return
    if cmd == "setup-runtime":
        import runtime_setup
        runtime_setup.main(sys.argv[2:])
        return
    try:
        configure()
    except Exception as exc:
        die(clean_error(exc))
    if cmd in ("send", "group", "send-file"):
        require_login()

    if cmd == "grab":
        try:
            current=call("/get_login_info",timeout=2)
            if current.get("retcode")==0 and (current.get("data") or {}).get("user_id")==QQ:
                print("✅ 已持有目标账号: %s（复用现有连接）" % QQ)
                return
        except Exception:
            pass
        # Fail before stopping desktop QQ if the configured runtime is incomplete.
        if NODE_DIR and not all(os.path.isfile(os.path.join(NODE_DIR,n)) for n in ("node.exe","index.js","wrapper.node","napcat/napcat.mjs")):
            die("专用 Node 运行包不完整；运行 setup-runtime，桌面 QQ 未停止")
        if not NODE_DIR and not os.path.isfile(os.path.join(NAPCAT_SHELL,"launcher-win10-user.bat")):
            die("缺少启动器；运行 setup-runtime，桌面 QQ 未停止")
        kill_qq()
        time.sleep(2)
        try:
            process=start_napcat()
            login_wait(timeout=int(os.environ.get("NAPCAT_LOGIN_TIMEOUT", "45")),process=process)
        except BaseException:
            # A failed borrow must not leave QQ held by a hidden runtime.
            try:
                kill_qq()
                start_desktop()
                print("启动未完成，已停止专用运行并拉起桌面QQ；本次未发送")
            except Exception as restore_error:
                print("还号待处理：" + clean_error(restore_error))
            raise

    elif cmd == "whoami":
        try:
            d = call("/get_login_info")
        except Exception as e:
            die("API 不通（NapCat 没起来？）: %s" % e)
        uid = (d.get("data") or {}).get("user_id")
        if uid == QQ:
            print("✅ 真实登录: %d" % uid)
        elif d.get("retcode") == 0 and not uid:
            die("健康检查 stub（retcode=0 但无 user_id）——不算登录成功")
        else:
            die("登录账号不匹配: retcode=%s user_id=%s expected=%s" % (d.get("retcode"), uid, QQ))

    elif cmd == "send":
        qq, text = int(sys.argv[2]), sys.argv[3]
        d = call("/send_private_msg", {
            "user_id": qq,
            "message": [{"type": "text", "data": {"text": text}}],
        })
        mid = (d.get("data") or {}).get("message_id")
        if d.get("retcode") == 0 and mid:
            print("✅ sent msg_id=%s" % mid)
        else:
            die("发送失败: %s" % json.dumps(d, ensure_ascii=False)[:300])

    elif cmd == "group":
        gid, text = int(sys.argv[2]), sys.argv[3]
        d = call("/send_group_msg", {
            "group_id": gid,
            "message": [{"type": "text", "data": {"text": text}}],
        })
        mid = (d.get("data") or {}).get("message_id")
        if d.get("retcode") == 0 and mid:
            print("✅ sent msg_id=%s" % mid)
        else:
            die("发送失败: %s" % json.dumps(d, ensure_ascii=False)[:300])

    elif cmd == "send-file":
        qq, path = int(sys.argv[2]), sys.argv[3]
        name = sys.argv[4] if len(sys.argv) > 4 else os.path.basename(path)
        d = call("/upload_private_file", {"user_id": qq, "name": name, "file": path}, timeout=120)
        if d.get("retcode") == 0 and (d.get("data") or {}).get("file_id"):
            print("✅ file sent: %s" % json.dumps(d.get("data"), ensure_ascii=False)[:200])
        else:
            die("发文件失败: %s" % json.dumps(d, ensure_ascii=False)[:300])

    elif cmd == "poll":
        minutes, group, mapfile = 90, None, None
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            if args[i] == "--minutes":
                minutes = int(args[i + 1]); i += 2
            elif args[i] == "--group":
                group = int(args[i + 1]); i += 2
            elif args[i] == "--map":
                mapfile = args[i + 1]; i += 2
            else:
                i += 1
        names = {}
        if mapfile:
            mm = json.load(open(mapfile, encoding="utf-8"))
            if isinstance(mm, dict) and "班级QQ映射" in mm:
                mm = mm["班级QQ映射"]
            names = {str(v): k for k, v in mm.items()}
        d = call("/get_recent_contact", {"count": 100})
        now = int(time.time())
        rows = []
        for c in d.get("data") or []:
            lm = c.get("lastestMsg") or {}
            ts = lm.get("time") or 0
            if ts < now - minutes * 60:
                continue
            if c.get("chatType") == 2:
                gid = lm.get("group_id")
                if group and gid != group:
                    continue
                who = "群%d/%s" % (gid, (lm.get("sender", {}) or {}).get("card")
                                   or (lm.get("sender", {}) or {}).get("nickname") or "")
            else:
                q = str(c.get("peerUin") or "")
                if group:
                    continue
                who = names.get(q, "QQ" + q)
            txt = " ".join(seg_text(s) for s in (lm.get("message") or [])
                           if isinstance(s, dict))[:110].replace("\n", " ")
            rows.append((ts, who, txt))
        rows.sort()
        for ts, who, txt in rows:
            print("%s | %s | %s" % (time.strftime("%m-%d %H:%M:%S", time.localtime(ts)), who, txt))
        if not rows:
            print("（%d 分钟内无消息）" % minutes)

    elif cmd == "history":
        qq = int(sys.argv[2])
        count = int(sys.argv[3]) if len(sys.argv) > 3 else 12
        d = call("/get_friend_msg_history", {"user_id": qq, "count": count})
        for m in reversed((d.get("data") or {}).get("messages") or []):
            ts = time.strftime("%m-%d %H:%M", time.localtime(m.get("time") or 0))
            sender = m.get("sender", {}) or {}
            who = "我" if sender.get("user_id") == QQ else (sender.get("nickname") or str(sender.get("user_id")))
            txt = " ".join(seg_text(s) for s in (m.get("message") or [])
                           if isinstance(s, dict))[:240].replace("\n", " ")
            print("%s | %s | %s" % (ts, who, txt))

    elif cmd == "save":
        fid, out = sys.argv[2], sys.argv[3]
        d = call("/get_file", {"file_id": fid}, timeout=60)
        p = (d.get("data") or {}).get("file")
        if p and os.path.exists(p):
            shutil.copy(p, out)
            print("✅ 已保存 %s (%d B)" % (out, os.path.getsize(out)))
        else:
            die("get_file 失败: %s" % json.dumps(d, ensure_ascii=False)[:300])

    elif cmd == "restore":
        kill_qq()
        time.sleep(3)
        start_desktop()
        print("✅ 桌面 QQ 已拉起（登录页需要人点一下，可能要短信验证码）")

    else:
        print(__doc__)
        die("未知子命令: " + cmd)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as exc:
        die(clean_error(exc))
