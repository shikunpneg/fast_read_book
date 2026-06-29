"""调试脚本：检查列表项在 markdown-it-py AST 中的结构"""
from markdown_it import MarkdownIt

md = MarkdownIt()
with open(r'e:\nlp\ltp\kg_book_full.md', 'r', encoding='utf-8') as f:
    md_text = f.read()

# 找第一个列表区域
lines = md_text.split('\n')
start = 0
for i, line in enumerate(lines):
    if line.startswith('- ') and i > 1000:
        start = i - 5
        break

chunk = '\n'.join(lines[start:start + 30])
print("=== MD 原文 ===")
print(chunk)
print("\n=== AST ===")

tokens = md.parse(chunk)
for i, t in enumerate(tokens):
    if t.type == 'inline' and t.children:
        content = ''.join(c.content for c in t.children if c.type == 'text')
        if content.strip():
            print(f'[{i:4d}] {t.type:20s} content="{content[:100]}"')
    elif t.type not in ('inline', 'text'):
        tag = t.tag if hasattr(t, 'tag') else ''
        content = t.content if hasattr(t, 'content') else ''
        info = t.info if hasattr(t, 'info') else ''
        print(f'[{i:4d}] {t.type:20s} tag={tag} info={info}')