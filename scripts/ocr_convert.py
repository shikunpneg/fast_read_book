"""
一键 OCR 转换工具：将图像型 PDF 或图片文件转成文本/JSON
用法:
  python scripts/ocr_convert.py <file_path> [--out <output_dir>] [--lang ch_sim+en]

支持格式: .pdf (图像型) / .png / .jpg / .jpeg / .bmp / .tiff / .webp
"""
import os
import sys
import argparse

# 加入项目路径
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from kg_core.converters import ocr_pdf, extract_image, extract_any, extract_pdf


def main():
    parser = argparse.ArgumentParser(description='OCR 转换工具')
    parser.add_argument('input', help='输入文件路径（PDF/图片）')
    parser.add_argument('--out', default=None, help='输出目录（默认同输入目录）')
    parser.add_argument('--lang', default='ch_sim+en', help='OCR 语言（默认 ch_sim+en）')
    parser.add_argument('--dpi', type=int, default=200, help='PDF 转图片分辨率（默认 200）')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f'文件不存在: {args.input}')
        return 1

    ext = os.path.splitext(args.input)[1].lower()
    out_dir = args.out or os.path.dirname(args.input)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(args.input))[0]
    out_path = os.path.join(out_dir, base + '.txt')

    print(f'[OCR] 输入: {args.input}')
    print(f'[OCR] 输出: {out_path}')
    print(f'[OCR] 语言: {args.lang}')
    print()

    if ext == '.pdf':
        # 先尝试文本提取
        try:
            text = extract_pdf(args.input)
            print(f'[OCR] PDF 文本提取成功（{len(text)} 字符），无需 OCR')
        except Exception as e:
            print(f'[OCR] PDF 文本提取失败（{e}），切换 OCR 模式...')
            text = ocr_pdf(args.input, lang=args.lang, dpi=args.dpi)
    elif ext in ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp', '.gif'):
        text = extract_image(args.input, lang=args.lang)
    else:
        print(f'不支持的格式: {ext}')
        return 1

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f'[OCR] 完成! 输出 {len(text)} 字符到: {out_path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
