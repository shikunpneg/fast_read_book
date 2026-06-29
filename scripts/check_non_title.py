import json
d = json.load(open(r'e:\nlp\ltp\kg_entity_v5.json', encoding='utf-8'))
others = [(n,v) for n,v in d.items() if not v['is_section_title']]
others.sort(key=lambda x: -x[1]['freq'])
print(f'非标题实体: {len(others)} 个')
print()
for i,(n,v) in enumerate(others[:50]):
    print(f'{i+1:2d}. [{n}]  ch{v["ch_num"]}  freq={v["freq"]}  rels={len(v["related_entities"])}  def={v["definition"][:60]}...')