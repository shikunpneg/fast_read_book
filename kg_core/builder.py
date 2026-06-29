"""
知识图谱构建器 - 核心引擎
将电子书文本转换为知识图谱实体/关系 JSON 数据
"""
import json
import re
import os
from collections import defaultdict
from .text_cleaner import split_chapters, extract_chapter_titles


# ============================================================
# 指示词匹配
# ============================================================
INDICATORS_ZH = [
    '是指', '指的是', '定义为', '即', '称为', '就是', '是',
    '表示', '描述', '简称',
]
INDICATORS_EN = [
    'is defined as', 'refers to', 'is', 'means', 'called', 'refers',
]


def get_indicator_score(sent):
    for score, ind in enumerate(reversed(INDICATORS_ZH)):
        if ind in sent:
            return (len(INDICATORS_ZH) - score, ind)
    for score, ind in enumerate(reversed(INDICATORS_EN)):
        if ind.lower() in sent.lower():
            return (len(INDICATORS_EN) - score, ind)
    return (0, None)


def split_sentences(text):
    sents = re.split(r'(?<=[。！？；\n])\s*', text)
    return [s.strip() for s in sents if len(s.strip()) > 5]


# ============================================================
# 定义提取
# ============================================================
def extract_definition(ch_text, entity, max_len=9999):
    """从章节文本中提取实体的定义句"""
    if entity not in ch_text:
        return ''
    sents = split_sentences(ch_text)
    first_pos = ch_text.find(entity)
    candidates = []
    for i, sent in enumerate(sents):
        if entity not in sent:
            continue
        sent_pos = ch_text.find(sent)
        if sent_pos < 0:
            continue
        distance = abs(sent_pos - first_pos)
        ind_score, indicator = get_indicator_score(sent)
        if ind_score > 0:
            total = ind_score * 500 - distance * 0.5
            candidates.append((total, i, sent, indicator))
    candidates.sort(key=lambda x: -x[0])
    if candidates:
        best_idx = candidates[0][1]
        best_sent = candidates[0][2]
        ctx_parts = []
        if best_idx > 0:
            ctx_parts.append(sents[best_idx - 1][-80:])
        ctx_parts.append(best_sent)
        if best_idx + 1 < len(sents):
            ctx_parts.append(sents[best_idx + 1][:200])
        ctx = ''.join(ctx_parts)
        ctx = re.sub(r'\n{3,}', '\n\n', ctx)
        ctx = re.sub(r'^(图\d+[-–—]\d+.*?[。；\n])', '', ctx)
        ctx = re.sub(r'^(表\d+[-–—]\d+.*?[。；\n])', '', ctx)
        ctx = re.sub(r'^\d+(\.\d+)+\s*\S{1,40}\n', '', ctx)
        return ctx[:max_len]
    # 降级：含"X是"
    for sent in sents:
        if entity in sent and entity + '是' in sent:
            return re.sub(r'\n{3,}', '\n\n', sent)[:max_len]
    for sent in sents:
        if entity in sent and 20 <= len(sent) <= 400:
            return re.sub(r'\n{3,}', '\n\n', sent)[:max_len]
    return ''


# ============================================================
# 段落提取
# ============================================================
def extract_paragraph(ch_text, entity, max_len=9999):
    """从章节文本中提取包含实体的段落"""
    if entity not in ch_text:
        return ''
    pos = ch_text.find(entity)
    before = ch_text[:pos]
    para_start = 0
    dnl = before.rfind('\n\n')
    if dnl >= 0:
        para_start = dnl + 2
    else:
        sec_match = list(re.finditer(r'\d+\.\d+\.\d+\s+\S', before))
        if sec_match:
            para_start = sec_match[-1].start()
    after = ch_text[pos:]
    para_end = len(ch_text)
    dnl = after.find('\n\n')
    if dnl >= 0 and dnl < 800:
        para_end = pos + dnl
    next_sec = re.search(r'\d+\.\d+\.\d+\s+\S', after)
    if next_sec and next_sec.start() < 800:
        para_end = min(para_end, pos + next_sec.start())
    paragraph = ch_text[para_start:para_end].strip()
    if len(paragraph) > max_len:
        start = max(0, pos - para_start - 200)
        end = min(len(paragraph), pos - para_start + 5000)
        paragraph = paragraph[start:end]
    paragraph = re.sub(r'\n{3,}', '\n\n', paragraph)
    return paragraph[:max_len]


