"""
TXT → Markdown 转换脚本
将 kg_book_full.txt 转换为带层级结构的 kg_book_full.md
"""
import re

INPUT = r'e:\nlp\ltp\kg_book_full.txt'
OUTPUT = r'e:\nlp\ltp\kg_book_full.md'

with open(INPUT, 'r', encoding='utf-8') as f:
    lines = f.readlines()

out_lines = []
in_refs = False  # 是否在参考文献段落中

for line in lines:
    stripped = line.strip()
    
    # 跳过空行
    if not stripped:
        if not in_refs:
            out_lines.append('')
        continue
    
    # 检测章节标题: "第X章 ..."
    ch_match = re.match(r'^第([\d一二三四五六七八九十]+)章\s+(.+)', stripped)
    if ch_match:
        in_refs = False
        out_lines.append(f'\n# {stripped}\n')
        continue
    
    # 检测子章节: "X.Y.Z ..." 或 "X.Y ..."
    sec_match = re.match(r'^(\d+(?:\.\d+){1,2})\s+(.+)', stripped)
    if sec_match:
        in_refs = False
        level = sec_match.group(1).count('.')  # 1 → ##, 2 → ###
        prefix = '#' * (level + 1)
        out_lines.append(f'\n{prefix} {stripped}\n')
        continue
    
    # 检测 "参考文献" 标记
    if re.match(r'^参考(文献|资料)', stripped) or stripped == '参考文献':
        in_refs = True
        out_lines.append(f'\n## {stripped}\n')
        continue
    
    # 检测 "本章小结"
    if re.match(r'^本章小结', stripped):
        in_refs = False
        out_lines.append(f'\n## {stripped}\n')
        continue
    
    # 检测 "X.X.X.X" 更深层级 (4级)
    deep_match = re.match(r'^(\d+(?:\.\d+){3})\s+(.+)', stripped)
    if deep_match:
        in_refs = False
        out_lines.append(f'\n#### {stripped}\n')
        continue
    
    # 检测列表项: "（1）" 或 "1）" 或 "①" 开头 (允许括号后无空格)
    list_match = re.match(r'^[（(]?(\d+)[）)]\s*(.+)', stripped)
    if list_match and len(stripped) > 5:
        out_lines.append(f'- {stripped}')
        continue
    
    # 检测 "1.xxx" 格式 (数字+点+中文，无空格，非章节号)
    # 例如: "1.基于模板的关系抽取方法" → 列表项
    if re.match(r'^\d+\.[\u4e00-\u9fff]', stripped) and not re.match(r'^\d+\.\d+', stripped):
        out_lines.append(f'- {stripped}')
        continue
    
    # 检测带编号的列表: "1. " 开头 (有空格，但不能是章节号)
    if re.match(r'^\d+\.\s+\S', stripped) and not re.match(r'^\d+\.\d+', stripped):
        out_lines.append(f'- {stripped}')
        continue
    
    # 检测 ●/•/· 等符号开头的项目符号列表 (加空行防止 lazy continuation)
    if re.match(r'^[●•·]\s*', stripped):
        out_lines.append('')  # 空行防止与上一个列表项合并
        out_lines.append(f'- {re.sub(r"^[●•·]\s*", "", stripped)}')
        continue
    
    # 参考文献中的内容，转换为列表
    if in_refs and re.match(r'^\[\d+\]', stripped):
        out_lines.append(f'- {stripped}')
        continue
    
    # 参考文献中的内容（无编号的）
    if in_refs:
        out_lines.append(f'  {stripped}')
        continue
    
    # 普通段落
    out_lines.append(stripped)

# 写入文件
with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out_lines))

# 统计
md_text = open(OUTPUT, 'r', encoding='utf-8').read()
h1 = len(re.findall(r'^# ', md_text, re.MULTILINE))
h2 = len(re.findall(r'^## ', md_text, re.MULTILINE))
h3 = len(re.findall(r'^### ', md_text, re.MULTILINE))
h4 = len(re.findall(r'^#### ', md_text, re.MULTILINE))
lists = len(re.findall(r'^- ', md_text, re.MULTILINE))
print(f'Markdown 生成完成:')
print(f'  H1 (章): {h1}')
print(f'  H2 (节): {h2}')
print(f'  H3 (子节): {h3}')
print(f'  H4 (细目): {h4}')
print(f'  列表项: {lists}')
print(f'  总字符: {len(md_text)}')
print(f'  → {OUTPUT}')