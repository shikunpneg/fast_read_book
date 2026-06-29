"""Check V4 results"""
import json

with open(r'e:\nlp\ltp\kg_entity_v4.json', encoding='utf-8') as f:
    data = json.load(f)

names = list(data.keys())
print(f'共 {len(names)} 个实体')
print()

by_ch = {}
for n, d in data.items():
    ch = d['ch_num']
    by_ch.setdefault(ch, []).append(n)

for ch in sorted(by_ch.keys()):
    ents = by_ch[ch]
    print(f'第{ch}章 ({len(ents)}个):')
    for n in ents:
        d = data[n]
        wt = d['weight']
        rel = len(d['related_entities'])
        def_preview = d['definition'][:60].replace('\n', ' ')
        print(f'  [{wt:.3f}] {n} | 定义: {def_preview}...')
        if rel:
            related_names = [r['name'] for r in d['related_entities']]
            print(f'       关联: {", ".join(related_names[:5])}')
    print()

# Check for generic words that slipped through
print('=== 可能需要过滤的通用词 ===')
check_words = ['包含', '语言', '开放', '工具', '框架', '模式', '文本', '建立', '表达',
               '需要', '提高', '能力', '商品', '形成', '效率', '模式', '集成']
for w in check_words:
    if w in data:
        print(f'  {w} (第{data[w]["ch_num"]}章, 权重{data[w]["weight"]})')