import json
d = json.load(open(r'e:\nlp\ltp\kg_entity_v6.json', encoding='utf-8'))

new_entities = ['知识表示', '国内外典型的知识图谱项目', '人工智能早期的知识表示方法', 
                '常见开放域知识图谱的知识表示方法', '知识挖掘', '推理概述',
                '语义搜索简介', '语义数据搜索', '知识问答系统', '知识图谱的价值',
                '互联网时代的语义网知识表示框架']

for e in new_entities:
    if e in d:
        info = d[e]
        print(f'{e}:')
        print(f'  定义: {str(info.get("definition",""))[:80]}')
        print(f'  段落: {str(info.get("paragraph",""))[:80]}')
        print(f'  摘要: {str(info.get("summary",""))[:80]}')
        print()
    else:
        print(f'{e}: 不存在')
        print()

# 统计无摘要实体
no_summary = [(n,v) for n,v in d.items() if not v.get('summary') or v['summary'] in ('', '(暂无理解)')]
print(f'=== 无摘要实体: {len(no_summary)} ===')
for n,v in no_summary[:10]:
    print(f'  {n}')