import json
d = json.load(open(r'e:\nlp\ltp\kg_entity_v5_refined.json', encoding='utf-8'))

key = ['一阶谓词逻辑','语义网络','关系抽取','实体抽取','描述逻辑','知识融合','属性图','全局本体','局部本体','知识图谱数据模型','知识表示']
for name in key:
    if name in d:
        v = d[name]
        print(f'\n=== {name} (ch{v["ch_num"]}) ===')
        print(f'  理解: {v.get("summary","(无)")[:120]}')
        txt = v['definition'][:200]
        print(f'  定义: {txt}')
    else:
        print(f'\n=== {name} === 不存在')