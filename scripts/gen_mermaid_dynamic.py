"""
《知识图谱 方法、实践与应用》Mermaid 图谱动态生成器

用法:
  python gen_mermaid_dynamic.py              # 生成全书图谱
  python gen_mermaid_dynamic.py 3            # 生成第3章子图
  python gen_mermaid_dynamic.py 1-5          # 生成第1~5章子图
  python gen_mermaid_dynamic.py 1 3 5        # 生成第1、3、5章子图
  python gen_mermaid_dynamic.py 3 --output ch3.mmd  # 指定输出文件
  python gen_mermaid_dynamic.py 1-3 --html    # 同时生成 HTML
"""
import re, sys, os, argparse
from collections import defaultdict

# ── 配置 ──────────────────────────────────────────────────
BOOK_TEXT = r'e:\nlp\ltp\kg_book_full.txt'
KGGEN_RESULT = r'e:\nlp\ltp\kg_book_5ch_kggen.txt'
DEFAULT_OUTPUT = r'e:\nlp\ltp\kg_book_dynamic.mmd'

# ── 颜色主题 ──────────────────────────────────────────────
CH_COLORS = [
    "#4A90D9",  # 第1章 蓝
    "#50C878",  # 第2章 绿
    "#FF8C42",  # 第3章 橙
    "#9B59B6",  # 第4章 紫
    "#E74C3C",  # 第5章 红
    "#1ABC9C",  # 第6章 青
    "#F39C12",  # 第7章 金
    "#3498DB",  # 第8章 亮蓝
    "#2ECC71",  # 第9章 翠绿
]
CH_STROKES = [
    "#2E5A8A", "#2E8B57", "#CC6B2E", "#6C3483", "#C0392B",
    "#148F77", "#D68910", "#2471A3", "#1E8449",
]

# ── 工具函数 ──────────────────────────────────────────────

def parse_toc(text):
    """从全书文本中解析去重的目录结构"""
    lines = text.split('\n')
    seen = set()
    toc = []
    for line in lines:
        ls = line.strip()
        if not ls:
            continue
        m = re.match(r'^第([一二三四五六七八九十\d]+)章\s+(.+)$', ls)
        if m:
            title = f"第{m.group(1)}章 {m.group(2)}"
            if title not in seen:
                seen.add(title)
                toc.append((0, title, m.group(1)))
            continue
        m = re.match(r'^(\d+)\.(\d+)\s+(.+)$', ls)
        if m:
            title = f"{m.group(1)}.{m.group(2)} {m.group(3)}"
            key = f"sec-{m.group(1)}.{m.group(2)}"
            if key not in seen and m.group(1).isdigit():
                seen.add(key)
                toc.append((1, title, m.group(1)))
    return toc


def parse_kggen(text):
    """解析 KGGen 结果，返回 (entities, relations, ch_entities)"""
    all_entities = set()
    all_relations = []
    ch_entities = {}
    current_ch = None
    in_entities = False
    in_relations = False

    for line in text.split('\n'):
        # 章标题
        m = re.match(r'---\s+(第\d+章\s+.+?)\s+---$', line)
        if m:
            current_ch = m.group(1).strip()
            ch_entities[current_ch] = set()
            continue
        # 实体行
        if line.strip().startswith('实体') and ': ' in line and current_ch:
            parts = line.strip().split(': ', 1)
            if len(parts) > 1:
                names = parts[1].split(', ')
                ch_entities[current_ch].update(n.strip() for n in names)
            continue
        # 汇总区
        if line.startswith('=== 全部实体 ==='):
            in_entities = True
            in_relations = False
            continue
        if line.startswith('=== 全部三元组 ==='):
            in_entities = False
            in_relations = True
            continue
        if in_entities:
            m = re.match(r'\s*-\s+(.+)$', line)
            if m:
                all_entities.add(m.group(1).strip())
        if in_relations:
            m = re.match(r'\s*\((.+),\s*(.+),\s*(.+)\)$', line)
            if m:
                all_relations.append((m.group(1).strip(), m.group(2).strip(), m.group(3).strip()))

    return all_entities, all_relations, ch_entities


