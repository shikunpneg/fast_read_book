"""KGGen 处理书籍样本（~8000字符）"""
import os
import sys
import json
from kg_gen import KGGen

# 配置环境
os.environ['PATH'] = r'e:\ollama;' + os.environ.get('PATH', '')
os.environ['OLLAMA_MODELS'] = r'e:\ollama\models'

# 读取样本
with open(r'e:\nlp\ltp\kg_book_ch1-2_sample.txt', 'r', encoding='utf-8') as f:
    text = f.read()

print(f"📖 输入文本: {len(text)} 字符")
sys.stdout.flush()

kg = KGGen(
    model='ollama_chat/qwen2.5:3b',
    temperature=0.0,
    api_base='http://localhost:11434',
)

# 不加聚类，直接抽取原始三元组
print("⏳ 正在抽取（无聚类）...")
sys.stdout.flush()
graph_raw = kg.generate(input_data=text, context='知识图谱书籍 第1章 知识图谱概述', chunk_size=4000)
sys.stdout.flush()

print(f"  实体: {len(graph_raw.entities)}")
print(f"  关系类型: {len(graph_raw.edges)}")
print(f"  三元组: {len(graph_raw.relations)}")
sys.stdout.flush()

# 保存原始结果
with open(r'e:\nlp\ltp\kg_book_sample_kggen_raw.txt', 'w', encoding='utf-8') as f:
    f.write(f"实体 ({len(graph_raw.entities)}):\n")
    for e in sorted(graph_raw.entities):
        f.write(f"  - {e}\n")
    f.write(f"\n关系类型 ({len(graph_raw.edges)}):\n")
    for e in sorted(graph_raw.edges):
        f.write(f"  - {e}\n")
    f.write(f"\n三元组 ({len(graph_raw.relations)}):\n")
    for s, p, o in graph_raw.relations:
        f.write(f"  ({s}, {p}, {o})\n")

# 再做一次带聚类的
print("⏳ 正在抽取（带聚类）...")
sys.stdout.flush()
graph_clustered = kg.generate(input_data=text, context='知识图谱书籍 第1章 知识图谱概述', chunk_size=4000, cluster=True)
sys.stdout.flush()

print(f"  实体(聚类后): {len(graph_clustered.entities)}")
print(f"  关系类型(聚类后): {len(graph_clustered.edges)}")
print(f"  三元组(聚类后): {len(graph_clustered.relations)}")
sys.stdout.flush()

# 保存聚类结果
with open(r'e:\nlp\ltp\kg_book_sample_kggen_clustered.txt', 'w', encoding='utf-8') as f:
    f.write(f"实体 ({len(graph_clustered.entities)}):\n")
    for e in sorted(graph_clustered.entities):
        f.write(f"  - {e}\n")
    f.write(f"\n关系类型 ({len(graph_clustered.edges)}):\n")
    for e in sorted(graph_clustered.edges):
        f.write(f"  - {e}\n")
    f.write(f"\n三元组 ({len(graph_clustered.relations)}):\n")
    for s, p, o in graph_clustered.relations:
        f.write(f"  ({s}, {p}, {o})\n")
    if hasattr(graph_clustered, 'entity_clusters') and graph_clustered.entity_clusters:
        f.write(f"\n实体聚类:\n")
        for k, v in graph_clustered.entity_clusters.items():
            f.write(f"  {k} <- {v}\n")
    if hasattr(graph_clustered, 'edge_clusters') and graph_clustered.edge_clusters:
        f.write(f"\n关系聚类:\n")
        for k, v in graph_clustered.edge_clusters.items():
            f.write(f"  {k} <- {v}\n")

print("\n✅ 完成！结果已保存")
print("  raw: kg_book_sample_kggen_raw.txt")
print("  clustered: kg_book_sample_kggen_clustered.txt")