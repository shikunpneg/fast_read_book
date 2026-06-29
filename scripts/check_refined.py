import json
d = json.load(open(r'e:\nlp\ltp\kg_entity_v5_refined.json', encoding='utf-8'))

key = ['一阶谓词逻辑','语义网络','关系抽取','实体抽取','描述逻辑','知识融合','属性图','全局本体','局部本体','知识图谱数据模型']
for name in key:
    if name in d:
        v = d[name]
        print(f'\n=== {name} (ch{v["ch_num"]}) ===')
        print(f'  理解: {v.get("summary","(无)")[:120]}')
        print(f'  定义: {v["definition"][:150]}...')
        print(f'  段落: {v["paragraph"][:100]}...')
    else:
        print(f'\n=== {name} === 不存在')

# 统计段落改进
paras = [(n,v['paragraph']) for n,v in d.items() if v.get('paragraph') and v['paragraph'] != '(暂无段落)']
print(f'\n\n=== 段落质量 ===')
print(f'有段落实体: {len(paras)}/{len(d)}')
avg_len = sum(len(p) for _,p in paras) / len(paras) if paras else 0
print(f'平均段落长度: {avg_len:.0f} 字')
para_empty = [(n,v) for n,v in d.items() if v.get('paragraph','') == '(暂无段落)' or not v.get('paragraph')]
print(f'段落为空: {[n for n,v in para_empty]}')