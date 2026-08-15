from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Optional
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "zcode_instruct", ROOT / "zcode-instruct.py"
)
assert SPEC and SPEC.loader
zcode_instruct = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = zcode_instruct
SPEC.loader.exec_module(zcode_instruct)


class BlockTransformTests(unittest.TestCase):
    def test_apply_to_empty_text(self):
        result = zcode_instruct.apply_managed_block("", "PROMPT", "1")
        self.assertEqual(
            result,
            "<!-- glm-5.3-zcode-instruct:begin version=1 -->\n"
            "PROMPT\n"
            "<!-- glm-5.3-zcode-instruct:end -->\n",
        )

    def test_append_preserves_existing_content(self):
        result = zcode_instruct.apply_managed_block("personal\n", "PROMPT", "1")
        self.assertEqual(
            result,
            "personal\n"
            "<!-- glm-5.3-zcode-instruct:begin version=1 -->\n"
            "PROMPT\n"
            "<!-- glm-5.3-zcode-instruct:end -->\n",
        )

    def test_update_preserves_text_outside_block(self):
        original = (
            "before\n"
            "<!-- glm-5.3-zcode-instruct:begin version=0 -->\n"
            "old\n"
            "<!-- glm-5.3-zcode-instruct:end -->\n"
            "after\n"
        )
        result = zcode_instruct.apply_managed_block(original, "new", "1")
        self.assertEqual(
            result,
            "before\n"
            "<!-- glm-5.3-zcode-instruct:begin version=1 -->\n"
            "new\n"
            "<!-- glm-5.3-zcode-instruct:end -->\n"
            "after\n",
        )

    def test_second_apply_is_idempotent(self):
        once = zcode_instruct.apply_managed_block("personal\n", "PROMPT", "1")
        self.assertEqual(
            zcode_instruct.apply_managed_block(once, "PROMPT", "1"), once
        )

    def test_crlf_is_preserved(self):
        result = zcode_instruct.apply_managed_block("personal\r\n", "A\nB", "1")
        self.assertNotIn("\n", result.replace("\r\n", ""))

    def test_remove_returns_original_surrounding_content(self):
        installed = zcode_instruct.apply_managed_block(
            "before\nafter\n", "PROMPT", "1"
        )
        self.assertEqual(
            zcode_instruct.remove_managed_block(installed), "before\nafter\n"
        )

    def test_remove_without_block_is_idempotent(self):
        self.assertEqual(zcode_instruct.remove_managed_block("personal\n"), "personal\n")

    def test_malformed_markers_are_rejected(self):
        cases = [
            "<!-- glm-5.3-zcode-instruct:begin version=1 -->\nx\n",
            "<!-- glm-5.3-zcode-instruct:end -->\n",
            (
                "<!-- glm-5.3-zcode-instruct:end -->\n"
                "<!-- glm-5.3-zcode-instruct:begin version=1 -->\n"
            ),
            (
                "<!-- glm-5.3-zcode-instruct:begin version=1 -->\n"
                "a\n"
                "<!-- glm-5.3-zcode-instruct:end -->\n"
                "<!-- glm-5.3-zcode-instruct:begin version=1 -->\n"
                "b\n"
                "<!-- glm-5.3-zcode-instruct:end -->\n"
            ),
        ]
        for text in cases:
            with self.subTest(text=text):
                with self.assertRaises(zcode_instruct.ManagedBlockError):
                    zcode_instruct.apply_managed_block(text, "PROMPT", "1")

    def test_invalid_begin_version_is_rejected(self):
        text = (
            "<!-- glm-5.3-zcode-instruct:begin version= -->\n"
            "x\n"
            "<!-- glm-5.3-zcode-instruct:end -->\n"
        )
        with self.assertRaises(zcode_instruct.ManagedBlockError):
            zcode_instruct.apply_managed_block(text, "PROMPT", "1")


class InstallerLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="glm53 中文 ")
        self.root = Path(self.temp.name)
        self.target = self.root / "ZCode 配置" / ".zcode" / "AGENTS.md"
        self.prompt = self.root / "prompt.md"
        self.prompt.write_text("PROMPT\n", encoding="utf-8")
        self.installer = zcode_instruct.Installer(self.target, self.prompt, "1")

    def tearDown(self):
        self.temp.cleanup()

    def test_apply_status_reset_lifecycle(self):
        applied = self.installer.apply()
        self.assertEqual(applied.status, "installed")
        self.assertTrue(applied.changed)
        self.assertTrue(self.target.exists())

        status = self.installer.status()
        self.assertEqual(status.status, "installed")
        self.assertFalse(status.changed)

        removed = self.installer.reset()
        self.assertEqual(removed.status, "removed")
        self.assertTrue(removed.changed)
        self.assertFalse(self.target.exists())

    def test_existing_content_and_permissions_survive(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text("personal\n", encoding="utf-8")
        self.target.chmod(0o640)

        self.installer.apply()
        self.installer.reset()

        self.assertEqual(self.target.read_text(encoding="utf-8"), "personal\n")
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o640)

    def test_apply_creates_snapshot_and_state(self):
        result = self.installer.apply()

        self.assertIsNotNone(result.snapshot)
        assert result.snapshot is not None
        self.assertTrue(result.snapshot.exists())
        self.assertEqual(result.snapshot.read_text(encoding="utf-8"), "")

        state_path = self.target.parent / zcode_instruct.STATE_FILENAME
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["version"], zcode_instruct.STATE_VERSION)
        self.assertEqual(state["instruction_version"], "1")
        self.assertEqual(
            state["prompt_sha256"], zcode_instruct.sha256_text("PROMPT\n")
        )
        self.assertEqual(state["target"], str(self.target.resolve()))

    def test_repeated_apply_is_idempotent(self):
        self.installer.apply()
        snapshots_before = list(self.target.parent.glob("AGENTS.md.bak_*"))

        result = self.installer.apply()

        self.assertEqual(result.status, "already-installed")
        self.assertFalse(result.changed)
        self.assertEqual(
            list(self.target.parent.glob("AGENTS.md.bak_*")), snapshots_before
        )

    def test_dry_run_writes_nothing(self):
        result = self.installer.apply(dry_run=True)

        self.assertEqual(result.status, "would-install")
        self.assertFalse(result.changed)
        self.assertFalse(self.target.exists())
        self.assertFalse(self.target.parent.exists())

    def test_reset_dry_run_preserves_install(self):
        self.installer.apply()

        result = self.installer.reset(dry_run=True)

        self.assertEqual(result.status, "would-remove")
        self.assertFalse(result.changed)
        self.assertTrue(self.target.exists())

    def test_status_reports_modified_prompt(self):
        self.installer.apply()
        text = self.target.read_text(encoding="utf-8")
        self.target.write_text(text.replace("PROMPT", "USER EDIT"), encoding="utf-8")

        result = self.installer.status()

        self.assertEqual(result.status, "modified")

    def test_reset_without_managed_block_is_noop(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text("personal\n", encoding="utf-8")

        result = self.installer.reset()

        self.assertEqual(result.status, "not-installed")
        self.assertFalse(result.changed)
        self.assertEqual(self.target.read_text(encoding="utf-8"), "personal\n")

    def test_missing_prompt_is_rejected(self):
        installer = zcode_instruct.Installer(
            self.target, self.root / "missing.md", "1"
        )
        with self.assertRaises(zcode_instruct.InstallError):
            installer.apply()

    @unittest.skipIf(os.name == "nt", "symlink permission varies on Windows")
    def test_target_symlink_is_rejected(self):
        real = self.root / "real.md"
        real.write_text("personal\n", encoding="utf-8")
        self.target.parent.mkdir(parents=True)
        self.target.symlink_to(real)

        with self.assertRaises(zcode_instruct.InstallError):
            self.installer.apply()
        self.assertEqual(real.read_text(encoding="utf-8"), "personal\n")

    @unittest.skipIf(os.name == "nt", "symlink permission varies on Windows")
    def test_state_symlink_is_rejected(self):
        self.target.parent.mkdir(parents=True)
        referent = self.root / "state-referent.json"
        referent.write_text("untouched", encoding="utf-8")
        state_path = self.target.parent / zcode_instruct.STATE_FILENAME
        state_path.symlink_to(referent)

        with self.assertRaises(zcode_instruct.InstallError):
            self.installer.apply()
        self.assertEqual(referent.read_text(encoding="utf-8"), "untouched")

    def test_concurrent_target_change_is_not_overwritten(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text("personal\n", encoding="utf-8")
        real_atomic_write = zcode_instruct.atomic_write_text

        def change_then_write(path, text, expected_sha256):
            if path == self.target:
                self.target.write_text("external edit\n", encoding="utf-8")
            return real_atomic_write(path, text, expected_sha256)

        with mock.patch.object(
            zcode_instruct, "atomic_write_text", side_effect=change_then_write
        ):
            with self.assertRaises(zcode_instruct.ConcurrentModificationError):
                self.installer.apply()

        self.assertEqual(
            self.target.read_text(encoding="utf-8"), "external edit\n"
        )

    def test_state_write_failure_rolls_back_target(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text("personal\n", encoding="utf-8")
        real_atomic_write = zcode_instruct.atomic_write_text

        def fail_state_write(path, text, expected_sha256):
            if path == self.installer.state_path:
                raise zcode_instruct.InstallError("simulated state failure")
            return real_atomic_write(path, text, expected_sha256)

        with mock.patch.object(
            zcode_instruct, "atomic_write_text", side_effect=fail_state_write
        ):
            with self.assertRaises(zcode_instruct.InstallError):
                self.installer.apply()

        self.assertEqual(self.target.read_text(encoding="utf-8"), "personal\n")


class CliTests(unittest.TestCase):
    def run_cli(
        self,
        *args: str,
        input_text: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "zcode-instruct.py"), *args],
            text=True,
            input=input_text,
            capture_output=True,
            check=False,
            env=env,
        )

    def test_apply_status_reset_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / ".zcode" / "AGENTS.md"
            prompt = root / "prompt.md"
            prompt.write_text("PROMPT\n", encoding="utf-8")
            common = [
                "--agents-file",
                str(target),
                "--prompt-file",
                str(prompt),
            ]

            applied = self.run_cli("--apply", *common)
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertIn("安装成功 / installed", applied.stdout)

            status = self.run_cli("--status", *common)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("已安装 / installed", status.stdout)

            reset = self.run_cli("--reset", *common)
            self.assertEqual(reset.returncode, 0, reset.stderr)
            self.assertIn("已移除 / removed", reset.stdout)

    def test_dry_run_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / ".zcode" / "AGENTS.md"
            prompt = root / "prompt.md"
            prompt.write_text("PROMPT\n", encoding="utf-8")

            result = self.run_cli(
                "--apply",
                "--dry-run",
                "--agents-file",
                str(target),
                "--prompt-file",
                str(prompt),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("预览 / dry run", result.stdout)
            self.assertFalse(target.exists())

    def test_malformed_target_returns_two(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "AGENTS.md"
            prompt = root / "prompt.md"
            target.write_text(
                "<!-- glm-5.3-zcode-instruct:end -->\n", encoding="utf-8"
            )
            prompt.write_text("PROMPT\n", encoding="utf-8")

            result = self.run_cli(
                "--apply",
                "--agents-file",
                str(target),
                "--prompt-file",
                str(prompt),
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("标记", result.stderr)

    def test_default_target_uses_zcode_user_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompt = root / "prompt.md"
            prompt.write_text("PROMPT\n", encoding="utf-8")
            env = os.environ.copy()
            env["HOME"] = str(root)
            env["USERPROFILE"] = str(root)

            result = self.run_cli(
                "--apply", "--prompt-file", str(prompt), env=env
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / ".zcode" / "AGENTS.md").exists())

    def test_interactive_quit_changes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "AGENTS.md"

            result = self.run_cli(
                "--agents-file", str(target), input_text="q\n"
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("未执行修改 / No modification made", result.stdout)
            self.assertFalse(target.exists())

    def test_version_flag(self):
        result = self.run_cli("--version")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1.0.0", result.stdout)


class PromptContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prompt = (ROOT / zcode_instruct.DEFAULT_PROMPT_FILENAME).read_text(
            encoding="utf-8"
        )

    def test_prompt_has_zcode_execution_contract(self):
        required = [
            "[MODE: GLM-5.3 ZCODE EXECUTOR]",
            "ZCode",
            "任务归一化",
            "首轮执行",
            "状态连续",
            "真实工件",
            "验证、失败恢复与回滚",
            "最终交付",
            "Skill",
            "Agent",
            "TodoWrite",
            "BEGIN.",
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.prompt)

    def test_prompt_has_no_codex_specific_configuration(self):
        forbidden = [
            "CODEX_HOME",
            "model_instructions_file",
            "config.toml",
            "gpt-5.6-sol",
        ]
        for phrase in forbidden:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.prompt)

    def test_prompt_has_all_zcode_tool_names(self):
        for tool_name in [
            "Read",
            "Edit",
            "Write",
            "Bash",
            "Glob",
            "Grep",
            "Skill",
            "Agent",
            "TodoWrite",
        ]:
            with self.subTest(tool_name=tool_name):
                self.assertIn(f"`{tool_name}`", self.prompt)

    def test_prompt_is_compact_enough_for_global_injection(self):
        self.assertLessEqual(len(self.prompt.encode("utf-8")), 12_000)


class PackagingTests(unittest.TestCase):
    def test_launchers_reference_shared_python_script(self):
        command = (ROOT / "install.command").read_text(encoding="utf-8")
        batch = (ROOT / "install.bat").read_text(encoding="utf-8")
        self.assertIn("zcode-instruct.py", command)
        self.assertIn("zcode-instruct.py", batch)
        self.assertIn("python3", command)
        self.assertIn("py -3", batch)
        self.assertIn("python", batch)

    def test_windows_launcher_preserves_child_exit_code(self):
        batch = (ROOT / "install.bat").read_text(encoding="utf-8")
        self.assertIn("EnableDelayedExpansion", batch)
        self.assertIn("!errorlevel!", batch)

    @unittest.skipIf(os.name == "nt", "POSIX executable bit is not used on Windows")
    def test_posix_entrypoints_are_executable(self):
        self.assertTrue(os.access(ROOT / "install.command", os.X_OK))
        self.assertTrue(os.access(ROOT / "zcode-instruct.py", os.X_OK))

    def test_skill_documents_all_lifecycle_commands(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for phrase in [
            "GLM-5.3",
            "ZCode",
            "--apply",
            "--reset",
            "--status",
            "--dry-run",
            "~/.zcode/AGENTS.md",
            "Python 3.9",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)

    def test_version_matches_installer_default(self):
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(version, zcode_instruct.PACKAGE_VERSION)

    def test_license_is_mit_for_project_owner(self):
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("MIT License", license_text)
        self.assertIn("2026 lyzbcy", license_text)


if __name__ == "__main__":
    unittest.main()
