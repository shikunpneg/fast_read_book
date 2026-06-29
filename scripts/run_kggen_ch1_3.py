"""用 KGGen 提取第1-3章各节内容（每个节独立小 chunk）"""
import os, sys, time, re

os.environ['PATH'] = r'e:\ollama;' + os.environ.get('PATH', '')
os.environ['OLLAMA_MODELS'] = r'e:\ollama\models'

# 预热
import urllib.request, json
print("预热 Ollama...")
sys.stdout.flush()
data = json.dumps({"model": "qwen2.5:3b", "prompt": "预热", "stream": False}).encode()
req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=data,
                             headers={"Content-Type": "application/json"})
urllib.request.urlopen(req, timeout=120)
print("OK\n")
sys.stdout.flush()

from kg_gen import KGGen
kg = KGGen(model="ollama_chat/qwen2.5:3b", temperature=0.0, api_base="http://127.0.0.1:11434")

text = open(r'e:\nlp\ltp\kg_book_full.txt', encoding='utf-8').read()
lines = text.split('\n')

# 解析全书结构：提取所有章节标题及其行号
entries = []  # (line_no, title, is_chapter, ch_num)
for i, line in enumerate(lines):
    ls = line.strip()
    if not ls:
        continue
    m = re.match(r'^第([一二三四五六七八九十\d]+)章\s+(.+)$', ls)
    if m:
        entries.append((i, ls, True, m.group(1)))
    m = re.match(r'^(\d+)\.(\d+)\s+(.+)$', ls)
    if m:
        entries.append((i, ls, False, m.group(1)))

# 去重
seen_titles = set()
unique_entries = []
for e in entries:
    if e[1] not in seen_titles:
        seen_titles.add(e[1])
        unique_entries.append(e)

print(f"全书结构: {sum(1 for e in unique_entries if e[2])} 章 + {sum(1 for e in unique_entries if not e[2])} 节")
sys.stdout.flush()

# 取前20个小节（第1-2章的量）进行 KGGen 处理
sections_to_process = [e for e in unique_entries if not e[2]][:20]
print(f"将处理前 {len(sections_to_process)} 节\n")
sys.stdout.flush()

def get_section_content(entry, entries, lines):
    """提取节标题后的内容（到下一个标题为止）"""
    line_no = entry[0]
    next_line = None
    for e in entries:
        if e[0] > line_no and e[2] == entry[2] and e[0] - line_no < 200:
            next_line = e[0]
            break
    if next_line is None:
        raw = '\n'.join(lines[line_no+1:line_no+50])
    else:
        raw = '\n'.join(lines[line_no+1:next_line])
    # 去图/表题
    raw = re.sub(r'图\d+-\d+.*?\n', '', raw)
    raw = re.sub(r'表\d+-\d+.*?\n', '', raw)
    raw = raw.strip()
    # 限制长度
    if len(raw) > 800:
        raw = raw[:800]
    return raw

results = []
t0 = time.time()
for idx, entry in enumerate(sections_to_process):
    content = get_section_content(entry, unique_entries, lines)
    if len(content) < 30:
        print(f"  [{idx+1}/20] {entry[1][:25]}... 内容太短，跳过")
        sys.stdout.flush()
        continue
    
    print(f"  [{idx+1}/20] {entry[1][:25]}... ({len(content)}字符) ", end='')
    sys.stdout.flush()
    
    try:
        t1 = time.time()
        graph = kg.generate(
            input_data=content,
            context=f"知识图谱书籍 - {entry[1]}",
            chunk_size=2000,
        )
        elapsed = time.time() - t1
        ents = list(graph.entities)
        rels = list(graph.relations)
        print(f"E:{len(ents)} R:{len(rels)} {elapsed:.0f}s")
        sys.stdout.flush()
        results.append({
            'title': entry[1],
            'entities': ents,
            'relations': rels,
        })
    except Exception as e:
        print(f"ERR: {str(e)[:40]}")
        sys.stdout.flush()

total = time.time() - t0
print(f"\n总耗时: {total:.1f}s")

# 汇总
all_ents = set()
all_rels = []
for r in results:
    for e in r['entities']:
        all_ents.add(e)
    for s, p, o in r['relations']:
        all_rels.append((s, p, o))

print(f"总计: {len(all_ents)} 实体, {len(all_rels)} 三元组")

# 保存
with open(r'e:\nlp\ltp\kg_book_ch1-3_kggen.txt', 'w', encoding='utf-8') as f:
    f.write(f"KGGen 第1-3章处理结果 (耗时 {total:.1f}s)\n")
    f.write(f"总计: {len(all_ents)} 实体, {len(all_rels)} 三元组\n\n")
    for r in results:
        f.write(f"--- {r['title']} ---\n")
        f.write(f"  实体: {', '.join(r['entities'][:10])}\n")
        for s,p,o in r['relations'][:8]:
            f.write(f"  ({s}, {p}, {o})\n")
        if len(r['relations']) > 8: f.write(f"  ...共{len(r['relations'])}个\n")
        f.write("\n")
    
    f.write("\n=== 全部三元组 ===\n")
    for s,p,o in all_rels:
        f.write(f"({s}, {p}, {o})\n")

print(f"✅ 保存: kg_book_ch1-3_kggen.txt")