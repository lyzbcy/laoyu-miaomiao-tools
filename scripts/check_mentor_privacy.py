#!/usr/bin/env python3
"""Check the two public mentor skills; optional private terms stay outside this repo.

This flags likely leaks, not proof of anonymity. Review prose and Git history too.
"""
import argparse
import json
from pathlib import Path
import re
import sys

NAMES = ("lyzbcy-tudou-mentor", "lyzbcy-laotian-cosleader")
RULES = {
    "absolute local path": r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]|/(?:Users|home)/[^/\s]+|\\\\[^\s\\]+\\",
    "credential value": r"(?i)\b(?:bearer\s+[a-z0-9._-]{12,}|(?:access_token|api_key|password|authorization)\s*[:=]\s*[\"']?[a-z0-9._/-]{8,})",
    "private key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "historical attribution": r"原话[：:]|逐字原话|逐字对话|一对一聊天|真实履历[：:]",
    "email address": r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}",
}


def inspect(skill, private_terms=()):
    entry = (skill / "SKILL.md").read_text(encoding="utf-8")
    manifest = re.findall(r"^    - (\S+)\s*$", entry, re.M)
    findings = []
    if not manifest:
        return [("SKILL.md", 0, "missing public manifest")]
    for rel in manifest:
        path = (skill / rel).resolve()
        if not path.is_relative_to(skill.resolve()) or not path.is_file():
            findings.append((rel, 0, "invalid manifest path"))
    disk = {p.relative_to(skill).as_posix() for p in skill.rglob("*") if p.is_file()}
    for rel in sorted(disk - set(manifest) - {".update-check.json"}):
        # Older runtimes may leave the same harmless state under references.
        if rel == "references/.update-check.json":
            continue
        findings.append((rel, 0, "file outside public manifest"))
    for rel in manifest:
        path = skill / rel
        if not path.is_file():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for label, pattern in RULES.items():
                if re.search(pattern, line):
                    findings.append((rel, number, label))
            if any(term.casefold() in line.casefold() for term in private_terms):
                findings.append((rel, number, "private term"))
            for url in re.findall(r"https?://[^\s)>\"']+", line):
                if not url.startswith((
                    "https://raw.githubusercontent.com/lyzbcy/laoyu-miaomiao-tools/",
                    "https://github.com/lyzbcy/laoyu-miaomiao-tools",
                )):
                    findings.append((rel, number, "URL requires review"))
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-root", type=Path, default=Path(__file__).resolve().parent.parent / "skills")
    parser.add_argument("--private-terms", type=Path, help="External UTF-8 JSON string list; never copied into output")
    args = parser.parse_args()
    terms = json.loads(args.private_terms.read_text(encoding="utf-8")) if args.private_terms else []
    if not isinstance(terms, list) or any(not isinstance(x, str) or not x for x in terms):
        parser.error("private terms must be a list of non-empty strings")
    failed = False
    for name in NAMES:
        findings = inspect(args.skills_root / name, terms)
        for rel, line, label in findings:
            print(f"{name}/{rel}:{line}: {label}")
        if not findings:
            print(f"PASS {name}: public content checks")
        failed |= bool(findings)
    print("Automated checks do not inspect Git history, remote assets, or guarantee anonymity.")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
