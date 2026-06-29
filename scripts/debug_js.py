"""从 HTML 中提取 JS 代码并检查语法错误"""
import re

html = open(r'e:\nlp\ltp\kg_book_interactive_v6.html', encoding='utf-8').read()

# 提取 <script> 标签内容
script_match = re.search(r'<script>\s*(.*?)\s*</script>', html, re.DOTALL)
if script_match:
    js_code = script_match.group(1)
    
    # 检查关键函数是否存在
    funcs = ['function saveNote', 'function deleteNote', 'function showEntity', 
             'function showChapter', 'function buildGraph', 'function highlightNode',
             'function closeDetail', 'function loadNotes']
    for f in funcs:
        if f in js_code:
            print(f'  ✓ {f}')
        else:
            print(f'  ✗ {f} 不存在!')
    
    # 检查 item.onclick 是否被正确设置
    # 找 showEntity 函数中是否包含了笔记相关的 HTML
    showEntity_match = re.search(r'function showEntity\(name\)\s*\{(.*?)(?=\nfunction|\n//)', js_code, re.DOTALL)
    if showEntity_match:
        func_body = showEntity_match.group(1)
        has_note = 'note-text' in func_body and 'saveNote' in func_body
        has_related = 'related-item' in func_body and 'showEntity' in func_body
        print(f'\nshowEntity:')
        print(f'  含笔记相关 HTML: {has_note}')
        print(f'  含关联实体可点击: {has_related}')
    
    # 检查 saveNote 函数
    saveNote_match = re.search(r'function saveNote\(name\)\s*\{(.*?)(?=\nfunction)', js_code, re.DOTALL)
    if saveNote_match:
        body = saveNote_match.group(1)
        has_localStorage = 'localStorage' in body
        has_note_text = "document.getElementById('note-text')" in body
        print(f'\nsaveNote:')
        print(f'  含 localStorage: {has_localStorage}')
        print(f'  获取 note-text: {has_note_text}')
    else:
        print(f'\nsaveNote: 函数不存在!')
else:
    print('未找到 <script> 标签')