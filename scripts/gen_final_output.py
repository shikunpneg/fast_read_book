"""组合最终输出：思维导图 + 知识图谱 + Mermaid + HTML"""
import re, json, os

# ===== 1. 读取 KGGen 结果 =====
with open(r'e:\nlp\ltp\kg_book_5ch_kggen.txt', encoding='utf-8') as f:
    kggen_text = f.read()

# 解析实体和关系
all_entities = set()
all_relations = []
in_entities = False
in_relations = False
for line in kggen_text.split('\n'):
    if line.startswith('=== 全部实体 ==='):
        in_entities = True
        in_relations = False
        continue
    if line.startswith('=== 全部三元组 ==='):
        in_entities = False
        in_relations = True
        continue
    if in_entities:
        m = re.match(r'\s*-\s+(.+)$', line)
        if m:
            all_entities.add(m.group(1).strip())
    if in_relations:
        m = re.match(r'\s*\((.+),\s*(.+),\s*(.+)\)$', line)
        if m:
            all_relations.append((m.group(1).strip(), m.group(2).strip(), m.group(3).strip()))

# ===== 2. 解析全书目录 =====
text = open(r'e:\nlp\ltp\kg_book_full.txt', encoding='utf-8').read()
lines = text.split('\n')

seen = set()
toc = []
for line in lines:
    ls = line.strip()
    if not ls: continue
    m = re.match(r'^第([一二三四五六七八九十\d]+)章\s+(.+)$', ls)
    if m:
        title = f"第{m.group(1)}章 {m.group(2)}"
        if title not in seen:
            seen.add(title)
            toc.append((0, title))
        continue
    m = re.match(r'^(\d+)\.(\d+)\s+(.+)$', ls)
    if m:
        title = f"{m.group(1)}.{m.group(2)} {m.group(3)}"
        key = f"sec-{m.group(1)}.{m.group(2)}"
        if key not in seen:
            seen.add(key)
            toc.append((1, title, m.group(1)))

# ===== 3. 生成 Markdown 思维导图（带 KG 注解） =====
md_lines = []
md_lines.append("# 📚 知识图谱 方法、实践与应用 全书知识框架\n")
md_lines.append("## 思维导图（附 KGGen 自动提取的关键实体）\n")
md_lines.append(f"> KGGen 从第1-5章提取 **{len(all_entities)} 个实体**、**{len(all_relations)} 条关系**\n")

ch_entities = {}
current_ch = None
# Parse KGGen result per chapter
for line in kggen_text.split('\n'):
    m = re.match(r'---\s+(第\d+章\s+.+?)\s+---$', line)
    if m:
        current_ch = m.group(1).strip()
        ch_entities[current_ch] = set()
    elif line.strip().startswith('实体') and ': ' in line and current_ch:
        parts = line.strip().split(': ', 1)
        if len(parts) > 1:
            names = parts[1].split(', ')
            ch_entities[current_ch].update(names)

for item in toc:
    if item[0] == 0:  # chapter
        ch_name = item[1]
        md_lines.append(f"\n## 📖 {ch_name}\n")
        if ch_name in ch_entities and ch_entities[ch_name]:
            ents = ch_entities[ch_name]
            md_lines.append(f"   > **关键实体**: {' · '.join(sorted(ents))}\n")
    elif item[0] == 1:  # section
        md_lines.append(f"    - **{item[1]}**\n")

# 全部实体列表
md_lines.append("\n### KGGen 提取的全部实体\n")
md_lines.append("| 实体 | 所属领域 |\n|------|----------|\n")
for e in sorted(all_entities):
    # 简单分类
    if e in ['RDF', 'RDFS', 'OWL', 'OWL2 Fragments', 'SPARQL', 'R2RML']:
        domain = "语义网标准"
    elif e in ['Freebase', 'Wikidata', 'DBpedia', 'Yago', 'ConceptNet5', 'WordNet']:
        domain = "开放知识库"
    elif e in ['Neo4j', 'gStore', 'Apache Jena', 'Protégé', 'DeepDive', 'LIMES']:
        domain = "开源工具"
    elif any(kw in e for kw in ['技术', '流程', '方法', '语言', '查询', '存储', '数据库']):
        domain = "技术概念"
    elif any(kw in e for kw in ['任务', '抽取', '挖掘', '融合', '推理']):
        domain = "核心任务"
    else:
        domain = "知识概念"
    md_lines.append(f"| {e} | {domain} |\n")

