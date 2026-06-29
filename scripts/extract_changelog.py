#!/usr/bin/env python3
"""从 CHANGELOG.md 提取指定版本的发布说明。

用法: python scripts/extract_changelog.py 1.0.0
"""
import re
import sys
from pathlib import Path


def extract(version: str) -> str:
    p = Path(__file__).parent.parent / "CHANGELOG.md"
    text = p.read_text(encoding="utf-8")

    # 匹配 ## [version] - date 段
    pattern = rf"## \[{re.escape(version)}\][^\n]*\n+(.*?)(?=\n## \[|\n\[Unreleased\]:|\Z)"
    m = re.search(pattern, text, re.DOTALL)
    if not m:
        return f"Release v{version}\n\n暂无 CHANGELOG 条目。"

    body = m.group(1).strip()
    return f"## Release v{version}\n\n{body}"


if __name__ == "__main__":
    version = sys.argv[1] if len(sys.argv) > 1 else "1.0.0"
    print(extract(version))
