"""验证 V3 增强数据"""
import os, json

enriched = r'e:\nlp\ltp\kg_entity_enriched.json'
relations = r'e:\nlp\ltp\kg_entity_relations.json'
html_v3 = r'e:\nlp\ltp\kg_book_interactive_v3.html'

print('=== 文件验证 ===')
for f in [enriched, relations, html_v3]:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f'OK {f} ({size:,} bytes)')
    else:
        print(f'MISSING {f} not found')

with open(enriched, encoding='utf-8') as f:
    data = json.load(f)

print(f'\n=== 数据统计 ===')
print(f'总实体数: {len(data)}')

has_paragraph = sum(1 for v in data.values() if v.get('definition_full'))
has_explanation = sum(1 for v in data.values() if v.get('explanation'))
has_relations = sum(1 for v in data.values() if v.get('related_entities'))

print(f'有原文段落的: {has_paragraph}')
print(f'有通俗解释的: {has_explanation}')
print(f'有关联关系的: {has_relations}')

print(f'\n=== 样本数据 (前5个) ===')
for i, (name, info) in enumerate(data.items()):
    if i >= 5: break
    print(f'\n--- {name} [{info["category"]}] ---')
    d = info['definition'][:80] if info['definition'] else '(无)'
    p = info['definition_full'][:80] if info['definition_full'] else '(无)'
    e = info['explanation'][:80] if info['explanation'] else '(无)'
    print(f'  定义: {d}')
    print(f'  段落: {p}')
    print(f'  解释: {e}')
    print(f'  关联: {len(info["related_entities"])} 条')
    for rel in info['related_entities'][:3]:
        print(f'    -> {rel["name"]} ({rel["type"]})')