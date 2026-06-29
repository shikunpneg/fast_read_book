"""KGGen 处理全书 80K 字符"""
import os, sys, time, json, urllib.request

os.environ['PATH'] = r'e:\ollama;' + os.environ.get('PATH', '')
os.environ['OLLAMA_MODELS'] = r'e:\ollama\models'

# 测试 Ollama 连通
req_data = json.dumps({"model": "qwen2.5:3b", "prompt": "连通测试", "stream": False}).encode()
req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=req_data, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=120)
result = json.loads(resp.read())
print(f"✅ Ollama 连通: {result.get('response','?')[:30]}")
sys.stdout.flush()

from kg_gen import KGGen

# 读取全文
text = open(r'e:\nlp\ltp\kg_book_ch1-2.txt', encoding='utf-8').read()
print(f"📖 输入: {len(text)} 字符")
sys.stdout.flush()

kg = KGGen(model='ollama_chat/qwen2.5:3b', temperature=0.0, api_base='http://127.0.0.1:11434')

start = time.time()
print("⏳ KGGen.generate() 处理中... (chunk_size=4000, 并行抽取)")
sys.stdout.flush()

graph = kg.generate(
    input_data=text,
    context='知识图谱书籍 第1-2章 知识图谱概述与基本概念',
    chunk_size=4000,
)

elapsed = time.time() - start
print(f"\n⏱️ 总耗时: {elapsed:.1f}s ({elapsed/60:.1f} 分钟)")
print(f"实体: {len(graph.entities)}")
print(f"关系类型: {len(graph.edges)}")
print(f"三元组: {len(graph.relations)}")
sys.stdout.flush()

# 保存完整结果
with open(r'e:\nlp\ltp\kg_book_full_kggen.txt', 'w', encoding='utf-8') as f:
    f.write(f"KGGen 全书结果 (chunk_size=4000, 耗时{elapsed:.1f}s)\n")
    f.write(f"实体 ({len(graph.entities)}):\n")
    for e in sorted(graph.entities):
        f.write(f"  - {e}\n")
    f.write(f"\n关系类型 ({len(graph.edges)}):\n")
    for e in sorted(graph.edges):
        f.write(f"  - {e}\n")
    f.write(f"\n三元组 ({len(graph.relations)}):\n")
    for s, p, o in graph.relations:
        f.write(f"  ({s}, {p}, {o})\n")

# 也导出三元组频率统计
rel_freq = {}
for s, p, o in graph.relations:
    key = (s, p, o)
    rel_freq[key] = rel_freq.get(key, 0) + 1

with open(r'e:\nlp\ltp\kg_book_full_kggen_stats.txt', 'w', encoding='utf-8') as f:
    f.write(f"KGGen 全书统计\n")
    f.write(f"实体数: {len(graph.entities)}\n")
    f.write(f"关系类型数: {len(graph.edges)}\n")
    f.write(f"三元组数: {len(graph.relations)}\n\n")
    
    # 实体频次
    ent_freq = {}
    for s, p, o in graph.relations:
        ent_freq[s] = ent_freq.get(s, 0) + 1
        ent_freq[o] = ent_freq.get(o, 0) + 1
    f.write("实体频次 (Top 50):\n")
    for e, cnt in sorted(ent_freq.items(), key=lambda x: -x[1])[:50]:
        f.write(f"  {e}: {cnt}\n")
    
    f.write(f"\n关系类型频次:\n")
    edge_freq = {}
    for s, p, o in graph.relations:
        edge_freq[p] = edge_freq.get(p, 0) + 1
    for e, cnt in sorted(edge_freq.items(), key=lambda x: -x[1]):
        f.write(f"  {e}: {cnt}\n")

print(f"\n✅ 结果:")
print(f"  - kg_book_full_kggen.txt (完整三元组)")
print(f"  - kg_book_full_kggen_stats.txt (统计分析)")