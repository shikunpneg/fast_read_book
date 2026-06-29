"""提取全书目录"""
import re

text = open(r'e:\nlp\ltp\kg_book_full.txt', encoding='utf-8').read()
lines = text.split('\n')

# 提取所有章节标题
chapters = []
sections = []
subsections = []

for i, line in enumerate(lines):
    line = line.strip()
    if not line:
        continue
    # 章标题: 第X章 ...
    m = re.match(r'^第([一二三四五六七八九十\d]+)章\s+(.+)$', line)
    if m:
        chapters.append({'num': m.group(1), 'title': m.group(2), 'line': i})
        continue
    # 节标题: X.X ...
    m = re.match(r'^(\d+)\.(\d+)\s+(.+)$', line)
    if m:
        ch = int(m.group(1))
        sec = m.group(2)
        title = m.group(3)
        sections.append({'ch': ch, 'sec': sec, 'title': title, 'line': i})
        continue
    # 子节标题: X.X.X
    m = re.match(r'^(\d+)\.(\d+)\.(\d+)\s+(.+)$', line)
    if m:
        ch = int(m.group(1))
        sec = m.group(2)
        sub = m.group(3)
        title = m.group(4)
        subsections.append({'ch': ch, 'sec': sec, 'sub': sub, 'title': title, 'line': i})

print(f"章: {len(chapters)}")
for c in chapters:
    label = f"第{c['num']}章 {c['title']}"
    print(f"  {label}")

print(f"\n节: {len(sections)}")
for s in sections:
    label = f"  {s['ch']}.{s['sec']} {s['title']}"
    print(label)

print(f"\n子节: {len(subsections)}")
for s in subsections[:20]:
    label = f"  {s['ch']}.{s['sec']}.{s['sub']} {s['title']}"
    print(label)
if len(subsections) > 20:
    print(f"  ... 共{len(subsections)}个")

# 保存结构化目录
with open(r'e:\nlp\ltp\kg_book_toc.txt', 'w', encoding='utf-8') as f:
    f.write("# 知识图谱 方法、实践与应用 - 目录\n\n")
    for c in chapters:
        f.write(f"## 第{c['num']}章 {c['title']}\n\n")
        for s in sections:
            if s['ch'] == int(c['num']):
                f.write(f"### {s['ch']}.{s['sec']} {s['title']}\n\n")
        f.write("\n")

print(f"\n✅ 保存: kg_book_toc.txt")