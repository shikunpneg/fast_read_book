"""KGGen 快速测试 - 用大 chunk_size 减少调用次数"""
import os, sys, time, json, urllib.request

os.environ['PATH'] = r'e:\ollama;' + os.environ.get('PATH', '')
os.environ['OLLAMA_MODELS'] = r'e:\ollama\models'

# 先连通测试 - 用更长超时
req_data = json.dumps({"model": "qwen2.5:3b", "prompt": "连通测试", "stream": False}).encode()
req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=req_data, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=120)
result = json.loads(resp.read())
print(f"✅ Ollama: {result.get('response','?')[:30]}")
sys.stdout.flush()

from kg_gen import KGGen

text = open(r'e:\nlp\ltp\kg_book_sample_2k.txt', encoding='utf-8').read()
print(f"📖 输入: {len(text)} 字符")
sys.stdout.flush()

kg = KGGen(model='ollama_chat/qwen2.5:3b', temperature=0.0, api_base='http://127.0.0.1:11434')

start = time.time()
print("⏳ generate() 开始...")
sys.stdout.flush()

graph = kg.generate(
    input_data=text,
    context='知识图谱概述',
    chunk_size=2000,
)

elapsed = time.time() - start
print(f"\n⏱️ 总耗时: {elapsed:.1f}s")
print(f"实体: {len(graph.entities)}")
print(f"关系类型: {len(graph.edges)}")
print(f"三元组: {len(graph.relations)}")

for s, p, o in graph.relations:
    print(f"  ({s}, {p}, {o})")

with open(r'e:\nlp\ltp\kg_book_sample_kggen_2k.txt', 'w', encoding='utf-8') as f:
    f.write(f"KGGen 结果 (chunk_size=2000, 耗时{elapsed:.1f}s)\n")
    f.write(f"实体 ({len(graph.entities)}):\n")
    for e in sorted(graph.entities): f.write(f"  - {e}\n")
    f.write(f"\n关系类型 ({len(graph.edges)}):\n")
    for e in sorted(graph.edges): f.write(f"  - {e}\n")
    f.write(f"\n三元组 ({len(graph.relations)}):\n")
    for s, p, o in graph.relations: f.write(f"  ({s}, {p}, {o})\n")

print(f"\n✅ 保存: kg_book_sample_kggen_2k.txt")