# 全部三元组
md_lines.append("\n### KGGen 提取的全部关系\n")
md_lines.append("```\n")
for s, p, o in all_relations:
    md_lines.append(f"({s}) --[{p}]--> ({o})\n")
md_lines.append("```\n")

with open(r'e:\nlp\ltp\kg_book_complete.md', 'w', encoding='utf-8') as f:
    f.writelines(md_lines)
print(f"✅ 完整思维导图: kg_book_complete.md")

# ===== 4. 生成 Mermaid 图（目录结构 + KG 实体） =====
mmd_lines = []
mmd_lines.append("flowchart TD\n")
mmd_lines.append("    %% 样式\n")
mmd_lines.append("    classDef ch fill:#4A90D9,color:#fff,stroke:#2E5A8A,stroke-width:2px\n")
mmd_lines.append("    classDef sec fill:#E8F4FD,color:#333,stroke:#50C878,stroke-width:1px\n")
mmd_lines.append("    classDef entity fill:#FFF3E0,color:#E65100,stroke:#FF8C42,stroke-width:1px\n")
mmd_lines.append("    classDef relation fill:none,stroke:#999,stroke-width:0.5px,stroke-dasharray: 5 5\n")

# 章节点
ch_nodes = {}
for i, item in enumerate(toc):
    if item[0] == 0:
        nid = f"CH{i}"
        ch_nodes[item[1]] = nid
        esc = item[1].replace('"', "'")
        mmd_lines.append(f'    {nid}["{esc}"]:::ch\n')

# 节节点 + 连接到章
for i, item in enumerate(toc):
    if item[0] == 1:
        nid = f"S{i}"
        ch_num = int(item[2])
        ch_keys = [k for k in ch_nodes.keys()]
        if ch_num <= len(ch_keys):
            parent = ch_keys[ch_num - 1]
            parent_id = ch_nodes.get(parent)
            if parent_id:
                esc = item[1].replace('"', "'")
                mmd_lines.append(f'    {nid}["{esc}"]:::sec\n')
                mmd_lines.append(f'    {parent_id} --> {nid}\n')

# 章间连接
ch_keys_sorted = sorted(ch_nodes.keys(), key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)
for i in range(len(ch_keys_sorted) - 1):
    src = ch_nodes[ch_keys_sorted[i]]
    dst = ch_nodes[ch_keys_sorted[i+1]]
    mmd_lines.append(f'    {src} ==> {dst}\n')

# 实体节点 + 连接到相关章节
entity_added = set()
for idx, (s, p, o) in enumerate(all_relations):
    # 找实体所属章节
    found_ch = None
    for ch_name, ents in ch_entities.items():
        if s in ents or o in ents:
            found_ch = ch_name
            break
    
    # 如果实体还没添加，添加到相关章节下
    for ent_name in [s, o]:
        if ent_name not in entity_added and len(ent_name) <= 20:
            nid = f"E{len(entity_added)}"
            entity_added.add(ent_name)
            esc = ent_name.replace('"', "'")
            mmd_lines.append(f'    {nid}["{esc}"]:::entity\n')
            # 连接到相关章节
            if found_ch and found_ch in ch_nodes:
                mmd_lines.append(f'    {ch_nodes[found_ch]} -.-> {nid}\n')

mmd_code = '\n'.join(mmd_lines)

with open(r'e:\nlp\ltp\kg_book_complete.mmd', 'w', encoding='utf-8') as f:
    f.write(mmd_code)
print(f"✅ Mermaid 图谱: kg_book_complete.mmd")

