"""
LLM + NLP 混合知识点提取器
- LLM (Ollama Qwen2.5:3b): 逐章提取核心知识点及其定义
- NLP (TextRank/Jieba): 交叉验证和补充
"""
import re, json, os, requests
from collections import Counter

BOOK_TEXT = r'e:\nlp\ltp\kg_book_full.txt'
OUTPUT_DEFINITIONS = r'e:\nlp\ltp\kg_entity_definitions_v2.json'
OUTPUT_ENTITY_DB = r'e:\nlp\ltp\kg_entity_db_v2.py'

OLLAMA_URL = 'http://localhost:11434/api/generate'
OLLAMA_MODEL = 'qwen2.5:3b'

# ── 1. 全书章节分割 ──

def split_book_chapters(text):
    """按章节分割全书，返回 {章号: {title, text}}"""
    lines = text.split('\n')
    
    # 已知的正文各章起始行号（0-indexed）
    # 从之前分析得到：第1章 body 在 line 406, 第2章 body 在 line 1734, 等等
    # 正文格式为 "第X章 知识 图谱概述"（内容中有空格）
    chapter_line_starts = {}
    
    for i, line in enumerate(lines):
        raw = line.strip()
        # 正文格式: 第X章后有多个空格分隔的文字
        # 例如: "第1章 知识 图谱概述"
        m = re.match(r'^(第\d+)章\s+(\S.*)$', raw)
        if m:
            num_part = m.group(1)  # "第1"
            ch_num_str = re.search(r'\d+', num_part).group()
            ch_title = f"第{ch_num_str}章 {m.group(2)}"
            # 只记录第一个匹配到的（跳过TOC章节说明行）
            n = int(re.search(r'\d+', num_part).group())
            # TOC中的章标题后面跟的是"主要介绍""围绕"等字眼
            rest = m.group(2).replace(' ', '')
            # 正文内容中，章标题后通常直接跟"5.1"或段落文字（不是"主要介绍"等）
            # 但我们统一取第二次出现（第一次在TOC）
            if n not in chapter_line_starts:
                chapter_line_starts[n] = i
            else:
                # 第二次出现，覆盖（正文标记）
                chapter_line_starts[n] = i
    
    # 检查是否找到足够的章节
    if len(chapter_line_starts) < 9:
        # 备用：使用验证过的准确行号
        print("   使用准确行号定位...")
        # 通过全书扫描验证过的章起始位置（0-indexed）
        verified = {1: 405, 2: 1733, 3: 2742, 4: 3882, 5: 5031, 6: 8087, 7: 9422, 8: 10049, 9: 11291}
        for n, line_num in verified.items():
            if line_num < len(lines):
                chapter_line_starts[n] = line_num

    # 按章号排序
    chapters = {}
    sorted_nums = sorted(chapter_line_starts.keys())
    
    for idx, n in enumerate(sorted_nums):
        start = chapter_line_starts[n]
        if idx + 1 < len(sorted_nums):
            end = chapter_line_starts[sorted_nums[idx + 1]]
        else:
            end = len(lines)
        
        ch_text = '\n'.join(lines[start:end]).strip()
        title_line = lines[start].strip()
        
        chapters[n] = {
            'title': title_line,
            'text': ch_text,
        }
    
    return chapters


# ── 2. LLM 知识点提取 ──

def extract_knowledge_points_llm(chapter_text, chapter_num):
    """用 LLM 提取核心知识点"""
    
    # 如果文本太长，取前4000字 + 后2000字（保证覆盖开头结尾）
    max_chars = 5000
    if len(chapter_text) > max_chars:
        # 按段落切分，取开头和关键部分
        paras = [p.strip() for p in chapter_text.split('\n') if p.strip()]
        first_part = '\n'.join(paras[:30])[:3000]
        # 从中间和结尾取样
        mid_idx = len(paras) // 3
        mid_part = '\n'.join(paras[mid_idx:mid_idx+15])[:1500]
        end_idx = max(mid_idx + 15, len(paras) - 20)
        end_part = '\n'.join(paras[end_idx:])[:1500]
        sample = f"[章首]\n{first_part}\n\n[章中]\n{mid_part}\n\n[章尾]\n{end_part}"
    else:
        sample = chapter_text[:max_chars]

    prompt = f'''你是一个知识图谱领域的专家。下面是一本教材中第{chapter_num}章的文本片段。

请提取本章最重要的12-15个核心知识点（概念、方法、技术、工具等）。
每个知识点严格按以下格式输出（每行一个）：
**名称** | 类别 | 一句话定义

类别只能是: 概念/方法/工具/理论/技术/任务

文本如下：
{sample}'''

    try:
        r = requests.post(OLLAMA_URL, json={
            'model': OLLAMA_MODEL,
            'prompt': prompt,
            'stream': False,
            'temperature': 0.2,
            'num_predict': 2048,
        }, timeout=180)
        result = r.json().get('response', '')
        return result
    except Exception as e:
        print(f'   ⚠️ LLM调用失败: {e}')
        return ''


