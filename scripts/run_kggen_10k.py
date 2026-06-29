"""KGGen 处理 10K 字符样本（3 chunk × 2调用 = 6次LLM调用）"""
import os, sys, time, json, urllib.request

os.environ['PATH'] = r'e:\ollama;' + os.environ.get('PATH', '')
os.environ['OLLAMA_MODELS'] = r'e:\ollama\models'

# 连通测试
req_data = json.dumps({"model": "qwen2.5:3b", "prompt": "连通测试", "stream": False}).encode()
req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=req_data,
                             headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=120)
result = json.loads(resp.read())
resp_text = result.get("response", "?")
print(f"✅ Ollama: {resp_text[:30]}")
sys.stdout.flush()

from kg_gen import KGGen

text = open(r'e:\nlp\ltp\kg_book_sample_10k.txt', encoding='utf-8').read()
print(f"📖 输入: {len(text)} 字符")
sys.stdout.flush()

kg = KGGen(model="ollama_chat/qwen2.5:3b", temperature=0.0, api_base="http://127.0.0.1:11434")

start = time.time()
print("⏳ 开始处理 (chunk_size=4000, 3 chunks)...")
sys.stdout.flush()

graph = kg.generate(input_data=text, context="知识图谱书籍", chunk_size=4000)

elapsed = time.time() - start
print()
print(f"⏱️ 耗时: {elapsed:.1f}s ({elapsed/60:.1f} 分钟)")
print(f"实体: {len(graph.entities)}")
print(f"关系类型: {len(graph.edges)}")
print(f"三元组: {len(graph.relations)}")
sys.stdout.flush()

with open(r'e:\nlp\ltp\kg_book_10k_kggen.txt', 'w', encoding='utf-8') as f:
    f.write(f"KGGen 10K 结果 (chunk_size=4000, 耗时{elapsed:.1f}s)\n")
    f.write(f"实体 ({len(graph.entities)}):\n")
    for e in sorted(graph.entities):
        f.write(f"  - {e}\n")
    f.write(f"\n关系类型 ({len(graph.edges)}):\n")
    for e in sorted(graph.edges):
        f.write(f"  - {e}\n")
    f.write(f"\n三元组 ({len(graph.relations)}):\n")
    for s, p, o in graph.relations:
        f.write(f"  ({s}, {p}, {o})\n")

print(f"✅ 保存: kg_book_10k_kggen.txt")