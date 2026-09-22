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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CFG_DIR = os.environ.get(
    "NAPCAT_CFG_DIR",
    r"E:\共享\创业\续火花\tools\napcat\shell\config",
)
NAPCAT_SHELL = os.environ.get(
    "NAPCAT_SHELL", os.path.dirname(CFG_DIR)
)
DESKTOP_QQ = os.environ.get(
    "DESKTOP_QQ", r"C:\Program Files\Tencent\QQNT\QQ.exe"
)


def discover():
    """返回 (api_base, token, qq)。env 覆盖 > 配置文件发现。"""
    token = os.environ.get("NAPCAT_TOKEN")
    qq = os.environ.get("NAPCAT_QQ")
    api = os.environ.get("NAPCAT_API")
    if not (token and qq and api):
        import glob
        cands = glob.glob(os.path.join(CFG_DIR, "onebot11_*.json"))
        if not cands:
            die("找不到 onebot11_*.json（检查 NAPCAT_CFG_DIR=%s）" % CFG_DIR)
        p = cands[0]
        cfg = json.load(open(p, encoding="utf-8"))
        srv = cfg["network"]["httpServers"][0]
        api = api or "http://%s:%d" % (srv.get("host", "127.0.0.1"), srv["port"])
        token = token or srv.get("token", "")
        qq = qq or os.path.basename(p)[len("onebot11_"):-len(".json")]
    return api.rstrip("/"), token, int(qq)


API, TOKEN, QQ = discover()


def die(msg):
    print("❌ " + str(msg))
    sys.exit(1)


def call(ep, payload=None, timeout=15):
    """路径风格调用。返回 dict。注意：body 风格 {"action":...} 会命中健康检查
    stub（retcode=0 且 data 为空）——那是静默失败，本函数不使用该风格。"""
    req = urllib.request.Request(
        API + ep,
        data=json.dumps(payload or {}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + TOKEN,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def ok(d, need_data=True):
    if d.get("retcode") != 0:
        return False
    if not need_data:
        return True
    return bool(d.get("data"))  # stub 的 data 为 {} / 空串


def kill_qq():
    subprocess.run(
        ["taskkill", "/F", "/T", "/IM", "QQ.exe"],
        capture_output=True,
    )
    subprocess.run(
        ["taskkill", "/F", "/IM", "NapCatWinBootMain.exe"],
        capture_output=True,
    )


def start_napcat():
    bat = os.path.join(NAPCAT_SHELL, "launcher-win10-user.bat")
    if not os.path.exists(bat):
        die("找不到启动脚本 " + bat)
    # CREATE_NEW_CONSOLE：NapCat 的快速登录依赖控制台交互，DETACHED 会导致卡死（实测）
    flags = 0x00000010  # CREATE_NEW_CONSOLE
    subprocess.Popen(
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


def login_wait(timeout=180):
    """等真实登录：必须 data.user_id == 本机QQ。retcode==0 不算数（stub 同样返回0）。"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            d = call("/get_login_info", timeout=6)
            uid = (d.get("data") or {}).get("user_id")
            if uid == QQ:
                print("✅ NapCat 已登录: %d (%s)" % (uid, (d["data"].get("nickname") or "")))
                return True
        except Exception:
            pass
        time.sleep(4)
    die("等待登录超时（%ds）。看 NapCat 控制台/端口号是否起来。" % timeout)


def seg_text(seg):
    t = seg.get("type")
    dd = seg.get("data") or {}
    if t == "text":
        return dd.get("text", "")
    if t == "image":
        return "[图片 %s]" % (dd.get("url") or dd.get("file") or "")[:120]
    if t == "file":
        fname = dd.get("file_name") or dd.get("name")
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

    if cmd == "grab":
        kill_qq()
        time.sleep(2)
        start_napcat()
        login_wait()

    elif cmd == "whoami":
        try:
            d = call("/get_login_info")
        except Exception as e:
            die("API 不通（NapCat 没起来？）: %s" % e)
        uid = (d.get("data") or {}).get("user_id")
        if uid == QQ:
            print("✅ 真实登录: %d" % uid)
        elif d.get("retcode") == 0:
            print("⚠ 健康检查 stub（retcode=0 但无 user_id）——不算登录成功")
        else:
            print("retcode=%s data=%s" % (d.get("retcode"), d.get("data")))

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
        if d.get("retcode") == 0:
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
    main()
