"""生成全书知识图谱可视化 HTML（Mermaid 渲染版）"""
import re, json

text = open(r'e:\nlp\ltp\kg_book_full.txt', encoding='utf-8').read()
lines = text.split('\n')

# 去重提取目录
seen = set()
toc = []
for line in lines:
    line = line.strip()
    if not line:
        continue
    m = re.match(r'^第([一二三四五六七八九十\d]+)章\s+(.+)$', line)
    if m:
        title = f"第{m.group(1)}章 {m.group(2)}"
        if title not in seen:
            seen.add(title)
            toc.append((0, title))
        continue
    m = re.match(r'^(\d+)\.(\d+)\s+(.+)$', line)
    if m:
        title = f"{m.group(1)}.{m.group(2)} {m.group(3)}"
        key = f"sec-{m.group(1)}.{m.group(2)}"
        if key not in seen:
            seen.add(key)
            toc.append((1, title, m.group(1)))

chapters = [t for t in toc if t[0] == 0]

# 生成 Mermaid 代码
mmd_lines = ['flowchart TD']
mmd_lines.append('')
mmd_lines.append('    %% 样式')
mmd_lines.append('    classDef ch fill:#4A90D9,color:#fff,stroke:#2E5A8A,stroke-width:2px')
mmd_lines.append('    classDef sec fill:#f8f9fa,color:#333,stroke:#50C878,stroke-width:1px')
mmd_lines.append('    classDef conn fill:none,stroke:#FF8C42,stroke-width:3px')
mmd_lines.append('')

ch_ids = {}
for i, item in enumerate(chapters):
    nid = f'CH{i}'
    ch_ids[item[1]] = nid
    esc = item[1].replace('"', "'")
    mmd_lines.append(f'    {nid}["{esc}"]:::ch')

# 节节点
sec_count = 0
for item in toc:
    if item[0] == 1:
        nid = f'SEC{sec_count}'
        sec_count += 1
        esc = item[1].replace('"', "'")
        mmd_lines.append(f'    {nid}["{esc}"]:::sec')

# 连接
sec_count = 0
for item in toc:
    if item[0] == 1:
        nid = f'SEC{sec_count}'
        sec_count += 1
        ch_idx_num = int(item[2])
        ch_key = chapters[ch_idx_num - 1][1]
        parent = ch_ids.get(ch_key)
        if parent:
            mmd_lines.append(f'    {parent} --> {nid}')

# 章间连接
for i in range(len(chapters) - 1):
    src = ch_ids[chapters[i][1]]
    dst = ch_ids[chapters[i+1][1]]
    mmd_lines.append(f'    {src} ==> {dst}')

mmd_code = '\n'.join(mmd_lines)

# 保存 Mermaid 文件
with open(r'e:\nlp\ltp\kg_book_full_v2.mmd', 'w', encoding='utf-8') as f:
    f.write(mmd_code)
print(f"✅ Mermaid 保存: kg_book_full_v2.mmd")

