#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qmd-lite-search.py

轻量替代 QMD 的本地搜索工具：
- 搜索 workspace 下的 markdown / txt / json 文件
- 基于关键词命中次数、标题命中、路径命中做简单打分
- 输出文件、行号、片段，适合快速定位记忆/文档

用法:
  python3 scripts/qmd-lite-search.py "宣传部 温州 视频"
  python3 scripts/qmd-lite-search.py "森空岛 自动签到" --top 10
"""

import argparse
import os
import re
from pathlib import Path

ROOT = Path('/home/admin/.openclaw/workspace')
INCLUDE_EXT = {'.md', '.txt', '.json', '.py', '.sh', '.yaml', '.yml'}
EXCLUDE_DIRS = {'.git', 'node_modules', '.openclaw', 'MemOS/.git'}


def tokenize(q: str):
    return [t.strip().lower() for t in re.split(r'\s+', q) if t.strip()]


def iter_files(root: Path):
    for p in root.rglob('*'):
        if not p.is_file():
            continue
        if p.suffix.lower() not in INCLUDE_EXT:
            continue
        rel = p.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        yield p


def score_text(path: Path, text: str, terms):
    lower = text.lower()
    score = 0
    for t in terms:
        hits = lower.count(t)
        score += hits
        if path.name.lower().find(t) >= 0:
            score += 8
        if ('# ' + t) in lower or ('## ' + t) in lower:
            score += 5
    return score


def best_snippets(text: str, terms, max_snips=3):
    lines = text.splitlines()
    found = []
    for idx, line in enumerate(lines, 1):
        lower = line.lower()
        if all(t in lower for t in terms[:1]) or any(t in lower for t in terms):
            found.append((idx, line.strip()))
        if len(found) >= max_snips:
            break
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('query')
    ap.add_argument('--top', type=int, default=8)
    args = ap.parse_args()

    terms = tokenize(args.query)
    results = []
    for p in iter_files(ROOT):
        try:
            text = p.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        score = score_text(p, text, terms)
        if score <= 0:
            continue
        snippets = best_snippets(text, terms)
        results.append((score, p, snippets))

    results.sort(key=lambda x: x[0], reverse=True)
    for i, (score, path, snippets) in enumerate(results[: args.top], 1):
        print(f'[{i}] score={score} file={path.relative_to(ROOT)}')
        for ln, snip in snippets:
            print(f'  L{ln}: {snip[:180]}')
        print()


if __name__ == '__main__':
    main()
