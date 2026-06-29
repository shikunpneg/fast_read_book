import json
d = json.load(open(r'e:\nlp\ltp\kg_entity_v5_summarized.json', encoding='utf-8'))

# 检查关键实体
key_entities = ['一阶谓词逻辑', '语义网络', '知识图谱', '关系抽取', '实体抽取', '描述逻辑', '知识融合']
for name in key_entities:
    if name in d:
        v = d[name]
        print(f'\n=== {name} (ch{v["ch_num"]}) ===')
        print(f'  理解: {v.get("summary", "(无)")}')
        print(f'  定义: {v["definition"][:100]}...')
    else:
        print(f'\n=== {name} === 不存在')

# 找几个非标题实体的摘要
print('\n\n=== 非标题实体摘要示例 ===')
others = [(n,v) for n,v in d.items() if not v['is_section_title'] and v.get('summary')]
for n,v in others[:10]:
    print(f'\n  [{n}] ch{v["ch_num"]}')
    print(f'  理解: {v["summary"]}')

# 统计
has_summary = sum(1 for v in d.values() if v.get('summary'))
no_summary = [n for n,v in d.items() if not v.get('summary')]
print(f'\n\n总实体: {len(d)}, 有摘要: {has_summary}, 无摘要: {no_summary}')