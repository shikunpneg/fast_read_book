import json
d = json.load(open(r'e:\nlp\ltp\kg_entity_v5.json', encoding='utf-8'))
print(f'总实体: {len(d)}')
print(f'标题实体: {sum(1 for v in d.values() if v["is_section_title"])}')
print()

# 按 freq 排序
sorted_items = sorted(d.items(), key=lambda x: -x[1]['freq'])
print('--- Top 60 实体（按频次） ---')
for i, (n, v) in enumerate(sorted_items[:60]):
    title_flag = '📌' if v['is_section_title'] else ' '
    print(f'{i+1:2d}. {title_flag} [{n}]  ch{v["ch_num"]}  freq={v["freq"]}  rels={len(v["related_entities"])}')

print()
# 检查"一阶谓词逻辑"
if '一阶谓词逻辑' in d:
    v = d['一阶谓词逻辑']
    print(f'✓ "一阶谓词逻辑" 存在: ch{v["ch_num"]} def={v["definition"][:80]}...')
else:
    print('✗ "一阶谓词逻辑" 不存在!')

if '语义网络' in d:
    v = d['语义网络']
    print(f'✓ "语义网络" 存在: ch{v["ch_num"]} def={v["definition"][:80]}...')
    
if '知识表示' in d:
    v = d['知识表示']
    print(f'✓ "知识表示" 存在: ch{v["ch_num"]} def={v["definition"][:80]}...')