def select_chapters(toc, chapter_nums):
    """
    从 toc 中筛选指定章节号的条目
    chapter_nums: list of int, e.g. [1, 3, 5]
    """
    if not chapter_nums:
        return toc  # 全部
    target = set(str(n) for n in chapter_nums)
    selected = []
    current_ch_num = None
    for item in toc:
        if item[0] == 0:  # chapter
            ch_num_str = re.search(r'\d+', item[1])
            ch_num = ch_num_str.group() if ch_num_str else ""
            if ch_num in target:
                current_ch_num = ch_num
                selected.append(item)
            else:
                current_ch_num = None
        elif item[0] == 1 and current_ch_num is not None:
            # section belonging to selected chapter
            sec_ch_num = item[2]
            if sec_ch_num == current_ch_num:
                selected.append(item)

    return selected


def generate_mermaid(toc, entities=None, relations=None, ch_entities=None, chapter_nums=None):
    """
    生成 Mermaid flowchart TD 代码
    - chapter_nums: None=全部, [1,3]=仅第1、3章
    返回 Mermaid 代码字符串
    """
    # 筛选
    if chapter_nums:
        filtered_toc = select_chapters(toc, chapter_nums)
    else:
        filtered_toc = toc

    if not filtered_toc:
        return "flowchart TD\n    A[\"指定章节无数据\"]"

    lines = []
    lines.append("flowchart TD")
    lines.append("")
    lines.append("    %% 样式定义")
    lines.append("    classDef ch fill:#4A90D9,color:#fff,stroke:#2E5A8A,stroke-width:2px")
    lines.append("    classDef sec fill:#E8F4FD,color:#333,stroke:#50C878,stroke-width:1px")
    lines.append("    classDef entity fill:#FFF3E0,color:#E65100,stroke:#FF8C42,stroke-width:1px")
    lines.append("    classDef edgeLabel font-size:11px,color:#666")
    lines.append("")

    # 收集各章名
    chapters = [item for item in filtered_toc if item[0] == 0]
    ch_names = [c[1] for c in chapters]

    if not ch_names:
        return "flowchart TD\n    A[\"未找到匹配的章节\"]"

    # ── 如果只选单章，用 subgraph ──
    single_chapter = len(ch_names) == 1

    if single_chapter:
        ch_name = ch_names[0]
        ch_label = ch_name.replace('"', "'")
        ch_num = re.search(r'\d+', ch_name).group() if re.search(r'\d+', ch_name) else "0"
        ch_idx = int(ch_num) - 1

        color = CH_COLORS[ch_idx] if ch_idx < len(CH_COLORS) else "#4A90D9"
        stroke = CH_STROKES[ch_idx] if ch_idx < len(CH_STROKES) else "#2E5A8A"

        # 子图中只包含该章内的节点
        lines.append(f'    subgraph {ch_name.replace(" ","_")}["📖 {ch_label}"]')
        lines.append(f"        direction TB")
        lines.append(f"        classDef sub_ch fill:{color},color:#fff,stroke:{stroke},stroke-width:2px")
        lines.append(f"        classDef sub_sec fill:#E8F4FD,color:#333,stroke:{stroke},stroke-width:1px")

        # 主章节点
        lines.append(f'        CH_{ch_num}["{ch_label}"]:::sub_ch')
        lines.append("")

        # 节节点
        sec_count = 0
        for item in filtered_toc:
            if item[0] == 1:
                nid = f"SEC_{ch_num}_{sec_count}"
                sec_count += 1
                label = item[1].replace('"', "'")
                lines.append(f'        {nid}["{label}"]:::sub_sec')
                lines.append(f'        CH_{ch_num} --> {nid}')

        lines.append("    end")
        lines.append("")

        # ── KGGen 实体 ──
        if entities and ch_entities and ch_name in ch_entities:
            ch_ents = ch_entities[ch_name]
            if ch_ents:
                lines.append("    %% 关键实体")
                entity_added = set()
                for ent in sorted(ch_ents):
                    if ent not in entity_added and len(ent) <= 20:
                        eid = f"ENT_{ch_num}_{len(entity_added)}"
                        entity_added.add(ent)
                        label = ent.replace('"', "'")
                        lines.append(f'    {eid}["{label}"]:::entity')
                        lines.append(f'    CH_{ch_num} -.-> {eid}')

                # 实体间的关系
                if relations:
                    for s, p, o in relations:
                        if s in ch_ents and o in ch_ents:
                            # 找对应的节点 ID
                            s_ents = sorted(ch_ents)
                            if s in s_ents and o in s_ents:
                                si = s_ents.index(s)
                                oi = s_ents.index(o)
                                p_esc = p.replace('"', "'")
                                lines.append(f'    ENT_{ch_num}_{si} -- "{p_esc}" --> ENT_{ch_num}_{oi}')

    else:
        # ── 多章：显示章节和章间链路 ──
        lines.append("    %% 章节点")
        ch_nodes = {}
        for i, ch_name in enumerate(ch_names):
            nid = f"CH_{i}"
            ch_nodes[ch_name] = nid
            label = ch_name.replace('"', "'")

            if entities and ch_entities:
                ch_idx = int(re.search(r'\d+', ch_name).group() if re.search(r'\d+', ch_name) else "0") - 1
                color = CH_COLORS[ch_idx] if ch_idx < len(CH_COLORS) else "#4A90D9"
                stroke = CH_STROKES[ch_idx] if ch_idx < len(CH_STROKES) else "#2E5A8A"

                # 获取该章实体数，动态调整颜色
                ent_count = len(ch_entities.get(ch_name, []))
                ent_suffix = f" (E:{ent_count})" if ent_count > 0 else ""
                label_rich = f"{label}{ent_suffix}"
                lines.append(f'    {nid}["{label_rich}"]:::ch')
            else:
                lines.append(f'    {nid}["{label}"]:::ch')

        lines.append("")
        lines.append("    %% 节节点及连接到章")
        ch_current = None
        ch_idx_for_sec = -1
        for item in filtered_toc:
            if item[0] == 0:
                ch_current = item[1]
                ch_idx_for_sec += 1
                continue
            if item[0] == 1 and ch_current:
                nid = f"SEC_{ch_idx_for_sec}_{hash(item[1]) % 10000}"
                label = item[1].replace('"', "'")
                parent_id = ch_nodes.get(ch_current)
                if parent_id:
                    lines.append(f'    {nid}["{label}"]:::sec')
                    lines.append(f'    {parent_id} --> {nid}')

        lines.append("")
        lines.append("    %% 章间顺序关系")
        ch_name_list = list(ch_nodes.keys())
        for i in range(len(ch_name_list) - 1):
            src = ch_nodes[ch_name_list[i]]
            dst = ch_nodes[ch_name_list[i + 1]]
            lines.append(f'    {src} ==> {dst}')

        # ── KGGen 实体 ──
        if entities and ch_entities:
            lines.append("")
            lines.append("    %% 关键实体关联")
            entity_added = set()
            for ch_name in ch_names:
                if ch_name not in ch_entities:
                    continue
                ch_ents = ch_entities[ch_name]
                parent_id = ch_nodes.get(ch_name)
                if not parent_id:
                    continue
                for ent in sorted(ch_ents):
                    if ent not in entity_added and len(ent) <= 20:
                        eid = f"ENT_{len(entity_added)}"
                        entity_added.add(ent)
                        label = ent.replace('"', "'")
                        lines.append(f'    {eid}["{label}"]:::entity')
                        lines.append(f'    {parent_id} -.-> {eid}')

    return '\n'.join(lines)


