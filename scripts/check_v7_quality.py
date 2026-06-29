"""检查 V7 实体数据质量"""
import json

with open(r'e:\nlp\ltp\kg_entity_v7.json', 'r', encoding='utf-8') as f:
    entities = json.load(f)

# 统计
total = len(entities)
headings = sum(1 for e in entities.values() if e['is_heading'])
list_items = sum(1 for e in entities.values() if not e['is_heading'])
with_def = sum(1 for e in entities.values() if e['definition'])
with_para = sum(1 for e in entities.values() if e['paragraph'])
with_parent = sum(1 for e in entities.values() if e['parent'])
with_children = sum(1 for e in entities.values() if any(r['type'] == '子概念' for r in e['related_entities']))

print(f'总实体数: {total}')
print(f'  标题实体: {headings}')
print(f'  列表项实体: {list_items}')
print(f'  有定义: {with_def} ({with_def/total*100:.1f}%)')
print(f'  有段落: {with_para} ({with_para/total*100:.1f}%)')
print(f'  有父实体: {with_parent} ({with_parent/total*100:.1f}%)')
print(f'  有子实体: {with_children} ({with_children/total*100:.1f}%)')

# 深度分布
depth_dist = {}
for e in entities.values():
    depth_dist[e['depth']] = depth_dist.get(e['depth'], 0) + 1
print(f'  深度分布: {dict(sorted(depth_dist.items()))}')

# 检查几个关键实体的内容
for name in ['知识图谱', 'RDF', 'OWL', '知识表示', '知识图谱概述']:
    if name in entities:
        e = entities[name]
        def_preview = e['definition'][:80] if e['definition'] else '(无)'
        para_len = len(e['paragraph']) if e['paragraph'] else 0
        children = [r['name'] for r in e['related_entities'] if r['type'] == '子概念']
        print(f'\n"{name}":')
        print(f'  depth={e["depth"]}, parent="{e["parent"]}", ch_num={e["ch_num"]}')
        print(f'  definition: {def_preview}...')
        print(f'  paragraph: {para_len} chars')
        print(f'  children: {children[:5]}')

# 检查最大段落长度的实体
max_para = max(entities.items(), key=lambda x: len(x[1]['paragraph']))
print(f'\n最大段落实体: "{max_para[0]}" ({len(max_para[1]["paragraph"])} chars)')