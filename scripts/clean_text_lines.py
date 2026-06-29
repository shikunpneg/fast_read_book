"""
clean_text_lines.py - 自动合并 PDF/EPUB 提取文本中的错误断行

规则:
  1. 如果一行不以句号、问号、感叹号、冒号结尾，且下一行不是空行、不是章节标题、
     不是列表项，则合并这两行（去掉换行符）。
  2. 不修改标题、列表项（1. 2. 3.）、表格。
  3. 输出清洗后的新文本文件。

用法:
  python clean_text_lines.py [输入路径] [输出路径]
  默认: 输入 kg_book_full.txt, 输出 kg_book_clean.txt
"""

import re
import sys
import os


def clean_text_lines(input_path: str, output_path: str = None) -> str:
    """
    清洗文本中的错误断行，返回输出路径。

    Args:
        input_path: 原始文本文件路径
        output_path: 输出路径，默认在同目录生成 *_clean.txt

    Returns:
        输出文件的绝对路径
    """
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_clean{ext}"

    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    cleaned = []
    i = 0
    total = len(lines)

    # 章节标题模式
    chapter_pattern = re.compile(
        r'^第\s*[一二三四五六七八九十\d]+\s*章'
        r'|^\d+(?:\.\d+)*\s+[^\d]'  # 如 "1.1 知识图谱概述"
        r'|^第\s*[一二三四五六七八九十\d]+\s*节'
    )

    # 列表项模式
    list_pattern = re.compile(
        r'^[\s]*[-•●·]\s'           # - xxx 或 ● xxx
        r'|^[\s]*\d+[\.\、\)）]\s'   # 1. xxx 或 1) xxx
        r'|^[\s]*[（(]\d+[）)]\s*'   # （1）xxx
        r'|^[\s]*[①②③④⑤⑥⑦⑧⑨⑩]'   # ① xxx
    )

    # 表格模式（简单检测：包含 | 且非代码块）
    table_pattern = re.compile(r'\|.*\|')

    # 行尾结束标点（这些标点结尾的行视为完整行）
    end_punctuation = set('。？！：；」』）)')

    while i < total:
        line = lines[i]
        stripped = line.rstrip('\n\r')

        # 空行直接保留
        if not stripped.strip():
            cleaned.append(line)
            i += 1
            continue

        # 检查是否为章节标题、列表项、表格 → 不合并，保留原样
        if (chapter_pattern.match(stripped.strip())
                or list_pattern.match(stripped.strip())
                or table_pattern.search(stripped)):
            cleaned.append(line)
            i += 1
            continue

        # 检查当前行是否以结束标点结尾
        last_char = stripped.strip()[-1] if stripped.strip() else ''
        if last_char in end_punctuation:
            # 以结束标点结尾，不合并
            cleaned.append(line)
            i += 1
            continue

        # 当前行不以结束标点结尾 → 尝试与下一行合并
        if i + 1 < total:
            next_line = lines[i + 1]
            next_stripped = next_line.rstrip('\n\r')

            # 下一行为空 → 不合并
            if not next_stripped.strip():
                cleaned.append(line)
                i += 1
                continue

            # 下一行是章节标题 → 不合并
            if chapter_pattern.match(next_stripped.strip()):
                cleaned.append(line)
                i += 1
                continue

            # 下一行是列表项 → 不合并
            if list_pattern.match(next_stripped.strip()):
                cleaned.append(line)
                i += 1
                continue

            # 合并：去掉当前行的换行符，拼接下一行内容
            merged = stripped.rstrip() + next_stripped.lstrip()
            # 递归处理：将合并后的行作为当前行，继续判断是否还需要合并
            lines[i] = merged + '\n'
            lines.pop(i + 1)
            total -= 1
            # 不增加 i，用合并后的行继续判断
            continue

        cleaned.append(line)
        i += 1

    # 写入输出文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(cleaned)

    print(f"[clean_text_lines] 清洗完成")
    print(f"  输入: {input_path} ({len(open(input_path, 'r', encoding='utf-8').readlines())} 行)")
    print(f"  输出: {output_path} ({len(cleaned)} 行)")

    return output_path


def main():
    # 默认路径
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_input = os.path.join(base_dir, 'kg_book_full.txt')
    default_output = os.path.join(base_dir, 'kg_book_clean.txt')

    input_path = sys.argv[1] if len(sys.argv) > 1 else default_input
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(input_path):
        print(f"[错误] 输入文件不存在: {input_path}")
        sys.exit(1)

    result = clean_text_lines(input_path, output_path)
    print(f"[完成] 清洗后文件: {result}")


if __name__ == '__main__':
    main()