def parse_llm_result(llm_text):
    """解析 LLM 输出的知识点列表"""
    knowledge_points = []
    
    for line in llm_text.split('\n'):
        ls = line.strip()
        # 匹配 **名称** | 类别 | 定义 格式
        if ls.startswith('**') and '**' in ls and '|' in ls:
            parts = [p.strip() for p in ls.split('|')]
            if len(parts) >= 3:
                name = parts[0].replace('**', '').strip()
                category = parts[1].strip()
                definition = parts[2].strip()
                if name and len(name) >= 2:
                    knowledge_points.append({
                        'name': name,
                        'category': category,
                        'definition': definition,
                    })
        # 备用格式: - **名称** | 类别 | 定义
        elif ls.startswith('-') and '**' in ls and '|' in ls:
            parts = [p.strip() for p in ls.replace('- ', '', 1).split('|')]
            if len(parts) >= 3:
                name = parts[0].replace('**', '').strip()
                definition = parts[2].strip()
                category = parts[1].strip() if len(parts) >= 2 else '概念'
                if name and len(name) >= 2:
                    knowledge_points.append({
                        'name': name,
                        'category': category,
                        'definition': definition,
                    })
        # 数字序号格式: 1. **名称** | 类别 | 定义
        elif re.match(r'^\d+[\.\)]\s*\*\*', ls) and '|' in ls:
            parts = [p.strip() for p in re.sub(r'^\d+[\.\)]\s*', '', ls).split('|')]
            if len(parts) >= 3:
                name = parts[0].replace('**', '').strip()
                category = parts[1].strip()
                definition = parts[2].strip()
                if name and len(name) >= 2:
                    knowledge_points.append({
                        'name': name,
                        'category': category,
                        'definition': definition,
                    })
    
    return knowledge_points


# ── 3. NLP 关键短语提取（TextRank/TF-IDF 替代方案）──

try:
    import jieba.analyse
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False
    print("⚠️ jieba 未安装，NLP 增强功能受限")


def extract_keywords_nlp(chapter_text, top_k=30):
    """用 jieba TextRank + TF-IDF 提取关键词"""
    if not HAS_JIEBA or len(chapter_text) < 50:
        return []
    
    # TextRank
    keywords_tr = jieba.analyse.textrank(chapter_text, topK=top_k, withWeight=True)
    
    # TF-IDF
    keywords_tfidf = jieba.analyse.extract_tags(chapter_text, topK=top_k, withWeight=True)
    
    # 合并评分
    scores = Counter()
    for word, weight in keywords_tr:
        scores[word] += weight * 0.6
    for word, weight in keywords_tfidf:
        scores[word] += weight * 0.4
    
    # 过滤单字和停用词
    stop_words = {'的', '了', '是', '在', '和', '也', '就', '都', '而', '及', '与',
                  '着', '或', '一个', '没有', '我们', '可以', '进行', '通过', '使用',
                  '这个', '这些', '那个', '那些', '因此', '从而', '其中', '以及',
                  '被', '将', '为', '对', '等', '从', '以', '上', '下', '很'}
    
    result = []
    for word, score in scores.most_common(top_k):
        if len(word) >= 2 and word not in stop_words and not word.isdigit():
            result.append((word, round(score, 4)))
    
    return result


# ── 4. 定义段落匹配 ──

def find_definition_paragraph(text, entity_name):
    """从原文中找到实体的定义段落"""
    paras = [p.strip() for p in text.split('\n') if p.strip()]
    
    for para in paras:
        if entity_name not in para:
            continue
        # 优先匹配定义模式
        if re.search(rf'{re.escape(entity_name)}.{{0,10}}(是指|指的是|就是|定义为|表示|描述)', para[:200]):
            return para[:500]
    
    # 回退：包含实体的第一个段落
    for para in paras:
        if entity_name in para:
            return para[:400]
    
    return ''


def update_entity_db_with_llm_results(chapters, llm_kps, nlp_keywords):
    """合并 LLM + NLP 结果，生成最终的实体数据库"""
    entity_db = {}
    definitions = {}
    
    for ch_num, ch_data in chapters.items():
        ch_title = ch_data['title']
        ch_text = ch_data['text']
        
        # 清理标题
        clean_title = ch_title.replace(' ', '')
        # 找对应的中文章号
        chinese_nums = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九']
        ch_title_with_num = f"第{chinese_nums[ch_num]}章 {ch_title.replace(f'第{ch_num}章', '').strip()}"
        
        # LLM 提取的知识点
        llm_entities = []
        if ch_num in llm_kps:
            for kp in llm_kps[ch_num]:
                name = kp['name']
                llm_entities.append(name)
                # 保存定义
                definition = kp.get('definition', '')
                if definition and len(definition) > 5:
                    definitions[name] = {
                        'definition': definition,
                        'chapter': clean_title,
                        'category': kp.get('category', '概念'),
                    }
        
        # NLP 补充的关键词
        nlp_entities = []
        if ch_num in nlp_keywords:
            for word, score in nlp_keywords[ch_num]:
                if score > 0.01 and word not in llm_entities and len(word) >= 2:
                    nlp_entities.append(word)
        
        # 合并，LLM 结果优先
        all_entities = llm_entities + [e for e in nlp_entities if e not in llm_entities]
        all_entities = all_entities[:20]  # 最多20个
        
        if all_entities:
            entity_db[clean_title] = all_entities
            
            # 为 NLP 补充的实体也找定义
            for ent in nlp_entities:
                if ent not in definitions:
                    defn = find_definition_paragraph(ch_text, ent)
                    if defn:
                        definitions[ent] = {
                            'definition': defn,
                            'chapter': clean_title,
                            'category': '概念',
                        }
    
    return entity_db, definitions


