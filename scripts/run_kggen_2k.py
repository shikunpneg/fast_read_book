"""KGGen 处理 2K 样本（快速测试）"""
import os, sys
from kg_gen import KGGen

os.environ['PATH'] = r'e:\ollama;' + os.environ.get('PATH', '')
os.environ['OLLAMA_MODELS'] = r'e:\ollama\models'

text = open(r'e:\nlp\ltp\kg_book_sample_2k.txt', encoding='utf-8').read()
print(f"📖 输入: {len(text)} 字符")
sys.stdout.flush()

kg = KGGen(model='ollama_chat/qwen2.5:3b', temperature=0.0, api_base='http://localhost:11434')

print("⏳ KGGen generate()...")
sys.stdout.flush()
graph = kg.generate(input_data=text, context='知识图谱概述')
sys.stdout.flush()

print(f"实体: {len(graph.entities)}")
print(f"关系: {len(graph.edges)}")  
print(f"三元组: {len(graph.relations)}")
for s, p, o in graph.relations:
    print(f"  ({s}, {p}, {o})")

# 保存
with open(r'e:\nlp\ltp\kg_book_sample_kggen_2k.txt', 'w', encoding='utf-8') as f:
    f.write(f"实体 ({len(graph.entities)}):\n")
    for e in sorted(graph.entities): f.write(f"  - {e}\n")
    f.write(f"\n关系 ({len(graph.edges)}):\n")
    for e in sorted(graph.edges): f.write(f"  - {e}\n")
    f.write(f"\n三元组 ({len(graph.relations)}):\n")
    for s, p, o in graph.relations: f.write(f"  ({s}, {p}, {o})\n")
print("✅ 保存到 kg_book_sample_kggen_2k.txt")