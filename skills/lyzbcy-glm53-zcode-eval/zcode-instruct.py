#!/usr/bin/env python3
"""Install a managed GLM-5.3 instruction block for ZCode."""

from __future__ import annotations

import argparse
import re
import hashlib
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


BEGIN_PREFIX = "<!-- glm-5.3-zcode-instruct:begin version="
BEGIN_TOKEN = "glm-5.3-zcode-instruct:begin"
END_MARKER = "<!-- glm-5.3-zcode-instruct:end -->"
END_TOKEN = "glm-5.3-zcode-instruct:end"
STATE_VERSION = 1
STATE_FILENAME = ".glm53-zcode-instruct-state.json"
PACKAGE_VERSION = "1.0.0"
INSTRUCTION_VERSION = "1"
DEFAULT_PROMPT_FILENAME = "glm-5.3-zcode-instruct-v1.md"
BEGIN_PATTERN = re.compile(
    r"^<!-- glm-5\.3-zcode-instruct:begin version=([A-Za-z0-9._-]+) -->$"
)


class ManagedBlockError(ValueError):
    """Raised when managed markers are incomplete, duplicated, or malformed."""


class InstallError(RuntimeError):
    """Raised when an installation cannot be completed without data risk."""


class ConcurrentModificationError(InstallError):
    """Raised when a target changes between inspection and mutation."""


@dataclass(frozen=True)
class ManagedBlock:
    start: int
    end: int
    version: str
    text: str


@dataclass(frozen=True)
class InstallResult:
    status: str
    target: Path
    changed: bool
    snapshot: Optional[Path] = None


def detect_newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def _without_line_ending(line: str) -> str:
    if line.endswith("\r\n"):
        return line[:-2]
    if line.endswith(("\n", "\r")):
        return line[:-1]
    return line


def locate_managed_block(text: str) -> Optional[ManagedBlock]:
    lines = text.splitlines(keepends=True)
    begin_lines = []
    end_lines = []
    offset = 0

    for line in lines:
        content = _without_line_ending(line)
        if BEGIN_TOKEN in content:
            begin_lines.append((offset, offset + len(line), content))
        if END_TOKEN in content:
            end_lines.append((offset, offset + len(line), content))
        offset += len(line)

    if not begin_lines and not end_lines:
        return None
    if len(begin_lines) != 1 or len(end_lines) != 1:
        raise ManagedBlockError(
            "托管标记必须恰好包含一对 / Managed markers must be one complete pair"
        )

    begin_start, _begin_end, begin_content = begin_lines[0]
    end_start, end_end, end_content = end_lines[0]
    match = BEGIN_PATTERN.fullmatch(begin_content)
    if match is None or end_content != END_MARKER:
        raise ManagedBlockError(
            "托管标记格式无效 / Managed marker format is invalid"
        )
    if begin_start >= end_start:
        raise ManagedBlockError(
            "托管标记顺序无效 / Managed marker order is invalid"
        )

    return ManagedBlock(
        start=begin_start,
        end=end_end,
        version=match.group(1),
        text=text[begin_start:end_end],
    )


def render_managed_block(prompt: str, version: str, newline: str) -> str:
    normalized = prompt.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
    body = normalized.replace("\n", newline)
    return (
        f"{BEGIN_PREFIX}{version} -->{newline}"
        f"{body}{newline}"
        f"{END_MARKER}{newline}"
    )


def apply_managed_block(text: str, prompt: str, version: str) -> str:
    newline = detect_newline(text)
    replacement = render_managed_block(prompt, version, newline)
    block = locate_managed_block(text)
    if block is not None:
        return text[: block.start] + replacement + text[block.end :]

    separator = "" if not text or text.endswith(("\n", "\r")) else newline
    return text + separator + replacement


def remove_managed_block(text: str) -> str:
    block = locate_managed_block(text)
    if block is None:
        return text
    return text[: block.start] + text[block.end :]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_text_if_exists(path: Path) -> str:
    if path.is_symlink():
        raise InstallError(f"拒绝操作符号链接 / Refusing symlink: {path}")
    if not path.exists():
        return ""
    if not path.is_file():
        raise InstallError(f"目标不是文件 / Target is not a file: {path}")
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return handle.read()
    except (OSError, UnicodeError) as exc:
        raise InstallError(f"读取失败 / Failed to read {path}: {exc}") from exc


