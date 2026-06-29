"""检查提取结果"""
import json

with open(r'e:\nlp\ltp\kg_entity_definitions_v2.json', encoding='utf-8') as f:
    data = json.load(f)

print(f'共 {len(data)} 个实体定义\n')

# 按章节分组
chapters = {}
for name, info in data.items():
    ch = info.get('chapter', '未知')
    if ch not in chapters:
        chapters[ch] = []
    chapters[ch].append((name, info))

for ch_title in sorted(chapters.keys()):
    items = chapters[ch_title]
    print(f'\n{"="*50}')
    print(f'📖 {ch_title} ({len(items)} 个实体)')
    print(f'{"="*50}')
    for i, (name, info) in enumerate(items[:15]):
        defn = info['definition'][:100] if len(info['definition']) > 100 else info['definition']
        print(f'  {i+1}. [{info["category"]}] {name}')
        print(f'     定义: {defn}...' if len(info['definition']) > 100 else f'     定义: {defn}')
    if len(items) > 15:
        print(f'     ... 还有 {len(items)-15} 个')

# 统计类别分布
from collections import Counter
cats = Counter()
for info in data.values():
    cats[info['category']] += 1
print(f'\n📊 类别分布:')
for cat, count in cats.most_common():
    print(f'  {cat}: {count}')