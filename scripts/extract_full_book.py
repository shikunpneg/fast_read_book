"""提取全书文本（所有章节）"""
import fitz  # PyMuPDF

pdf_path = r'e:\nlp\知识图谱 方法、实践与应用 [转换版] (王昊奋, 漆桂林, 陈华钧) (z-library.sk, 1lib.sk, z-lib.sk).pdf'
doc = fitz.open(pdf_path)
print(f"PDF 共 {len(doc)} 页")

# 提取全部页
all_text = []
for i, page in enumerate(doc):
    txt = page.get_text()
    all_text.append(txt)
    if (i + 1) % 20 == 0:
        print(f"  已提取 {i+1} 页...")

full_text = '\n'.join(all_text)
out_path = r'e:\nlp\ltp\kg_book_full.txt'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(full_text)

print(f"✅ 全书提取完成: {len(full_text)} 字符，保存到 {out_path}")