def atomic_write_text(
    path: Path, text: str, expected_sha256: Optional[str]
) -> None:
    if path.is_symlink():
        raise InstallError(f"拒绝操作符号链接 / Refusing symlink: {path}")

    exists = path.exists()
    if exists:
        current = read_text_if_exists(path)
        current_sha256 = sha256_text(current)
        if expected_sha256 is None or current_sha256 != expected_sha256:
            raise ConcurrentModificationError(
                f"文件已被其他进程修改 / File changed concurrently: {path}"
            )
        mode = path.stat().st_mode & 0o777
    else:
        if expected_sha256 is not None:
            raise ConcurrentModificationError(
                f"文件已被其他进程删除 / File was removed concurrently: {path}"
            )
        mode = 0o600

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=str(path.parent)
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, mode)
        os.replace(temporary_path, path)
    except OSError as exc:
        raise InstallError(f"写入失败 / Failed to write {path}: {exc}") from exc
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def unlink_if_unchanged(path: Path, expected_sha256: str) -> None:
    if path.is_symlink():
        raise InstallError(f"拒绝操作符号链接 / Refusing symlink: {path}")
    if not path.exists():
        raise ConcurrentModificationError(
            f"文件已被其他进程删除 / File was removed concurrently: {path}"
        )
    current = read_text_if_exists(path)
    if sha256_text(current) != expected_sha256:
        raise ConcurrentModificationError(
            f"文件已被其他进程修改 / File changed concurrently: {path}"
        )
    path.unlink()


class Installer:
    def __init__(self, target: Path, prompt_path: Path, version: str):
        self.target = target.expanduser()
        self.prompt_path = prompt_path.expanduser()
        self.version = version
        self.state_path = self.target.parent / STATE_FILENAME

    def _read_prompt(self) -> str:
        if self.prompt_path.is_symlink() or not self.prompt_path.is_file():
            raise InstallError(
                f"提示词文件不存在或不安全 / Prompt is missing or unsafe: "
                f"{self.prompt_path}"
            )
        return read_text_if_exists(self.prompt_path)

    def _validate_state_path(self) -> None:
        if self.state_path.is_symlink():
            raise InstallError(
                f"状态文件不能是符号链接 / State must not be a symlink: "
                f"{self.state_path}"
            )

    def _snapshot(self, original: str) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%fZ")
        snapshot = self.target.parent / f"{self.target.name}.bak_{stamp}"
        atomic_write_text(snapshot, original, None)
        return snapshot

    def _write_state(self, prompt: str, block: ManagedBlock) -> None:
        self._validate_state_path()
        existing = read_text_if_exists(self.state_path)
        expected = sha256_text(existing) if self.state_path.exists() else None
        state = {
            "version": STATE_VERSION,
            "instruction_version": self.version,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "target": str(self.target.resolve()),
            "prompt_sha256": sha256_text(prompt),
            "block_sha256": sha256_text(block.text),
        }
        atomic_write_text(
            self.state_path,
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            expected,
        )

    def apply(self, dry_run: bool = False) -> InstallResult:
        prompt = self._read_prompt()
        current_exists = self.target.exists() or self.target.is_symlink()
        current = read_text_if_exists(self.target)
        old_block = locate_managed_block(current)
        updated = apply_managed_block(current, prompt, self.version)

        if updated == current:
            return InstallResult("already-installed", self.target, False)
        if dry_run:
            return InstallResult("would-install", self.target, False)

        self._validate_state_path()
        self.target.parent.mkdir(parents=True, exist_ok=True)
        snapshot = self._snapshot(current)
        expected = sha256_text(current) if current_exists else None
        atomic_write_text(self.target, updated, expected)
        block = locate_managed_block(updated)
        assert block is not None
        try:
            self._write_state(prompt, block)
        except InstallError as state_error:
            updated_sha256 = sha256_text(updated)
            try:
                if current_exists:
                    atomic_write_text(self.target, current, updated_sha256)
                else:
                    unlink_if_unchanged(self.target, updated_sha256)
            except InstallError as rollback_error:
                raise InstallError(
                    "状态写入失败且目标回滚失败 / State write and target rollback "
                    f"both failed: {state_error}; {rollback_error}"
                ) from state_error
            raise
        status = "updated" if old_block is not None else "installed"
        return InstallResult(status, self.target, True, snapshot)

    def reset(self, dry_run: bool = False) -> InstallResult:
        current_exists = self.target.exists() or self.target.is_symlink()
        current = read_text_if_exists(self.target)
        block = locate_managed_block(current)
        if block is None:
            return InstallResult("not-installed", self.target, False)

        updated = remove_managed_block(current)
        if dry_run:
            return InstallResult("would-remove", self.target, False)

        self._validate_state_path()
        snapshot = self._snapshot(current)
        expected = sha256_text(current) if current_exists else None
        assert expected is not None
        if updated.strip():
            atomic_write_text(self.target, updated, expected)
        else:
            unlink_if_unchanged(self.target, expected)

        if self.state_path.exists():
            state_text = read_text_if_exists(self.state_path)
            unlink_if_unchanged(self.state_path, sha256_text(state_text))
        return InstallResult("removed", self.target, True, snapshot)

    def status(self) -> InstallResult:
        current = read_text_if_exists(self.target)
        block = locate_managed_block(current)
        if block is None:
            return InstallResult("not-installed", self.target, False)

        prompt = self._read_prompt()
        expected = render_managed_block(
            prompt, self.version, detect_newline(current)
        )
        status = "installed" if block.text == expected else "modified"
        return InstallResult(status, self.target, False)


