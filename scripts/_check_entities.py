import json
d = json.load(open(r'e:\nlp\ltp\kg_entity_v6.json', encoding='utf-8'))
special = []
for name in d:
    if any(c in name for c in '<>&"'):
        special.append(name)
print(f'Entities with special chars: {len(special)}')
for n in special[:20]:
    print(f'  [{n}]')