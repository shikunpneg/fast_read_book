"""调试脚本：检查 markdown-it-py 的 AST 结构"""
from markdown_it import MarkdownIt

md = MarkdownIt()
with open(r'e:\nlp\ltp\kg_book_full.md', 'r', encoding='utf-8') as f:
    md_text = f.read()

# 只取第1章内容（从第816行开始）
lines = md_text.split('\n')
ch1_start = 0
for i, line in enumerate(lines):
    if line.strip().startswith('# 第1章 知识图谱概述') and i > 500:
        ch1_start = i
        break

ch1_text = '\n'.join(lines[ch1_start:ch1_start + 200])
tokens = md.parse(ch1_text)

# 打印所有 token 类型
for i, t in enumerate(tokens):
    # 跳过 inline 和 text 的细节
    if t.type in ('inline', 'text'):
        tag = t.tag if hasattr(t, 'tag') else ''
        content = ''
        if t.children:
            content = ''.join(c.content for c in t.children if c.type == 'text')
        if content.strip():
            print(f'[{i:4d}] {t.type:20s} tag={tag} content="{content[:80]}"')
    elif t.type in ('paragraph_open', 'paragraph_close'):
        print(f'[{i:4d}] {t.type:20s}')
    else:
        tag = t.tag if hasattr(t, 'tag') else ''
        content = t.content if hasattr(t, 'content') else ''
        print(f'[{i:4d}] {t.type:20s} tag={tag} content="{content[:80]}"')