"""用 KGGen 逐节处理"""
import os, sys, time, json, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

os.environ['PATH'] = r'e:\ollama;' + os.environ.get('PATH', '')
os.environ['OLLAMA_MODELS'] = r'e:\ollama\models'

# 重启时模型可能不在内存
print("预热 Ollama...")
sys.stdout.flush()
data = json.dumps({"model": "qwen2.5:3b", "prompt": "预热", "stream": False}).encode()
req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=data,
                             headers={"Content-Type": "application/json"})
urllib.request.urlopen(req, timeout=120)
print("OK")
sys.stdout.flush()

from kg_gen import KGGen

# 读取各节
sections = []
current = None
with open(r'e:\nlp\ltp\kg_book_sections.txt', encoding='utf-8') as f:
    for line in f:
        if line.startswith('=== '):
            if current:
                sections.append(current)
            m = line.strip().split(' === ')[0].replace('=== ', '')
            typ = 'chapter' if 'CHAPTER' in m else 'section'
            title = line.strip().split(' === ')[1]
            current = {'type': typ, 'title': title, 'content': ''}
        else:
            if current:
                current['content'] += line
# 最后一个
if current:
    sections.append(current)

# 过滤：跳过章节标题行（内容太短）
sections = [s for s in sections if len(s['content']) > 50]

print(f"共 {len(sections)} 节待处理")
sys.stdout.flush()

kg = KGGen(model="ollama_chat/qwen2.5:3b", temperature=0.0, api_base="http://127.0.0.1:11434")

def process_section(sec):
    """处理单个节"""
    tid = sec['title'][:20]
    try:
        start = time.time()
        graph = kg.generate(
            input_data=sec['content'],
            context=f"知识图谱书籍 - {sec['title']}",
            chunk_size=2000,
        )
        elapsed = time.time() - start
        triples = list(graph.relations)
        entities = list(graph.entities)
        return {
            'title': sec['title'],
            'type': sec['type'],
            'entities': entities,
            'relations': triples,
            'elapsed': elapsed,
        }
    except Exception as e:
        return {
            'title': sec['title'],
            'type': sec['type'],
            'entities': [],
            'relations': [],
            'error': str(e),
            'elapsed': time.time() - start,
        }

# 串行处理（避免 DSPy + Ollama 并行冲突）
all_results = []
t0 = time.time()
for i, sec in enumerate(sections):
    print(f"  [{i+1}/{len(sections)}] {sec['title'][:30]}...", end=' ')
    sys.stdout.flush()
    result = process_section(sec)
    all_results.append(result)
    status = f"E:{len(result['entities'])} R:{len(result['relations'])} {result.get('elapsed',0):.0f}s"
    if 'error' in result:
        status += f" ERR:{result['error'][:40]}"
    print(status)
    sys.stdout.flush()

total_time = time.time() - t0
print(f"\n总耗时: {total_time:.1f}s")

# 输出
all_entities = set()
all_relations = []
for r in all_results:
    for e in r['entities']:
        all_entities.add(e)
    for s, p, o in r['relations']:
        all_relations.append((s, p, o))

print(f"\n总实体: {len(all_entities)}")
print(f"总三元组: {len(all_relations)}")

# 保存
with open(r'e:\nlp\ltp\kg_book_sections_result.txt', 'w', encoding='utf-8') as f:
    f.write(f"KGGen 逐节处理结果 (总耗时 {total_time:.1f}s)\n")
    f.write(f"总实体: {len(all_entities)}, 总三元组: {len(all_relations)}\n\n")
    
    for r in all_results:
        f.write(f"--- {r['type']}: {r['title']} ---\n")
        f.write(f"  实体: {', '.join(r['entities'][:15])}")
        if len(r['entities']) > 15: f.write(f" ... 共{len(r['entities'])}个")
        f.write("\n")
        for s, p, o in r['relations'][:10]:
            f.write(f"  ({s}, {p}, {o})\n")
        if len(r['relations']) > 10: f.write(f"  ... 共{len(r['relations'])}个\n")
        f.write("\n")
    
    f.write("\n\n=== 汇总 ===\n")
    f.write(f"所有实体 ({len(all_entities)}):\n")
    for e in sorted(all_entities): f.write(f"  - {e}\n")
    f.write(f"\n所有三元组 ({len(all_relations)}):\n")
    for s,p,o in all_relations: f.write(f"  ({s}, {p}, {o})\n")

print(f"✅ 保存: kg_book_sections_result.txt")