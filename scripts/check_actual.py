"""检查 JSON 和 HTML 中的实体数据是否一致"""
import json, os
from datetime import datetime

# 检查 JSON 文件
d = json.load(open(r'e:\nlp\ltp\kg_entity_v6.json', encoding='utf-8'))
print('JSON 文件: %d 实体' % len(d))

# 检查 HTML 中 DATA 对象
html = open(r'e:\nlp\ltp\kg_book_interactive_v6.html', encoding='utf-8').read()
start = html.find('const DATA = {')
end = html.find('};', start)
data_str = html[start+14:end+1]
entity_count = data_str.count('": {')
print('HTML 中 DATA 实体数: %d' % entity_count)

# 检查关键实体
for name in ['知识表示', '知识图谱', '知识图谱的价值', '知识图谱的发展历史',
             '知识图谱的技术流程', '知识问答系统', '知识挖掘']:
    in_json = name in d
    in_html = name in html
    print('  %s: JSON=%s, HTML=%s' % (name, 'Y' if in_json else 'N', 'Y' if in_html else 'N'))

# 检查修改时间
json_time = os.path.getmtime(r'e:\nlp\ltp\kg_entity_v6.json')
html_time = os.path.getmtime(r'e:\nlp\ltp\kg_book_interactive_v6.html')
print('JSON 修改: %s' % datetime.fromtimestamp(json_time))
print('HTML 修改: %s' % datetime.fromtimestamp(html_time))