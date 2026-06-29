"""用 KGGen 按章处理（取每章前 5000 字符作为内容）"""
import os, sys, time, re, json, urllib.request

os.environ['PATH'] = r'e:\ollama;' + os.environ.get('PATH', '')
os.environ['OLLAMA_MODELS'] = r'e:\ollama\models'

# 预热
print("预热 Ollama...")
sys.stdout.flush()
data = json.dumps({"model": "qwen2.5:3b", "prompt": "预热", "stream": False}).encode()
req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=data,
                             headers={"Content-Type": "application/json"})
urllib.request.urlopen(req, timeout=120)
print("OK\n")
sys.stdout.flush()

with open(r'e:\nlp\ltp\kg_book_full.txt', encoding='utf-8') as f:
    text = f.read()

lines = text.split('\n')

# 找到每章的起止行号
chapters = []
for i, line in enumerate(lines):
    ls = line.strip()
    m = re.match(r'^第([一二三四五六七八九十\d]+)章\s+(.+)$', ls)
    if m:
        if chapters:
            chapters[-1]['end'] = i
        ch_title = f"第{m.group(1)}章 {m.group(2)}"
        chapters.append({'title': ch_title, 'start': i + 1, 'end': len(lines)})
if chapters:
    chapters[-1]['end'] = len(lines)

print(f"全书 {len(chapters)} 章\n")

# 去重（目录在书前和书内重复出现）
seen = set()
unique_chs = []
for ch in chapters:
    if ch['title'] not in seen:
        seen.add(ch['title'])
        unique_chs.append(ch)

print(f"去重后 {len(unique_chs)} 章:")
for ch in unique_chs:
    content = '\n'.join(lines[ch['start']:ch['end']])
    # 去表/图题
    content = re.sub(r'图\d+-\d+.*?\n', '', content)
    content = re.sub(r'表\d+-\d+.*?\n', '', content)
    # 去多余空行
    content = re.sub(r'\n{3,}', '\n\n', content)
    ch['content'] = content[:5000]
    print(f"  {ch['title']}: {len(ch['content'])} 字符")
print()

sys.stdout.flush()

from kg_gen import KGGen
kg = KGGen(model="ollama_chat/qwen2.5:3b", temperature=0.0, api_base="http://127.0.0.1:11434")

# 处理前 5 章
process_chs = unique_chs[:5]
results = []
t0 = time.time()

for idx, ch in enumerate(process_chs):
    print(f"[{idx+1}/{len(process_chs)}] {ch['title'][:20]}... ", end='')
    sys.stdout.flush()
    
    try:
        t1 = time.time()
        graph = kg.generate(
            input_data=ch['content'],
            context=f"知识图谱书籍 - {ch['title']}",
            chunk_size=2500,
        )
        elapsed = time.time() - t1
        ents = list(graph.entities)
        rels = list(graph.relations)
        print(f"E:{len(ents)} R:{len(rels)} {elapsed:.0f}s")
        sys.stdout.flush()
        results.append({
            'title': ch['title'],
            'entities': ents,
            'relations': rels,
        })
    except Exception as e:
        print(f"ERR: {str(e)[:50]}")
        sys.stdout.flush()
        results.append({'title': ch['title'], 'entities': [], 'relations': []})

total = time.time() - t0
print(f"\n总耗时: {total:.1f}s\n")

# 汇总
all_ents = set()
all_rels = []
for r in results:
    for e in r['entities']:
        all_ents.add(e)
    for s, p, o in r['relations']:
        all_rels.append((s, p, o))

print(f"总计: {len(all_ents)} 独立实体, {len(all_rels)} 三元组")

# 保存
with open(r'e:\nlp\ltp\kg_book_5ch_kggen.txt', 'w', encoding='utf-8') as f:
    f.write(f"KGGen 前5章处理结果 (耗时 {total:.1f}s)\n")
    f.write(f"总计: {len(all_ents)} 实体, {len(all_rels)} 三元组\n\n")
    for r in results:
        f.write(f"--- {r['title']} ---\n")
        f.write(f"  实体 ({len(r['entities'])}): {', '.join(r['entities'][:12])}\n")
        f.write(f"  关系:\n")
        for s, p, o in r['relations'][:10]:
            f.write(f"    ({s}, {p}, {o})\n")
        if len(r['relations']) > 10:
            f.write(f"    ...共{len(r['relations'])}个\n")
        f.write("\n")
    
    f.write("\n=== 全部实体 ===\n")
    for e in sorted(all_ents): f.write(f"  - {e}\n")
    f.write(f"\n=== 全部三元组 ===\n")
    for s,p,o in all_rels: f.write(f"  ({s}, {p}, {o})\n")

print(f"✅ 保存: kg_book_5ch_kggen.txt")