"""快速重新生成 HTML（跳过 LLM，使用已有 JSON）"""
import json, os

# 读取现有 JSON
d = json.load(open(r'e:\nlp\ltp\kg_entity_v6.json', encoding='utf-8'))

# 导入 HTML 模板生成函数
from build_v6 import generate_html

html = generate_html(d)
out_path = r'e:\nlp\ltp\kg_book_interactive_v6.html'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'→ {out_path}')
print(f'  实体: {len(d)}')
print(f'  HTML大小: {len(html)} 字节')