def interactive_action() -> Optional[str]:
    print("GLM-5.3 for ZCode 指令部署工具 / Instruction Installer")
    print("1. 安装或更新 / Apply or update")
    print("2. 卸载托管指令 / Remove managed instructions")
    print("3. 查看状态 / Show status")
    print("q. 退出 / Quit")
    while True:
        try:
            choice = input("请选择 / Select [1/2/3/q]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        actions = {"1": "apply", "2": "reset", "3": "status", "q": None}
        if choice in actions:
            return actions[choice]
        print("[错误] 请输入 1、2、3 或 q / Enter 1, 2, 3, or q.")


def print_result(result: InstallResult, action: str) -> None:
    if action == "status":
        messages = {
            "installed": "已安装 / installed",
            "modified": "已安装但内容已修改 / installed but modified",
            "not-installed": "未安装 / not installed",
        }
    else:
        messages = {
            "installed": "安装成功 / installed",
            "updated": "更新成功 / updated",
            "already-installed": "已是最新 / already installed",
            "would-install": "预览 / dry run: 将安装或更新 / would install or update",
            "removed": "已移除 / removed",
            "would-remove": "预览 / dry run: 将移除 / would remove",
            "not-installed": "未安装，无需修改 / not installed; no change",
        }
    print(messages.get(result.status, result.status))
    print(f"目标 / Target: {result.target}")
    if result.snapshot is not None:
        print(f"快照 / Snapshot: {result.snapshot}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deploy or remove GLM-5.3 instructions for ZCode."
    )
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument("--apply", action="store_true", help="Apply instructions")
    action_group.add_argument("--reset", action="store_true", help="Remove instructions")
    action_group.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writes")
    parser.add_argument(
        "--agents-file",
        type=Path,
        default=Path.home() / ".zcode" / "AGENTS.md",
        help="Override the ZCode user AGENTS.md path",
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        default=Path(__file__).resolve().parent / DEFAULT_PROMPT_FILENAME,
        help="Override the instruction Markdown path",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {PACKAGE_VERSION}"
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.apply:
        action = "apply"
    elif args.reset:
        action = "reset"
    elif args.status:
        action = "status"
    else:
        action = interactive_action()

    if action is None:
        print("未执行修改 / No modification made.")
        return 0

    installer = Installer(args.agents_file, args.prompt_file, INSTRUCTION_VERSION)
    try:
        if action == "apply":
            result = installer.apply(dry_run=args.dry_run)
        elif action == "reset":
            result = installer.reset(dry_run=args.dry_run)
        else:
            result = installer.status()
        print_result(result, action)
        return 0
    except (ManagedBlockError, InstallError) as exc:
        print(f"[错误 / Error] {exc}", file=sys.stderr)
        return 2
    except (OSError, UnicodeError) as exc:
        print(f"[错误 / Error] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