# ============================================================
# 标题转实体名
# ============================================================
def title_to_entity(title_text):
    """将章节标题转为实体名"""
    if title_text.startswith('什么是'):
        return title_text[3:]
    if title_text.endswith('简介'):
        core = title_text[:-2]
        if core:
            return core
    return title_text


# ============================================================
# 关系构建
# ============================================================
def build_relations(data, chapters):
    """构建实体间关系

    为每个实体补充：
    - depth: 在章节树中的层级（章=0, 一级子标题=1, ...）
    - parent: 直接父级实体名（章→节→子节）
    - related_entities: 关联实体列表（type: 父章节/子概念/同章/定义共现）
    """
    # 1. 收集每章的实体，按标题层级排序
    ch_entities = defaultdict(list)
    for name, info in data.items():
        ch = info.get('ch_num', 1)
        # depth 默认 0（章），有 is_section_title 但不是最高层级的为 1
        if 'depth' not in info:
            info['depth'] = 0
        info.setdefault('parent', '')
        ch_entities[ch].append(name)

    # 2. 同一章节内：识别父子（章 vs 节 vs 子节）和兄弟（同章）
    added_edges = set()
    for ch_num, entities in ch_entities.items():
        # 按 is_section_title 优先级 + 名称长度 排序（章标题更长，更"上"）
        sorted_ents = sorted(entities, key=lambda n: (
            -int(data[n].get('is_section_title', False)),  # 是节标题的排前面
            -len(n),                                       # 长的更可能是父级
            n
        ))
        # 同一章节内，建立前后关系（前面的为父，后面的为子）
        for i in range(len(sorted_ents)):
            ei = sorted_ents[i]
            for j in range(i + 1, len(sorted_ents)):
                ej = sorted_ents[j]
                key = (ei, ej)
                if key in added_edges:
                    continue
                added_edges.add(key)

                # 检测包含关系：定义/段落中包含对方名字 → 包含概念
                def_a = data[ei].get('definition', '') or data[ei].get('paragraph', '')
                def_b = data[ej].get('definition', '') or data[ej].get('paragraph', '')
                if ej in def_a and ei not in def_b:
                    rel_type_i, rel_type_j = '子概念', '父章节'
                elif ei in def_b and ej not in def_a:
                    rel_type_i, rel_type_j = '父章节', '子概念'
                else:
                    rel_type_i, rel_type_j = '同章', '同章'

                data[ei]['related_entities'].append({
                    'name': ej, 'type': rel_type_i, 'strength': 0.7
                })
                data[ej]['related_entities'].append({
                    'name': ei, 'type': rel_type_j, 'strength': 0.7
                })

                # 设置 parent（最近的父级）
                if rel_type_i == '父章节' and not data[ej].get('parent'):
                    data[ej]['parent'] = ei
                if rel_type_j == '父章节' and not data[ei].get('parent'):
                    data[ei]['parent'] = ej

    # 3. 跨章节：定义/段落共现
    for i, (name, info) in enumerate(data.items()):
        def_text = (info.get('definition', '') or '') + (info.get('paragraph', '') or '')
        for j, (other, oinfo) in enumerate(data.items()):
            if name >= other:
                continue
            if other in def_text or name in oinfo.get('definition', '') or name in oinfo.get('paragraph', ''):
                key = (name, other)
                if key in added_edges:
                    continue
                added_edges.add(key)
                data[name]['related_entities'].append({
                    'name': other, 'type': '定义共现', 'strength': 0.6
                })
                data[other]['related_entities'].append({
                    'name': name, 'type': '定义共现', 'strength': 0.6
                })
    return len(added_edges)


