"""KGGen 处理 2K 样本 - 带超时和日志"""
import os, sys, signal, time
from kg_gen import KGGen

os.environ['PATH'] = r'e:\ollama;' + os.environ.get('PATH', '')
os.environ['OLLAMA_MODELS'] = r'e:\ollama\models'

text = open(r'e:\nlp\ltp\kg_book_sample_2k.txt', encoding='utf-8').read()
print(f"📖 输入: {len(text)} 字符")
print(f"内容前100字: {text[:100]}")
sys.stdout.flush()

# 测试 Ollama 直连
import urllib.request, json
req_data = json.dumps({"model": "qwen2.5:3b", "prompt": "测试连通性，请回复OK", "stream": False}).encode()
req = urllib.request.Request("http://localhost:11434/api/generate", data=req_data, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=30)
result = json.loads(resp.read())
print(f"✅ Ollama 连通测试: {result.get('response', 'NO RESPONSE')[:50]}")
sys.stdout.flush()

print("⏳ 初始化 KGGen...")
sys.stdout.flush()
start = time.time()

kg = KGGen(model='ollama_chat/qwen2.5:3b', temperature=0.0, api_base='http://localhost:11434')

print(f"⏳ KGGen.generate() 开始... (toolkit init: {time.time()-start:.1f}s)")
sys.stdout.flush()

# 限制每个LLM调用的最大时间
graph = kg.generate(input_data=text, context='知识图谱概述')

elapsed = time.time() - start
print(f"⏱️ 总耗时: {elapsed:.1f}s")
print(f"实体: {len(graph.entities)}")
print(f"关系: {len(graph.edges)}")
print(f"三元组: {len(graph.relations)}")
for s, p, o in graph.relations:
    print(f"  ({s}, {p}, {o})")
sys.stdout.flush()

with open(r'e:\nlp\ltp\kg_book_sample_kggen_2k.txt', 'w', encoding='utf-8') as f:
    f.write(f"KGGen 结果 (耗时 {elapsed:.1f}s)\n")
    f.write(f"实体 ({len(graph.entities)}):\n")
    for e in sorted(graph.entities): f.write(f"  - {e}\n")
    f.write(f"\n关系 ({len(graph.edges)}):\n")
    for e in sorted(graph.edges): f.write(f"  - {e}\n")
    f.write(f"\n三元组 ({len(graph.relations)}):\n")
    for s, p, o in graph.relations: f.write(f"  ({s}, {p}, {o})\n")
print(f"✅ 保存完成: kg_book_sample_kggen_2k.txt")