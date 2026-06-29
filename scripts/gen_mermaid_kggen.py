"""从 KGGen 结果生成 Mermaid 流程图"""
import re

# KGGen 结果中的三元组
triples = [
    ("王昊奋", "是", "乐言科技"),
    ("Semantic Web", "知识表示与推理在Web中的应用", ""),
    ("谷歌知识图谱", "目标成为世界最大开放知识库", "Wikidata"),
    ("知识图谱", "是一种用图模型来描述知识和建模世界万物之间的关联关系的技术方法", ""),
    ("Semantic Web", "最初理想是把基于文本链接的万维网转化成基于实体链接的语义网", ""),
    ("知识图谱", "可以看作是Semantic Web的一种简化后的商业实现", "谷歌知识图谱"),
    ("漆桂林", "是", "东南大学"),
    ("谷歌知识图谱", "作为Freebase的数据基础之一", "IBM Waston"),
    ("王鑫", "是", "天津大学"),
    ("知识图谱", "节点可以是抽象的概念", ""),
    ("RDF", "是一种面向 Web 设计实现的标准化的知识表示语言", "OWL"),
    ("知识图谱", "节点可以是实体", ""),
    ("知识图谱", "由节点和边组成", ""),
    ("Semantic Web", "是传统人工智能与Web融合发展的结果", ""),
    ("知识图谱", "边可以是实体的属性", ""),
    ("知识图谱", "边可以是实体之间的关系", ""),
    ("谷歌知识图谱", "于2012年正式推出了称为知识图谱的搜索引擎服务", ""),
    ("陈华钧", "是", "浙江大学"),
    ("Semantic Web", "早期理念来自", "知识图谱"),
    ("Tim Berners-Lee", "提出构建一个全球化的以'链接'为中心的信息系统", "Linked Information System"),
]

# Mermaid 需要转义的特殊字符
def mermaid_id(text):
    """生成安全的 Mermaid 节点 ID"""
    # 只保留字母数字
    safe = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]', '', text)
    return safe[:20]

def mermaid_label(text, max_len=30):
    """截断长标签"""
    if len(text) <= max_len:
        return text
    return text[:max_len-2] + "…"

# 构建 Mermaid 代码
lines = []
lines.append("flowchart TD")
lines.append("")

# 节点定义
all_entities = set()
for s, p, o in triples:
    if s: all_entities.add(s)
    if o: all_entities.add(o)

# 给主要节点加样式分组
style_map = {
    "知识图谱": "fill:#4A90D9,color:#fff,stroke:#2E5A8A",
    "Semantic Web": "fill:#50C878,color:#fff,stroke:#2E8B57",
    "谷歌知识图谱": "fill:#FF8C42,color:#fff,stroke:#CC6B2E",
    "RDF": "fill:#9B59B6,color:#fff,stroke:#6C3483",
}

for i, e in enumerate(sorted(all_entities, key=lambda x: -len(x))):
    nid = f"N{i}"
    safe_id = mermaid_id(e)
    label = mermaid_label(e)
    if e in style_map:
        lines.append(f'    {nid}["<b>{label}</b>"]:::{safe_id}')
    else:
        lines.append(f'    {nid}["{label}"]')

lines.append("")

# 关系连线（过滤掉无 object 的三元组）
edge_idx = 0
for s, p, o in triples:
    if not o:
        continue  # 跳过无 object 的关系
    
    # 找节点索引
    def find_id(name):
        for i, e in enumerate(sorted(all_entities, key=lambda x: -len(x))):
            if e == name:
                return f"N{i}"
        return None
    
    sid = find_id(s)
    oid = find_id(o)
    if sid and oid:
        p_label = mermaid_label(p)
        lines.append(f'    {sid} -- "{p_label}" --> {oid}')
        edge_idx += 1

lines.append("")
# 样式定义
for e, style in style_map.items():
    safe_id = mermaid_id(e)
    lines.append(f'    classDef {safe_id} {style}')

lines.append("")
lines.append(f"%% 共 {len(all_entities)} 个实体, {edge_idx} 条关系")

mermaid_code = "\n".join(lines)

# 保存
with open(r'e:\nlp\ltp\kg_book_sample_kggen.mmd', 'w', encoding='utf-8') as f:
    f.write(mermaid_code)

print("✅ Mermaid 已保存: kg_book_sample_kggen.mmd")
print()
print(mermaid_code)