# 生成 HTML
html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>知识图谱 方法、实践与应用 - 全书知识图谱</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
  body {{ font-family: 'Microsoft YaHei', sans-serif; margin: 20px; background: #f5f5f5; }}
  h1 {{ text-align: center; color: #333; font-size: 24px; }}
  .container {{ max-width: 1200px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); }}
  .mermaid {{ text-align: center; }}
  .legend {{ margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; }}
  .legend-item {{ display: inline-block; margin-right: 20px; }}
  .legend-color {{ display: inline-block; width: 20px; height: 20px; border-radius: 4px; vertical-align: middle; margin-right: 5px; }}
  .structure {{ margin-top: 30px; columns: 3; column-gap: 30px; }}
  .ch-block {{ break-inside: avoid; margin-bottom: 20px; }}
  .ch-title {{ background: #4A90D9; color: #fff; padding: 8px 12px; border-radius: 6px; font-weight: bold; font-size: 14px; }}
  .sec-list {{ margin: 8px 0 0 16px; }}
  .sec-item {{ color: #333; font-size: 13px; line-height: 1.8; list-style: none; }}
  .sec-item::before {{ content: "▸ "; color: #50C878; }}
</style>
</head>
<body>
<div class="container">
  <h1>📚 《知识图谱 方法、实践与应用》全书知识图谱</h1>
  <p style="text-align:center;color:#666;margin-bottom:20px;">共 {len(chapters)} 章 · {sec_count} 节 · 全书知识框架可视化</p>
  
  <div class="mermaid">
{mmd_code}
  </div>

  <div class="legend">
    <div class="legend-item"><span class="legend-color" style="background:#4A90D9;"></span> 章</div>
    <div class="legend-item"><span class="legend-color" style="background:#f8f9fa;border:1px solid #50C878;"></span> 节</div>
    <div class="legend-item"><span class="legend-color" style="background:#FF8C42;"></span> 章间逻辑关系</div>
  </div>
  
  <div class="structure">
'''

for item in toc:
    if item[0] == 0:
        html += f'    <div class="ch-block"><div class="ch-title">{item[1]}</div><ul class="sec-list">\n'
    elif item[0] == 1:
        html += f'      <li class="sec-item">{item[1]}</li>\n'

html += '''    </div>
</div>

<script>
  mermaid.initialize({ 
    startOnLoad: true,
    theme: 'default',
    flowchart: { 
      useMaxWidth: true,
      htmlLabels: true,
      curve: 'basis'
    }
  });
</script>
</body>
</html>'''

with open(r'e:\nlp\ltp\kg_book_full_v2.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f"✅ HTML 可视化: kg_book_full_v2.html")

# ===== 2. 用 KGGen 处理关键章节内容 =====
# 对第1章各节提取关键词/实体
print("\n正在用 KGGen 处理第1章各节...")
import os, sys, urllib.request

os.environ['PATH'] = r'e:\ollama;' + os.environ.get('PATH', '')
os.environ['OLLAMA_MODELS'] = r'e:\ollama\models'

# 提取第1章各节内容
ch1_sections = []
current_section = None
in_ch1 = False
for line in lines:
    ls = line.strip()
    if ls == '第1章 知识图谱概述':
        in_ch1 = True
        continue
    if ls.startswith('第2章'):
        in_ch1 = False
        break
    if in_ch1 and re.match(r'^1\.\d+\s', ls):
        if current_section:
            ch1_sections.append(current_section)
        current_section = {'title': ls, 'content': ''}
    elif in_ch1 and current_section:
        current_section['content'] += line.strip()
if current_section:
    ch1_sections.append(current_section)

print(f"  第1章共 {len(ch1_sections)} 节")

# 用 KGGen 处理
from kg_gen import KGGen
kg = KGGen(model="ollama_chat/qwen2.5:3b", temperature=0.0, api_base="http://127.0.0.1:11434")

ch1_entities = set()
ch1_relations = []

for sec in ch1_sections:
    if len(sec['content']) < 50:
        continue
    try:
        print(f"  处理: {sec['title'][:20] if sec['title'] else '?'}...", end=' ')
        sys.stdout.flush()
        graph = kg.generate(input_data=sec['content'][:1500], context=f"知识图谱 - {sec['title']}", chunk_size=2000)
        ch1_entities.update(graph.entities)
        ch1_relations.extend(list(graph.relations))
        print(f"E:{len(graph.entities)} R:{len(graph.relations)}")
        sys.stdout.flush()
    except Exception as e:
        print(f"ERR: {str(e)[:30]}")
        sys.stdout.flush()

# 保存第1章 KG 结果
with open(r'e:\nlp\ltp\kg_book_ch1_kggen.txt', 'w', encoding='utf-8') as f:
    f.write(f"KGGen 第1章 知识图谱概述 结果\n")
    f.write(f"实体 ({len(ch1_entities)}):\n")
    for e in sorted(ch1_entities): f.write(f"  - {e}\n")
    f.write(f"\n三元组 ({len(ch1_relations)}):\n")
    for s,p,o in ch1_relations: f.write(f"  ({s}, {p}, {o})\n")
print(f"✅ 第1章 KG 结果: kg_book_ch1_kggen.txt")