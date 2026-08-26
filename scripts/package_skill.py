#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
package_skill.py — laoyu-miaomiao-tools 单 skill 打包发版工具

用途：
  1. 校验 skill 版本一致性（SKILL.md metadata.version ↔ CHANGELOG 顶条 ↔ 文件 manifest）
  2. 打 release zip（固定 asset 名，解压后即 skill 文件夹）
  3. 打印发版 checklist（下一个全局 tag、站点需同步的所有位置）

用法：
  python scripts/package_skill.py <skill目录名>          # 校验 + 打包 + checklist
  python scripts/package_skill.py <skill目录名> --check   # 只校验不打包

版本约定（2026-08-26 起）：
  skill 版本唯一真源 = SKILL.md 的 metadata.version（semver）。
  release tag 是仓库全局递增号（跨 skill 共用），只是运输标签，不等于 skill 版本。
  站点卡片 / 纯文本摘要 / zip 内版本一律显示 skill 自身版本。
"""
import re
import sys
import subprocess
from pathlib import Path
from zipfile import ZipFile

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

# skill 目录名 → release asset 文件名（保持稳定，站点链接靠它）
ASSET_NAMES = {
    "lyzbcy-study-map": "lyzbcy-study-map.zip",
    "lyzbcy-最后的1%": "lyzbcy-last-1-percent.zip",
    "lyzbcy-视频生成提示词润色": "lyzbcy-video-prompt-polish.zip",
    "lyzbcy-wechat-autopublish": "lyzbcy-wechat-autopublish.zip",
    "lyzbcy-glm53-zcode-eval": "lyzbcy-glm53-zcode-eval.zip",
    "lyzbcy-xhs-comment-check": "lyzbcy-xhs-comment-check.zip",
}

# 打包时排除的运行时产物 / 系统杂项
EXCLUDES = {".update-check.json", ".DS_Store", "Thumbs.db"}


def die(msg: str) -> None:
    print(f"❌ {msg}")
    sys.exit(1)


def read_frontmatter(skill_dir: Path) -> tuple[str, str, list[str]]:
    """从 SKILL.md 解析 metadata.version 与 metadata.files（简单行级解析，不依赖 yaml）。"""
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    m = re.search(r"^---\s*\n(.*?)\n---\s*$", text, re.S | re.M)
    if not m:
        die(f"{skill_dir}/SKILL.md 没有 YAML frontmatter")
    fm = m.group(1)

    vm = re.search(r'^\s+version:\s*["\']?([\d.]+)["\']?\s*$', fm, re.M)
    if not vm:
        die("frontmatter 里找不到 metadata.version")
    version = vm.group(1)

    files: list[str] = []
    in_files = False
    for line in fm.splitlines():
        if re.match(r"^\s{2}files:\s*$", line):
            in_files = True
            continue
        if in_files:
            em = re.match(r"^\s+-\s+(\S+)\s*$", line)
            if em:
                files.append(em.group(1))
            else:
                in_files = False
    return version, text, files


def read_changelog_top(skill_dir: Path) -> str | None:
    """读 CHANGELOG.md 最顶部的版本号条目。"""
    changelog = skill_dir / "CHANGELOG.md"
    if not changelog.exists():
        return None
    m = re.search(r"^##\s*\[([\d.]+)\]", changelog.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else None


def next_global_tag() -> str:
    """优先读远端 tag（准确），失败退回本地 tag；取最大 semver，建议下一个 tag（minor +1）。"""
    out, source = "", "本地"
    try:
        r = subprocess.run(
            ["git", "ls-remote", "--tags", "origin"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=20,
        )
        if r.returncode == 0:
            out, source = r.stdout, "远端"
    except Exception:
        pass
    if not out.strip():
        try:
            out = subprocess.run(
                ["git", "tag"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
            ).stdout
            source = "本地（ls-remote 不可达，建议先 git fetch --tags 核对）"
        except Exception:
            return "v？（读不到 git tag，请手动确认）"
    vers = []
    for t in out.replace("refs/tags/", "").split():
        m = re.match(r"^\^?v(\d+)\.(\d+)\.(\d+)$", t)
        if m:
            vers.append(tuple(int(x) for x in m.groups()))
    if not vers:
        return "v1.0.0"
    a, b, c = max(vers)
    print(f"（tag 来源：{source}，当前最大 v{a}.{b}.{c}）")
    return f"v{a}.{b + 1}.0"


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    skill_name = sys.argv[1]
    check_only = "--check" in sys.argv[2:]
    skill_dir = SKILLS_DIR / skill_name
    if not skill_dir.is_dir():
        die(f"找不到 {skill_dir}")

    asset = ASSET_NAMES.get(skill_name)
    if not asset:
        die(f"ASSET_NAMES 里没有 {skill_name} 的映射，请先在 scripts/package_skill.py 里登记")

    # ---- 校验 ----
    version, _, files = read_frontmatter(skill_dir)

    top = read_changelog_top(skill_dir)
    if top is None:
        print(f"⚠ {skill_name} 没有 CHANGELOG.md（单文件 skill 可接受）")
    elif top != version:
        die(f"版本不一致：SKILL.md={version}，CHANGELOG 顶条={top}。先对齐再打包。")

    problems = []
    if not files:
        files = ["SKILL.md"]  # 没有 manifest 的老 skill 只校验 SKILL.md
        print("⚠ frontmatter 没有 metadata.files（单文件 skill）")
    for rel in files:
        if not (skill_dir / rel).exists():
            problems.append(f"manifest 里的文件不存在: {rel}")
    disk_files = {
        str(p.relative_to(skill_dir)).replace("\\", "/")
        for p in skill_dir.rglob("*")
        if p.is_file() and p.name not in EXCLUDES and ".update-tmp" not in p.parts
    }
    orphans = sorted(disk_files - set(files))
    if orphans:
        problems.append(f"磁盘上存在但 manifest 未收录（不会进 zip）: {', '.join(orphans)}")

    if problems:
        for p in problems:
            print(f"❌ {p}")
        die("校验未通过")
    print(f"✓ 校验通过：{skill_name} v{version}，manifest {len(files)} 个文件齐全")

    if check_only:
        return

    # ---- 打包 ----
    out = REPO_ROOT / "dist" / asset
    out.parent.mkdir(exist_ok=True)
    # zip 内容统一 LF，与 raw.githubusercontent 线上文件字节一致
    # （zip 安装与 skill 静默更新两种途径拿到的内容完全相同）
    with ZipFile(out, "w") as zf:
        for rel in files:
            data = (skill_dir / rel).read_bytes().replace(b"\r\n", b"\n")
            zf.writestr(f"{skill_name}/{rel}", data)
    print(f"✓ 已打包：{out}（zip 内版本 v{version}，LF 行尾）")

    # ---- 发版 checklist ----
    tag = next_global_tag()
    print(
        f"""
================ 发版 checklist ================
1. 确认改动已提交并推送：
   git add -A && git commit -m "chore: {skill_name} v{version}" && git push origin main
2. 在 GitHub 创建 release：
   tag = {tag}（全局递增号，脚本按现有 tag 自动建议；与 skill 版本 {version} 无需一致）
   asset 上传 dist/{asset}
3. 同步站点 docs/index.html（共 4 处，缺一不可）：
   ① 卡片 <span class="ver"> · v{version}
   ② RELEASES map 里该 skill 的英文 id 链接 → .../download/{tag}/{asset}
   ③ 纯文本摘要 copyForAI() 里的版本号 → v{version}
   ④ window.__FR__.changelog 数组加一条
4. 同步 docs/version.json：页面 version 改新值（如 日期-序号），changes 加同一条
5. push 后打开 https://lyzbcy.github.io/laoyu-miaomiao-tools/ 验证卡片版本与下载链接
================================================"""
    )


if __name__ == "__main__":
    main()
