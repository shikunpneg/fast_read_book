"""提取各节内容"""
import re

text = open(r'e:\nlp\ltp\kg_book_ch1-2.txt', encoding='utf-8').read()
lines = text.split('\n')

# 找到所有章节标题及其行号
sections = []
for i, line in enumerate(lines):
    line = line.strip()
    if re.match(r'^第\d+章\s', line):
        sections.append({'type': 'chapter', 'title': line, 'line': i})
    elif re.match(r'^\d+\.\d+\s', line):
        sections.append({'type': 'section', 'title': line, 'line': i})

# 提取每个章节标题后的内容（约500字符上下文）
output = []
for idx, sec in enumerate(sections):
    start_line = sec['line'] + 1
    if idx + 1 < len(sections):
        end_line = sections[idx + 1]['line']
    else:
        end_line = len(lines)
    
    # 提取【下一标题之前的全部内容】前 500 字符
    content_lines = lines[start_line:end_line]
    content = '\n'.join(content_lines).strip()
    
    # 去掉图/表题
    content = re.sub(r'图\d+-\d+.*?\n', '', content)
    content = re.sub(r'表\d+-\d+.*?\n', '', content)
    
    if len(content) > 500:
        content = content[:500] + '…'
    
    output.append({'title': sec['title'], 'type': sec['type'], 'content': content})

with open(r'e:\nlp\ltp\kg_book_sections.txt', 'w', encoding='utf-8') as f:
    for sec in output:
        f.write(f"=== {sec['type'].upper()}: {sec['title']} ===\n")
        f.write(f"{sec['content']}\n\n")

print(f"提取完成：{len(output)} 个章节/节")
for sec in output:
    label = f"[{sec['type']}] {sec['title']}"
    print(f"  {label}: {len(sec['content'])} 字符")