# ============================================================
# KnowledgeGraphBuilder 主类
# ============================================================
class KnowledgeGraphBuilder:
    """知识图谱构建器

    用法:
        builder = KnowledgeGraphBuilder("book.txt")
        builder.set_model("qwen2.5:3b")
        data = builder.build(enable_summary=False)
        builder.save_json("kg_entity.json")
        builder.save_js("kg_entity.js")
    """

    def __init__(self, book_path: str, model_name: str = "qwen2.5:3b"):
        self.book_path = book_path
        self.model_name = model_name
        self.data = {}
        self.chapters = {}
        self.full_text = ""
        self._stats = {}

    def read_text_file(self, filepath: str) -> str:
        """读取文本文件，自动检测编码（UTF-8 → GBK → GB2312 → latin-1）"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin-1']
        for enc in encodings:
            try:
                with open(filepath, encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
        # 最后兜底：忽略错误
        with open(filepath, encoding='utf-8', errors='replace') as f:
            return f.read()

    def extract_pdf(self, filepath: str) -> str:
        """从 PDF 文件中提取文本（含 OCR 回退）"""
        from .converters import extract_pdf as _extract_pdf
        return _extract_pdf(filepath)

    def extract_epub(self, filepath: str) -> str:
        """从 EPUB 文件中提取文本"""
        from .converters import extract_epub as _extract_epub
        return _extract_epub(filepath)

    def load_book(self):
        """加载书籍文本并分割章节。自动识别 PDF/EPUB/DOCX/PPTX/XLSX/HTML/图片等格式"""
        from .converters import extract_any
        ext = os.path.splitext(self.book_path)[1].lower()

        # DOCX/PPTX/XLSX/HTML/图片 用统一调度（支持 OCR 回退）
        if ext in ('.docx', '.pptx', '.xlsx', '.html', '.htm', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp'):
            self.full_text = extract_any(self.book_path)
        elif ext == '.pdf':
            # 优先文本提取，失败/空时自动 OCR 回退
            self.full_text = extract_any(self.book_path)
        elif ext == '.epub':
            self.full_text = self.extract_epub(self.book_path)
        else:
            # TXT / MD / 其他 - 自动检测编码
            self.full_text = self.read_text_file(self.book_path)

        if not self.full_text or not self.full_text.strip():
            raise RuntimeError("文件内容为空，无法构建知识图谱")

        self.chapters = split_chapters(self.full_text)
        return self

    def load_existing_data(self, json_path: str = None):
        """加载已有的实体数据（用于增量更新）"""
        if json_path and os.path.exists(json_path):
            encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030']
            for enc in encodings:
                try:
                    with open(json_path, encoding=enc) as f:
                        self.data = json.load(f)
                    break
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
            else:
                with open(json_path, encoding='utf-8', errors='replace') as f:
                    self.data = json.load(f)
        else:
            self.data = {}
        return self

    def extract_entities(self, existing_data_path: str = None):
        """提取实体：章节标题 + 参考文献 + 合并已有数据"""
        if self.data:
            existing = set(self.data.keys())
        else:
            existing = set()

        # 1. 章节标题
        section_titles = extract_chapter_titles(self.full_text, self.chapters)
        new_count = 0

        for title_text, ch_num in section_titles.items():
            entity_name = title_to_entity(title_text)
            if entity_name in existing:
                continue
            self.data[entity_name] = {
                'ch_num': ch_num,
                'weight': 0.5,
                'definition': '',
                'paragraph': '',
                'summary': '',
                'is_section_title': True,
                'related_entities': []
            }
            existing.add(entity_name)
            new_count += 1

        # 2. 参考文献条目（识别"参考文献"小节后的编号条目）
        ref_count = self._extract_references(existing)
        new_count += ref_count

        self._stats['new_entities'] = new_count
        self._stats['total_entities'] = len(self.data)
        return self

    def _extract_references(self, existing: set) -> int:
        """提取参考文献条目作为实体。返回新增数量。"""
        import re
        ref_section_idx = -1
        lines = self.full_text.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if re.search(r'参考文献|References|Bibliography|引文|引用文献', stripped):
                # 排除"本章参考文献"等正文中的引用，而要找独立的"参考文献"小节
                if len(stripped) < 30:
                    ref_section_idx = i
                    break

        if ref_section_idx < 0:
            return 0

        added = 0
        i = ref_section_idx + 1
        current_ch = self._find_chapter_at(lines, ref_section_idx)
        n = 0
        while i < len(lines):
            line = lines[i].strip()
            # 跳过空行
            if not line:
                i += 1
                continue
            # 遇到下一个标题（##/### 或 第X章）停止
            if re.match(r'^(第[一二三四五六七八九十\d]+章|#{1,4} )', line):
                break
            # 识别参考文献条目：以 [数字] 或 数字. 开头的非空行
            m = re.match(r'^\[?(\d+)\]?[\.\s]+(.+)$', line)
            if m and len(line) > 30:  # 排除短行
                ref_num = m.group(1)
                ref_content = m.group(2).strip()
                # 提取前几个作者作为 entity name（避免太长）
                first_author = ref_content.split(',')[0].split('.')[0].strip()
                if not first_author or len(first_author) < 2:
                    # 用内容前 40 字符作为名字
                    first_author = ref_content[:40].strip()
                entity_name = f"[{ref_num}] {first_author}"
                if entity_name in existing:
                    i += 1
                    continue
                # 限制总数
                n += 1
                if n > 200:
                    break
                self.data[entity_name] = {
                    'ch_num': current_ch,
                    'weight': 0.3,
                    'definition': ref_content[:200],
                    'paragraph': ref_content,
                    'summary': '',
                    'is_reference': True,
                    'related_entities': []
                }
                existing.add(entity_name)
                added += 1
            i += 1
        return added

    def _find_chapter_at(self, lines, idx):
        """找到第 idx 行所在的最接近的章节号"""
        import re
        for i in range(idx, -1, -1):
            m = re.match(r'^第([一二三四五六七八九十\d]+)章', lines[i].strip())
            if m:
                cn = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
                      '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}.get(m.group(1))
                if cn is None:
                    try:
                        cn = int(m.group(1))
                    except ValueError:
                        cn = None
                if cn is not None:
                    return cn
        return 1

    def extract_definitions_and_paragraphs(self):
        """为所有实体提取定义和段落"""
        def_stats = {'found': 0, 'empty': 0, 'improved': 0}

        for i, (name, info) in enumerate(self.data.items()):
            ch_num = info.get('ch_num', 1)
            ch_text = self.chapters.get(ch_num, self.full_text)

            old_def = info.get('definition', '')
            new_def = extract_definition(ch_text, name)
            new_para = extract_paragraph(ch_text, name)

            if new_def and len(new_def) > 20:
                if not old_def or old_def == '(暂无定义)' or len(new_def) > len(old_def) * 0.5:
                    self.data[name]['definition'] = new_def
                    def_stats['improved'] += 1
                def_stats['found'] += 1
            elif old_def:
                def_stats['found'] += 1
            else:
                def_stats['empty'] += 1

            if new_para and len(new_para) > 30:
                if not info.get('paragraph') or info.get('paragraph') == '(暂无段落)' or len(new_para) > len(info.get('paragraph', '')):
                    self.data[name]['paragraph'] = new_para

        self._stats['definitions'] = def_stats
        return self

    def build_relations(self):
        """构建实体间关系"""
        rel_count = build_relations(self.data, self.chapters)
        self._stats['new_relations'] = rel_count
        total_rels = sum(len(v.get('related_entities', [])) for v in self.data.values())
        self._stats['total_relations'] = total_rels
        return self

    def build(self, enable_summary: bool = False, existing_data_path: str = None) -> dict:
        """执行完整构建流程"""
        self.load_book()
        self.load_existing_data(existing_data_path)
        self.extract_entities(existing_data_path)
        self.extract_definitions_and_paragraphs()
        self.build_relations()

        if enable_summary:
            from .summarizer import SummaryGenerator
            gen = SummaryGenerator(self.data, self.model_name)
            gen.generate()

        return self.data

    def save_json(self, output_path: str):
        """保存为 JSON 文件"""
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        return self

    def save_js(self, output_path: str, var_name: str = '__KG_DATA__'):
        """保存为 JS 文件（可直接被前端引用）"""
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f'// Auto-generated by kg_core\n')
            f.write(f'window.{var_name} = ')
            json.dump(self.data, f, ensure_ascii=False, indent=2)
            f.write(';\n')
        return self

    def save_md(self, output_path: str, book_name: str = ''):
        """保存原文为 Markdown 文件（按章节组织，参考文献小节格式化为列表）"""
        import re
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            if book_name:
                f.write(f'# {book_name}\n\n')
            if self.chapters:
                for ch_num, ch_text in self.chapters.items():
                    f.write(f'\n## 第 {ch_num} 章\n\n')
                    # 处理参考文献小节
                    ch_text = self._format_reference_section(ch_text)
                    f.write(ch_text)
                    f.write('\n\n')
            else:
                text = self._format_reference_section(self.full_text)
                f.write(text)
        return self

    def _format_reference_section(self, text: str) -> str:
        """将参考文献小节格式化为 markdown 列表
        输入: "参考文献\\n[1] xxx\\nGoogle）, 2012.\\n[2] ..."
        输出: "参考文献\\n- [1] xxx Google）, 2012.\\n- [2] ..."
        """
        import re
        # 找参考文献小节起点
        m = re.search(r'^(.*?参考文献\s*$|.*?References\s*$|.*?Bibliography\s*$)',
                      text, re.MULTILINE)
        if not m:
            return text

        # 确保参考文献标题后立即换行（在 m.end() 处插入换行）
        head = text[:m.end()].rstrip('\n') + '\n'
        rest = text[m.end():].lstrip('\n') + '\n'  # 也确保后续以换行结尾以便正则匹配下一章
        # 找下一个章节或文末
        nxt = re.search(r'\n(?=第[一二三四五六七八九十\d]+章|\#{1,4}\s)', rest)
        ref_block = rest[:nxt.start()] if nxt else rest

        # 在 ref_block 内合并 [n] 编号条目（PDF 换行问题）
        # 规则：[n] 开头 → 一直加到下一个 [n+1] 或 ref_block 结束
        # 先按 [n] 拆
        chunks = re.split(r'(?=\[\d+\])', ref_block)
        merged = []
        for chunk in chunks:
            if not chunk.strip():
                continue
            # 合并多行
            lines = [ln.strip() for ln in chunk.split('\n') if ln.strip()]
            if not lines:
                continue
            # 首行以 [n] 开头
            if re.match(r'^\[\d+\]', lines[0]):
                full = ' '.join(lines)
                merged.append(f'- {full}')
            else:
                # 不是 ref 条目（如说明文字），保留
                for ln in lines:
                    merged.append(ln)

        new_ref_block = '\n'.join(merged)
        if nxt:
            return head + new_ref_block + '\n' + rest[nxt.start():]
        return head + new_ref_block

    def get_stats(self) -> dict:
        """获取构建统计信息"""
        total = len(self.data)
        summaries = sum(1 for v in self.data.values() if v.get('summary') and v['summary'] not in ('', '(暂无理解)'))
        defs = sum(1 for v in self.data.values() if v.get('definition') and v['definition'] not in ('', '(暂无定义)'))
        paras = sum(1 for v in self.data.values() if v.get('paragraph') and v['paragraph'] not in ('', '(暂无段落)'))
        total_rels = sum(len(v.get('related_entities', [])) for v in self.data.values())
        return {
            'total_entities': total,
            'total_relations': total_rels,
            'with_summary': summaries,
            'with_definition': defs,
            'with_paragraph': paras,
            **self._stats
        }