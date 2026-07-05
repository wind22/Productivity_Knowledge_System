#!/usr/bin/env python3
"""知识库质量检查：相对链接有效性 + front matter 完整性。

用法：python3 scripts/check_links.py（在仓库根目录运行，CI 与本地通用）
退出码：0 = 全部通过；1 = 存在断链或缺失 front matter。
"""
import os
import re
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

# 有意保留的"断链"白名单：模板内的路径占位符（以模板被复制后的位置为准书写）
# 格式：(文件相对路径, 链接原文)
ALLOWED_BROKEN = {
    ("09-案例库/案例模板.md", "../../03-运营/3.3-方法论.md"),
    ("09-案例库/案例模板.md", "../案例模板.md"),
}

# 需要 front matter 的文件范围之外的例外
FRONT_MATTER_EXEMPT = {"CLAUDE.md"}

REQUIRED_KEYS = ("title", "chapter", "layer", "domain", "updated")


def iter_markdown_files():
    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", ".github", "scripts", "node_modules")]
        for name in sorted(files):
            if name.endswith(".md"):
                yield os.path.join(dirpath, name)


def check_links(path, text, errors):
    rel = os.path.relpath(path, ROOT)
    dirpath = os.path.dirname(path)
    for match in LINK_PATTERN.finditer(text):
        raw = match.group(1).strip()
        if raw.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = urllib.parse.unquote(raw.split("#")[0])
        if not target:
            continue
        if (rel, raw) in ALLOWED_BROKEN or (rel, target) in ALLOWED_BROKEN:
            continue
        resolved = os.path.normpath(os.path.join(dirpath, target))
        if not os.path.exists(resolved):
            errors.append(f"断链: {rel} -> {raw}")


def check_front_matter(path, text, errors):
    rel = os.path.relpath(path, ROOT)
    if os.path.basename(path) in FRONT_MATTER_EXEMPT:
        return
    if not text.startswith("---\n"):
        errors.append(f"缺少 front matter: {rel}")
        return
    end = text.find("\n---", 4)
    if end == -1:
        errors.append(f"front matter 未闭合: {rel}")
        return
    block = text[4:end]
    for key in REQUIRED_KEYS:
        if not re.search(rf"^{key}:", block, re.MULTILINE):
            errors.append(f"front matter 缺少字段 {key}: {rel}")


def main():
    errors = []
    count = 0
    for path in iter_markdown_files():
        count += 1
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        check_links(path, text, errors)
        check_front_matter(path, text, errors)
    if errors:
        print(f"检查了 {count} 个文件，发现 {len(errors)} 个问题：")
        for err in errors:
            print(f"  {err}")
        return 1
    print(f"检查了 {count} 个文件，链接与 front matter 全部通过 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