# ── 主流程 ──

def main():
    print("=" * 60)
    print("📚 LLM + NLP 混合知识点提取")
    print("=" * 60)
    
    # 1. 加载全书
    print("\n📖 加载全书...")
    with open(BOOK_TEXT, encoding='utf-8') as f:
        text = f.read()
    
    # 2. 分割章节
    print("📑 分割章节...")
    chapters = split_book_chapters(text)
    print(f"   找到 {len(chapters)} 章")
    for n in sorted(chapters.keys()):
        print(f"   第{n}章: {chapters[n]['title'][:30]}... ({len(chapters[n]['text'])} 字符)")
    
    if len(chapters) < 9:
        print("⚠️ 章节分割不完整，使用备用方案")
        # 备用：手工构建章节
        return
    
    # 3. LLM 逐章提取
    print("\n🤖 LLM 知识点提取（Ollama Qwen2.5:3b）...")
    llm_kp_results = {}
    
    for ch_num in sorted(chapters.keys()):
        ch_data = chapters[ch_num]
        print(f"\n  第{ch_num}章: {ch_data['title']}")
        print(f"  文本长度: {len(ch_data['text'])} 字符")
        
        result = extract_knowledge_points_llm(ch_data['text'], ch_num)
        
        if result:
            kps = parse_llm_result(result)
            print(f"  LLM 提取到 {len(kps)} 个知识点")
            for kp in kps[:5]:
                print(f"    ✅ {kp['name']} ({kp['category']})")
            if len(kps) > 5:
                print(f"    ... 还有 {len(kps)-5} 个")
            llm_kp_results[ch_num] = kps
        else:
            print(f"  ⚠️ LLM 未返回有效结果")
            llm_kp_results[ch_num] = []
    
    # 4. NLP 交叉验证
    print("\n🔤 NLP 关键词提取（TextRank + TF-IDF）...")
    nlp_results = {}
    for ch_num in sorted(chapters.keys()):
        ch_data = chapters[ch_num]
        keywords = extract_keywords_nlp(ch_data['text'], top_k=30)
        nlp_results[ch_num] = keywords
        if keywords:
            top5 = [w for w, s in keywords[:5]]
            print(f"  第{ch_num}章: {', '.join(top5)}")
    
    # 5. 合并结果
    print("\n🔄 合并 LLM + NLP 结果...")
    entity_db, definitions = update_entity_db_with_llm_results(chapters, llm_kp_results, nlp_results)
    
    # 6. 保存
    print(f"\n💾 保存结果...")
    
    # 保存定义 JSON
    with open(OUTPUT_DEFINITIONS, 'w', encoding='utf-8') as f:
        json.dump(definitions, f, ensure_ascii=False, indent=2)
    print(f"   ✅ 定义文件: {OUTPUT_DEFINITIONS}")
    print(f"      共 {len(definitions)} 个实体定义")
    
    # 保存实体 DB（Python 文件）
    with open(OUTPUT_ENTITY_DB, 'w', encoding='utf-8') as f:
        f.write("# 自动生成的实体数据库（LLM + NLP 混合提取）\n")
        f.write("ENTITY_DB = {\n")
        for ch_title in sorted(entity_db.keys(), key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0):
            entities = entity_db[ch_title]
            f.write(f'    "{ch_title}": {json.dumps(entities, ensure_ascii=False)},\n')
        f.write("}\n")
    print(f"   ✅ 实体数据库: {OUTPUT_ENTITY_DB}")
    
    # 统计
    total_entities = sum(len(v) for v in entity_db.values())
    print(f"\n📊 最终统计:")
    print(f"   9 章全覆盖")
    print(f"   共 {total_entities} 个知识点")
    print(f"   其中 {len(definitions)} 个带有定义")
    
    for ch_title in sorted(entity_db.keys(), key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0):
        ents = entity_db[ch_title]
        with_def = sum(1 for e in ents if e in definitions)
        print(f"   {ch_title}: {len(ents)} 知识点 ({with_def} 带定义)")
    
    print("\n✅ 完成！")


if __name__ == '__main__':
    main()