def generate_html(mermaid_code, chapter_nums=None):
    """将 Mermaid 代码包装为可独立运行的 HTML"""
    if chapter_nums:
        title_suffix = f"第{'、'.join(str(n) for n in chapter_nums)}章"
    else:
        title_suffix = "全书"

    # 计算统计
    ch_count = mermaid_code.count('["第') - mermaid_code.count('sub_ch')
    ent_count = mermaid_code.count(':::entity')

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>知识图谱 · {title_suffix}</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
  body {{ font-family: 'Microsoft YaHei', sans-serif; margin: 20px; background: #f0f2f5; }}
  .header {{ background: linear-gradient(135deg, #4A90D9 0%, #2E5A8A 100%); color:#fff; padding:20px; text-align:center; border-radius:12px; }}
  .header h1 {{ margin:0; font-size:22px; }}
  .header p {{ margin:5px 0 0; opacity:.8; font-size:13px; }}
  .container {{ max-width:1200px; margin:20px auto; background:#fff; padding:30px; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.08); }}
  .mermaid {{ text-align:center; overflow-x:auto; }}
  .legend {{ display:flex; gap:15px; justify-content:center; padding:10px 0; flex-wrap:wrap; }}
  .legend-item {{ display:flex; align-items:center; gap:5px; font-size:12px; }}
  .legend-color {{ width:14px; height:14px; border-radius:3px; display:inline-block; }}
</style>
</head>
<body>
<div class="header">
  <h1>📚 {{title_suffix}} · 知识图谱结构</h1>
  <p>{{ch_count}} 章 · {ent_count} 个实体</p>
</div>
<div class="container">
  <div class="legend">
    <div class="legend-item"><span class="legend-color" style="background:#4A90D9;"></span> 章</div>
    <div class="legend-item"><span class="legend-color" style="background:#E8F4FD;border:1px solid #50C878;"></span> 节</div>
    <div class="legend-item"><span class="legend-color" style="background:#FFF3E0;border:1px solid #FF8C42;"></span> 实体</div>
  </div>
  <div class="mermaid">
{mermaid_code}
  </div>
</div>
<script>
  mermaid.initialize({{ startOnLoad: true, theme: 'default', flowchart: {{ useMaxWidth: true, htmlLabels: true }} }});
</script>
</body>
</html>'''
    return html


# ── 主入口 ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="《知识图谱 方法、实践与应用》Mermaid 图谱动态生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python gen_mermaid_dynamic.py              → 全书图谱
  python gen_mermaid_dynamic.py 3            → 第3章子图
  python gen_mermaid_dynamic.py 1-5          → 第1~5章
  python gen_mermaid_dynamic.py 1 3 5        → 第1、3、5章
  python gen_mermaid_dynamic.py 3 -o ch3.mmd → 输出到文件
  python gen_mermaid_dynamic.py 1-3 --html   → 同时生成 HTML""",
    )
    parser.add_argument("chapters", nargs="*", help="章节号（1-9），支持 3、1-5、1 3 5 等格式")
    parser.add_argument("-o", "--output", help="输出文件路径（默认自动生成）")
    parser.add_argument("--html", action="store_true", help="同时生成 HTML 文件")
    args = parser.parse_args()

    # ── 解析章节参数 ──
    chapter_nums = set()
    for arg in args.chapters:
        if '-' in arg:
            parts = arg.split('-')
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                start, end = int(parts[0]), int(parts[1])
                chapter_nums.update(range(start, end + 1))
        elif arg.isdigit():
            chapter_nums.add(int(arg))

    # 校验范围
    if chapter_nums:
        invalid = [n for n in chapter_nums if n < 1 or n > 9]
        if invalid:
            print(f"⚠️ 无效章节号: {invalid}（有效范围 1-9）")
            sys.exit(1)
    chapter_nums = sorted(chapter_nums) if chapter_nums else None

    # ── 加载数据 ──
    with open(BOOK_TEXT, encoding='utf-8') as f:
        text = f.read()
    toc = parse_toc(text)

    entities, relations, ch_entities = set(), [], {}
    if os.path.exists(KGGEN_RESULT):
        with open(KGGEN_RESULT, encoding='utf-8') as f:
            kggen_text = f.read()
        entities, relations, ch_entities = parse_kggen(kggen_text)

    # ── 生成 Mermaid ──
    mmd = generate_mermaid(toc, entities, relations, ch_entities, chapter_nums)

    # ── 输出 ──
    if args.output:
        out_path = args.output
    elif chapter_nums and len(chapter_nums) == 1:
        out_path = rf'e:\nlp\ltp\kg_ch{chapter_nums[0]}.mmd'
    elif chapter_nums:
        label = '-'.join(str(n) for n in chapter_nums[:3])
        label += f'+{len(chapter_nums)-3}' if len(chapter_nums) > 3 else ''
        out_path = rf'e:\nlp\ltp\kg_ch{label}.mmd'
    else:
        out_path = rf'e:\nlp\ltp\kg_book_all.mmd'

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(mmd)
    print(f"✅ Mermaid 已保存: {out_path}")

    # 统计
    sec_count = mmd.count(':::sec')
    ent_count = mmd.count(':::entity')
    ch_label = f"第{'、'.join(str(n) for n in chapter_nums)}章" if chapter_nums else "全书"
    print(f"   图谱: {ch_label} | 章: {mmd.count('::ch')} | 节: {sec_count} | 实体: {ent_count}")
    print(f"   代码行数: {len(mmd.split(chr(10)))}")

    # ── HTML ──
    if args.html:
        html = generate_html(mmd, chapter_nums)
        html_path = out_path.replace('.mmd', '.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✅ HTML 已保存: {html_path}")

    # 打印预览
    print("\n── Mermaid 代码预览（前15行）──")
    for line in mmd.split('\n')[:15]:
        print(line)
    if len(mmd.split('\n')) > 15:
        print(f"... (共 {len(mmd.split(chr(10)))} 行)")


if __name__ == '__main__':
    main()