# ===== 5. 生成 HTML =====
html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>知识图谱 方法、实践与应用 - 全书知识图谱</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
  * { box-sizing: border-box; }
  body { font-family: 'Microsoft YaHei', sans-serif; margin: 0; background: #f0f2f5; color: #333; }
  .header { background: linear-gradient(135deg, #4A90D9 0%, #2E5A8A 100%); color: #fff; padding: 30px; text-align: center; }
  .header h1 { margin: 0 0 5px; font-size: 28px; }
  .header p { margin: 0; opacity: 0.9; font-size: 14px; }
  .stats { display: flex; justify-content: center; gap: 30px; margin-top: 15px; }
  .stat-item { text-align: center; }
  .stat-value { font-size: 28px; font-weight: bold; }
  .stat-label { font-size: 12px; opacity: 0.8; }
  .container { max-width: 1300px; margin: 20px auto; padding: 0 20px; }
  .card { background: #fff; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 20px; overflow: hidden; }
  .card-header { padding: 15px 20px; border-bottom: 1px solid #eee; font-weight: bold; font-size: 16px; }
  .card-body { padding: 20px; }
  .mermaid { text-align: center; overflow-x: auto; }
  .legend { display: flex; flex-wrap: wrap; gap: 15px; justify-content: center; padding: 10px 0; }
  .legend-item { display: flex; align-items: center; gap: 5px; font-size: 13px; }
  .legend-color { width: 16px; height: 16px; border-radius: 4px; display: inline-block; }
  
  .structure { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
  .ch-block { background: #f8f9ff; border-radius: 8px; padding: 12px; border-left: 4px solid #4A90D9; }
  .ch-block-2 { border-left-color: #50C878; }
  .ch-block-3 { border-left-color: #FF8C42; }
  .ch-block-4 { border-left-color: #9B59B6; }
  .ch-block-5 { border-left-color: #E74C3C; }
  .ch-block-6 { border-left-color: #1ABC9C; }
  .ch-block-7 { border-left-color: #F39C12; }
  .ch-block-8 { border-left-color: #3498DB; }
  .ch-block-9 { border-left-color: #2ECC71; }
  .ch-title { font-weight: bold; font-size: 14px; color: #2E5A8A; margin-bottom: 8px; }
  .sec-list { list-style: none; padding: 0; margin: 0; }
  .sec-item { font-size: 12px; color: #555; line-height: 1.8; padding-left: 12px; position: relative; }
  .sec-item::before { content: "▸"; position: absolute; left: 0; color: #50C878; }
  .entity-tags { margin-top: 8px; }
  .entity-tag { display: inline-block; background: #FFF3E0; color: #E65100; font-size: 11px; padding: 2px 8px; border-radius: 10px; margin: 2px; }

  .triples { font-family: 'Consolas', monospace; font-size: 13px; line-height: 1.8; }
  .triple { padding: 3px 0; }
  .triple-subject { color: #4A90D9; }
  .triple-predicate { color: #FF8C42; }
  .triple-object { color: #50C878; }
</style>
</head>
<body>
<div class="header">
  <h1>📚 《知识图谱 方法、实践与应用》全书知识图谱</h1>
  <p>基于 KGGen + LLM 自动提取的完整知识框架</p>
  <div class="stats">
    <div class="stat-item"><div class="stat-value">9</div><div class="stat-label">章节</div></div>
'''

html += f'    <div class="stat-item"><div class="stat-value">{len(ch_keys_sorted)}</div><div class="stat-label">章节域</div></div>\n'
html += f'    <div class="stat-item"><div class="stat-value">{len(all_entities)}</div><div class="stat-label">KG实体</div></div>\n'
html += f'    <div class="stat-item"><div class="stat-value">{len(all_relations)}</div><div class="stat-label">关系</div></div>\n'

html += '''  </div>
</div>
<div class="container">
  <div class="card">
    <div class="card-header">📊 全书知识图谱（章-节 层次结构 + 关键实体关系）</div>
    <div class="card-body">
      <div class="legend">
        <div class="legend-item"><span class="legend-color" style="background:#4A90D9;"></span> 章</div>
        <div class="legend-item"><span class="legend-color" style="background:#E8F4FD;border:1px solid #50C878;"></span> 节</div>
        <div class="legend-item"><span class="legend-color" style="background:#FFF3E0;border:1px solid #FF8C42;"></span> KGGen实体</div>
        <div class="legend-item"><span style="border-top:2px dashed #999;width:30px;"></span> 实体关联</div>
        <div class="legend-item"><span class="legend-color" style="background:#FF8C42;height:4px;border-radius:2px;"></span> 章顺序</div>
      </div>
      <div class="mermaid">
'''

# 简化版 Mermaid（只显示主要结构，避免太大）
mmd_simple = ['flowchart TD']
mmd_simple.append('    classDef ch fill:#4A90D9,color:#fff,stroke:#2E5A8A,stroke-width:2px')
mmd_simple.append('    classDef sec fill:#E8F4FD,color:#333,stroke:#50C878,stroke-width:1px')
mmd_simple.append('    classDef entity fill:#FFF3E0,color:#E65100,stroke:#FF8C42,stroke-width:1px')

# 章
ch_nid_map = {}
for i, item in enumerate(toc):
    if item[0] == 0:
        nid = f'CH{i}'
        ch_nid_map[item[1]] = nid
        esc = item[1].replace('"', "'")
        mmd_simple.append(f'    {nid}["{esc}"]:::ch')

# 章间连接
ch_sorted_keys = sorted(ch_nid_map.keys(), key=lambda x: int(re.search(r'\\d+', x).group()) if re.search(r'\\d+', x) else 0)
for i in range(len(ch_sorted_keys) - 1):
    mmd_simple.append(f'    {ch_nid_map[ch_sorted_keys[i]]} ==> {ch_nid_map[ch_sorted_keys[i+1]]}')

# 部分实体（只取核心的）
core_entities = sorted(all_entities)[:12]
for ent in core_entities:
    nid = f'ENT_{hash(ent) % 10000}'
    esc = ent.replace('"', "'")
    mmd_simple.append(f'    {nid}["{esc}"]:::entity')
    # 连接到第一章节
    first_ch = ch_sorted_keys[0]
    mmd_simple.append(f'    {ch_nid_map[first_ch]} -.-> {nid}')

html += '\n'.join(mmd_simple)
html += '''
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-header">📋 全书目录结构（9章 104节）</div>
    <div class="card-body">
      <div class="structure">
'''

ch_colors = ['', 'ch-block-1', 'ch-block-2', 'ch-block-3', 'ch-block-4', 'ch-block-5', 'ch-block-6', 'ch-block-7', 'ch-block-8', 'ch-block-9']
for item in toc:
    if item[0] == 0:
        ch_num = int(re.search(r'\\d+', item[1]).group()) if re.search(r'\\d+', item[1]) else 1
        color_class = ch_colors[ch_num] if ch_num <= 9 else 'ch-block-1'
        html += f'<div class="ch-block {color_class}"><div class="ch-title">{item[1]}</div><ul class="sec-list">\n'
    elif item[0] == 1:
        ch_num = int(item[2])
        if ch_num <= 5 and item[1] in [r['title'] for r in {}]:
            # 有 KGGen 实体的节
            html += f'<li class="sec-item">{item[1]}</li>\n'
        else:
            html += f'<li class="sec-item">{item[1]}</li>\n'

html += '''
      </ul></div>
    </div>
  </div>
</div>

<div class="card">
  <div class="card-header">🔗 KGGen 提取的关系网络（前5章，''' + str(len(all_relations)) + '''条关系）</div>
  <div class="card-body">
    <div class="triples">
'''

for s, p, o in all_relations[:30]:
    html += f'      <div class="triple"><span class="triple-subject">{s}</span> <span class="triple-predicate">--[{p}]--></span> <span class="triple-object">{o}</span></div>\n'

html += '''
    </div>
  </div>
</div>

<div class="card">
  <div class="card-header">🏷️ 全部实体索引（''' + str(len(all_entities)) + '''个）</div>
  <div class="card-body">
    <div class="entity-tags">
'''

for e in sorted(all_entities):
    html += f'      <span class="entity-tag">{e}</span>\n'

html += '''
    </div>
  </div>
</div>
</div>

<script>
  mermaid.initialize({ startOnLoad: true, theme: 'default', flowchart: { useMaxWidth: true, htmlLabels: true, curve: 'basis' } });
</script>
</body>
</html>'''

with open(r'e:\nlp\ltp\kg_book_complete.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f"✅ 完整 HTML: kg_book_complete.html")

print(f"\n🎉 全部完成！")
print(f"  - kg_book_complete.md    Markdown 思维导图")
print(f"  - kg_book_complete.mmd   Mermaid 图谱代码")
print(f"  - kg_book_complete.html  交互式 HTML 可视化")