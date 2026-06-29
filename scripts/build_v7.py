"""
build_v7.py - 将 kg_entity_v7.json 转换为 kg_entity_v7.js
"""
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT = os.path.join(BASE_DIR, 'kg_entity_v7.json')
OUTPUT = os.path.join(BASE_DIR, 'kg_entity_v7.js')


def main():
    with open(INPUT, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 写入 JS 文件
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write('// Auto-generated from kg_entity_v7.json\n')
        f.write('window.__KG_DATA__ = ')
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write(';\n')

    print(f'[build_v7] 完成: {len(data)} 个实体 -> {OUTPUT}')


if __name__ == '__main__':
    main()