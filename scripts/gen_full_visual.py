"""生成全书知识图谱思维导图 + Mermaid + PyVis"""
import re

text = open(r'e:\nlp\ltp\kg_book_full.txt', encoding='utf-8').read()
lines = text.split('\n')

# 去重提取完整目录
seen = set()
toc = []  # list of (level, title)
for line in lines:
    line = line.strip()
    if not line:
        continue
    
    # 章标题
    m = re.match(r'^第([一二三四五六七八九十\d]+)章\s+(.+)$', line)
    if m:
        title = f"第{m.group(1)}章 {m.group(2)}"
        if title not in seen:
            seen.add(title)
            toc.append((0, title))
        continue
    
    # 节标题
    m = re.match(r'^(\d+)\.(\d+)\s+(.+)$', line)
    if m:
        title = f"{m.group(1)}.{m.group(2)} {m.group(3)}"
        key = f"sec-{m.group(1)}.{m.group(2)}"
        if key not in seen:
            seen.add(key)
            toc.append((1, title, m.group(1)))
        continue

# ===== 1. Markdown 思维导图 =====
def md_level(t, indent=4):
    return ' ' * indent * t

md = []
md.append("# 📚 知识图谱 方法、实践与应用\n")
md.append("## 全书知识框架（思维导图）\n")

for item in toc:
    if item[0] == 0:
        md.append(f"\n## 📖 {item[1]}\n")
    elif item[0] == 1:
        md.append(f"{md_level(1)}- **{item[1]}**\n")

with open(r'e:\nlp\ltp\kg_book_mindmap.md', 'w', encoding='utf-8') as f:
    f.writelines(md)
print(f"✅ 思维导图: kg_book_mindmap.md ({len(toc)} 条目)")

# ===== 2. Mermaid 图谱 =====
mmd = []
mmd.append("flowchart TD\n")
mmd.append("    %% 样式定义\n")
mmd.append("    classDef ch fill:#4A90D9,color:#fff,stroke:#2E5A8A,stroke-width:2px\n")
mmd.append("    classDef sec fill:#50C878,color:#fff,stroke:#2E8B57,stroke-width:1px\n")

# 每章节点
ch_nodes = {}
for item in toc:
    if item[0] == 0:
        nid = f"CH{toc.index(item)}"
        title_esc = item[1].replace('"', "'")
        mmd.append(f"    {nid}[\"{title_esc}\"]:::ch\n")
        ch_nodes[item[1]] = nid

# 节节点和连接
for item in toc:
    if item[0] == 1:
        ch_idx = int(item[2])  # chapter number
        ch_title_0 = ""
        for t in toc:
            if t[0] == 0 and t[1].startswith(f"第{item[2]}章"):
                ch_title_0 = t[1]
                break
        parent = ch_nodes.get(ch_title_0)
        if parent:
            nid = f"S{toc.index(item)}"
            title_esc = item[1].replace('"', "'")
            mmd.append(f"    {nid}[\"{title_esc}\"]:::sec\n")
            mmd.append(f"    {parent} --> {nid}\n")

# 章之间的逻辑连接（按顺序）
ch_ids = [v for k, v in ch_nodes.items()]
for i in range(len(ch_ids) - 1):
    mmd.append(f"    {ch_ids[i]} ==> {ch_ids[i+1]}\n")
    mmd.append(f"    linkStyle {i+1} stroke:#FF8C42,stroke-width:3px\n")

with open(r'e:\nlp\ltp\kg_book_full.mmd', 'w', encoding='utf-8') as f:
    f.writelines(mmd)
print(f"✅ Mermaid: kg_book_full.mmd ({len(ch_nodes)} 章)")

# ===== 3. PyVis HTML =====
from pyvis.network import Network
import webbrowser

net = Network(height="800px", width="100%", directed=True, font_color="#333333")
net.set_options("""
{
  "nodes": {
    "font": {"size": 14, "face": "Microsoft YaHei"},
    "shape": "dot",
    "size": 20
  },
  "edges": {
    "arrows": {"to": {"enabled": true, "scaleFactor": 0.5}},
    "font": {"size": 10, "face": "Microsoft YaHei"},
    "color": {"color": "#888", "hover": "#333"}
  },
  "physics": {
    "barnesHut": {
      "gravitationalConstant": -3000,
      "centralGravity": 0.3,
      "springLength": 200
    }
  }
}
""")

# 添加章节点
for item in toc:
    if item[0] == 0:
        title = item[1]
        net.add_node(title, label=title, color="#4A90D9", size=30, shape="box", font={"size": 16, "color": "white"})

# 添加节节点和边
for item in toc:
    if item[0] == 1:
        title = item[1]
        ch_idx = int(item[2])
        ch_title = ""
        for t in toc:
            if t[0] == 0 and t[1].startswith(f"第{item[2]}章"):
                ch_title = t[1]
                break
        if ch_title:
            net.add_node(title, label=title, color="#50C878", size=15)
            net.add_edge(ch_title, title, title="包含", color="#2E8B57")

# 章间顺序边
ch_list = [t[1] for t in toc if t[0] == 0]
for i in range(len(ch_list) - 1):
    net.add_edge(ch_list[i], ch_list[i+1], title="→ 下一章", color="#FF8C42", width=3)

html_path = r'e:\nlp\ltp\kg_book_full.html'
net.show(html_path)
print(f"✅ PyVis: kg_book_full.html")
print(f"   节点: {len(net.nodes)}, 边: {len(net.edges)}")