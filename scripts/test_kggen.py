"""KGGen 小样测试"""
import os
import sys
from kg_gen import KGGen

# 配置环境
os.environ['PATH'] = r'e:\ollama;' + os.environ.get('PATH', '')
os.environ['OLLAMA_MODELS'] = r'e:\ollama\models'

kg = KGGen(
    model='ollama_chat/qwen2.5:3b',
    temperature=0.0,
    api_base='http://localhost:11434',
)

# 小样测试
text = '知识图谱是一种用图结构来描述知识和关系的技术。实体是知识图谱中的基本单元，关系则描述了实体之间的语义联系。知识图谱广泛应用于搜索引擎和推荐系统。'

print("⏳ 正在调用 KGGen.generate()...")
sys.stdout.flush()
graph = kg.generate(input_data=text, context='知识图谱技术介绍')
sys.stdout.flush()

print(f'实体数: {len(graph.entities)}')
print(f'关系类型数: {len(graph.edges)}')
print(f'三元组数: {len(graph.relations)}')
print()
print('Entities:', graph.entities)
print('Edges:', graph.edges)
print('Relations:')
for s, p, o in graph.relations:
    print(f'  ({s}, {p}, {o})')

print("\n✅ 测试完成")