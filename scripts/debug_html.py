import json, re

# 检查 JSON 数据中实体名是否包含特殊字符
d = json.load(open(r'e:\nlp\ltp\kg_entity_v6.json', encoding='utf-8'))
for name in d:
    if "'" in name or '"' in name:
        print(f'含引号实体: {repr(name)}')

# 检查 HTML 中相关代码
html = open(r'e:\nlp\ltp\kg_book_interactive_v6.html', encoding='utf-8').read()

# 找 showEntity 的保存按钮 onclick
# 用正则找
onclicks = re.findall(r'onclick="saveNote\([^)]+\)"', html)
for oc in onclicks[:5]:
    print(f'saveNote onclick: {oc}')

# 找 related-item onclick
rel_onclicks = re.findall(r'onclick="showEntity\([^)]+\)"', html)
for oc in rel_onclicks[:5]:
    print(f'related-item onclick: {oc}')

# 检查 item.onclick 的生成
entity_item_onclick = re.findall(r'item\.onclick\s*=.*', html)
for oc in entity_item_onclick[:3]:
    print(f'item.onclick: {oc}')

# 检查是否有 xss 问题（实体名被直接插入 HTML 而未转义）
# 找出 showEntity 函数中定义部分是否使用了 .textContent 或 innerHTML
uses_innerhtml = 'innerHTML' in html
uses_textcontent = '.textContent' in html
print(f'\n使用 innerHTML: {uses_innerhtml}')
print(f'使用 textContent: {uses_textcontent}')

# 检查 detail-panel display 默认值
if 'detail-panel' in html:
    # 找 CSS 中 detail-panel 的 display
    css_panel = re.findall(r'#detail-panel[^}]+', html)
    for c in css_panel:
        if 'display' in c:
            print(f'detail-panel CSS: {c[:80]}')

# 检查 JavaScript 语法 - 快速找常见错误
# 找不匹配的括号
open_braces = html.count('{')
close_braces = html.count('}')
open_parens = html.count('(')
close_parens = html.count(')')
print(f'\n括号匹配: {{={open_braces}, }}={close_braces}, dif={open_braces-close_braces}')
print(f'圆括号: (={open_parens}, )={close_parens}, dif={open_parens-close_parens}')