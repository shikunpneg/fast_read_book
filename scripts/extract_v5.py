"""
V5 混合管线：LTP + 结构解析 + LLM 验证 + 统计
===============================================
策略：
  1. 解析章节标题（最重要知识点）
  2. LTP 依存句法分析 → 提取技术术语 + 关系三元组
  3. 统计（每章词频）排序
  4. LLM 验证实体质量 + 过滤噪音
"""
import sys, os, re, json, time
from collections import Counter, defaultdict
import requests

# ============================================================
# 0. 配置
# ============================================================
BOOK_FILE = r'e:\nlp\ltp\kg_book_full.txt'
OUTPUT_JSON = r'e:\nlp\ltp\kg_entity_v5.json'
OUTPUT_HTML = r'e:\nlp\ltp\kg_book_interactive_v5.html'

OLLAMA_URL = 'http://localhost:11434/api/generate'
LLM_MODEL = 'qwen2.5:3b'

MAX_ENTITIES_PER_CHAPTER = 20  # 每章保留实体数

# 停用词
STOP_WORDS = {
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都',
    '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着',
    '没有', '看', '好', '自己', '这', '他', '她', '它', '那', '些',
    '之', '与', '但', '而', '或', '被', '把', '对', '等', '从',
    '以', '为', '所', '如', '将', '能', '可', '已', '还', '又', '并',
    '其', '个', '种', '些', '某', '各', '每', '哪', '谁', '怎', '么',
    '什么', '如何', '为什么', '因为', '所以', '如果', '虽然', '但是',
    '而且', '然后', '并且', '或者', '不过', '关于',
    '当前', '目前', '通常', '一般', '基本', '主要', '重要',
    '不同', '相同', '一定', '其他', '各种', '相关', '实际',
    '这个', '这些', '那个', '那些', '每个', '某个', '各个',
    '其中', '之间', '之内', '之中',
    '任何', '所有', '全部', '整个', '一些', '多个', '多种',
    '若干', '大量', '少量', '部分',
    '方面', '角度', '层面', '维度',
}

# 通用词（明显不是技术概念的词）
GENERIC_WORDS = {
    '工作','方法','问题','技术','方面','方式','过程','时候','地方',
    '情况','部分','水平','当前','目前','通常','一般','基本','主要',
    '重要','进行','使用','利用','根据','按照','经过','然后','之后',
    '同时','从而','因此','由于','关于','对于','其中','之间',
    '应该','可以','需要','能够','必须','可能','一定','不能',
    '实现','完成','达到','存在','产生','形成','成为','作为',
    '表示','描述','包括','提供','采用','提出','建立','开发',
    '系统','应用','数据','信息','模型','领域','研究','学习',
    '开发','支持','计算','分析','处理','流程','阶段','步骤',
    '符号','集合','元素','对象','类型','方式','形式','数量',
    '规模','结构','特征','属性','功能','作用','结果','解释',
    '定义','概念','基础','目标','任务','能力','性能','效率',
    '质量','成本','需求','资源','来源','来源','来源',
    '操作','操作','运行','更新','转换','映射','导入','导出',
    '检查','判断','选择','评估','评价','验证','测试','测量',
    '搜索','查找','匹配','对比','比较','区别','联系','关联',
    '连接','链接','关系','排序','过滤','限制','控制','管理',
    '组织','协调','整合','集成','协同','合作','分面',
}


# ============================================================
# 1. 读取全书
# ============================================================
print("=" * 60)
print("V5 混合管线：结构 + LTP + LLM + 统计")
print("=" * 60)

print("\n[1/6] 读取全书文本...")
with open(BOOK_FILE, 'r', encoding='utf-8') as f:
    lines = f.readlines()
full_text = ''.join(lines)
print(f"  共 {len(lines)} 行, {len(full_text)} 字符")


# ============================================================
# 2. 解析章节标题
# ============================================================
print("\n[2/6] 解析章节标题...")

def get_chapter_range():
    """找每章起止行号"""
    ch_ranges = {}
    current_ch = None
    start = None
    CH_PATTERN = re.compile(r'第([一二三四五六七八九十\d+])章')
    
    for i, line in enumerate(lines):
        line = line.strip()
        # 匹配 "第X章"
        m = CH_PATTERN.match(line.lstrip('\ufeff'))
        if m:
            ch_num_str = m.group(1)
            ch_map = {'一':1,'二':2,'三':3,'四':4,'五':5,
                      '六':6,'七':7,'八':8,'九':9,'十':10}
            cn = ch_map.get(ch_num_str) or int(ch_num_str)
            if current_ch is not None:
                ch_ranges[current_ch] = (start, i - 1)
            current_ch = cn
            start = i
    if current_ch is not None:
        ch_ranges[current_ch] = (start, len(lines) - 1)
    return ch_ranges

CH_RANGES = get_chapter_range()
print(f"  找到 {len(CH_RANGES)} 章: {list(CH_RANGES.keys())}")

def get_ch_text(ch_num):
    """获取某章的完整文本"""
    if ch_num in CH_RANGES:
        s, e = CH_RANGES[ch_num]
        return '\n'.join(lines[s:e+1])
    return ''

def extract_section_titles():
    """
    提取所有小节标题（形如 X.X.X title）
    返回 [(ch_num, title_text, line_range_start)]
    """
    sections = []
    SECTION_PAT = re.compile(r'^(\d+)\.(\d+)\.(\d+)\s+(.+)')
    
    # 映射章节号到章编号
    ch_map = {}
    CH_PATTERN = re.compile(r'第([一二三四五六七八九十\d+])章')
    current_ch = None
    for i, line in enumerate(lines):
        m = CH_PATTERN.match(line.lstrip('\ufeff'))
        if m:
            ch_num_str = m.group(1)
            ch_map_nums = {'一':1,'二':2,'三':3,'四':4,'五':5,
                          '六':6,'七':7,'八':8,'九':9,'十':10}
            current_ch = ch_map_nums.get(ch_num_str) or int(ch_num_str)
        
        sm = SECTION_PAT.match(line.strip())
        if sm and current_ch:
            ch0 = int(sm.group(1))
            sec1 = int(sm.group(2))
            sec2 = int(sm.group(3))
            title = sm.group(4).strip()
            # 去掉标题中的编号前缀如 "1." 或 "2."
            title = re.sub(r'^\d+\.\s*', '', title)
            if title and len(title) >= 2:
                sections.append((current_ch, title, i))
    
    return sections

SECTION_TITLES = extract_section_titles()
print(f"  提取 {len(SECTION_TITLES)} 个小节标题")
# 打印前10个
for cn, t, line_no in SECTION_TITLES[:10]:
    print(f"    ch{cn}: {t}")


# ============================================================
# 3. LTP 依存句法分析提取技术术语
# ============================================================
print("\n[3/6] LTP 依存句法分析（逐章处理）...")
sys.stdout.flush()

from ltp import LTP
ltp = LTP()

def ltp_extract_terms(ch_text, ch_num):
    """
    对一章文本做 LTP 分析，提取技术短语和关系三元组
    返回 (entities_set, triples_list)
    """
    def is_good_term(term):
        """判断是否值得保留的技术术语"""
        if len(term) < 2 or len(term) > 15:
            return False
        if term in STOP_WORDS or term in GENERIC_WORDS:
            return False
        # 纯数字或字母
        if re.match(r'^[0-9a-zA-Z\s]+$', term):
            return False
        # 以某些字开头的通常不是实体
        if re.match(r'^[这那每某该各本此其何谁怎什么哪]', term):
            return False
        # 以动词后缀结尾的短词
        if term.endswith(('了', '着', '过', '的', '地', '得', '与', '和', '或')):
            return False
        # 纯英文或拼音
        if all(ord(c) < 256 for c in term):
            return False
        return True
    
    # 切句子
    sents = [s.strip() for s in re.split(r'(?<=[。！？；])\s*', ch_text) 
             if len(s.strip()) > 10]
    
    entities = set()
    triples = []
    
    for sent in sents[:200]:  # 每章最多处理200句
        try:
            result = ltp.pipeline([sent], tasks=['cws', 'pos', 'ner', 'dep'], 
                                  raw_format=True)
            words = result.cws[0]
            postags = result.pos[0]
            ner_tags = result.ner[0]
            dep_heads = result.dep[0]["head"]
            dep_rels = result.dep[0]["label"]
        except:
            continue
        
        # 3a. NER 实体
        i = 0
        while i < len(words):
            if ner_tags[i] != 'O':
                ent_type = ner_tags[i]
                ent_words = [words[i]]
                i += 1
                while i < len(words) and ner_tags[i] == ent_type:
                    ent_words.append(words[i])
                    i += 1
                ent_text = ''.join(ent_words)
                if is_good_term(ent_text):
                    entities.add(ent_text)
            else:
                i += 1
        
        # 3b. 复合名词短语（NN复合）
        compounds = []
        i = 0
        while i < len(words):
            if postags[i].startswith(('n', 'j', 'ws')):
                compound = [words[i]]
                i += 1
                while i < len(words) and postags[i].startswith(('n', 'j', 'v', 'ws')):
                    compound.append(words[i])
                    i += 1
                if len(compound) >= 2:
                    phrase = ''.join(compound)
                    if is_good_term(phrase):
                        compounds.append(phrase)
            else:
                i += 1
        entities.update(compounds)
        
        # 3c. 依存关系提取三元组 (SBV-VOB)
        # 找主语-谓语-宾语结构
        sbv_pairs = []  # (subj_idx, pred_idx)
        for idx, (head, rel) in enumerate(zip(dep_heads, dep_rels)):
            if rel == 'SBV' and head > 0:
                sbv_pairs.append((idx, head - 1))
        
        for subj_idx, pred_idx in sbv_pairs:
            subj = words[subj_idx]
            pred = words[pred_idx]
            # 找这个谓语的宾语
            for obj_idx, (ohead, orel) in enumerate(zip(dep_heads, dep_rels)):
                if orel == 'VOB' and ohead - 1 == pred_idx:
                    obj = words[obj_idx]
                    # 只要至少一个是实体
                    if subj in entities or obj in entities:
                        triples.append((subj, pred, obj, ch_num))
                    break
    
    return entities, triples


# 逐章处理
ch_entities = {}       # ch_num -> list of entities
ch_entity_freq = {}    # ch_num -> Counter
all_triples = []       # list of (subj, pred, obj, ch_num)
all_ch_entities = defaultdict(set)  # ch_num -> set of entities

for ch_num in sorted(CH_RANGES.keys()):
    ch_text = get_ch_text(ch_num)
    if not ch_text or len(ch_text) < 200:
        continue
    
    print(f"  LTP 处理第{ch_num}章 ({len(ch_text)} 字符)...", end=' ')
    sys.stdout.flush()
    t0 = time.time()
    
    entities, triples = ltp_extract_terms(ch_text, ch_num)
    all_ch_entities[ch_num].update(entities)
    all_triples.extend(triples)
    
    freq = Counter()
    for e in entities:
        freq[e] = ch_text.count(e)
    ch_entity_freq[ch_num] = freq
    
    print(f" 实体:{len(entities)} 三元组:{len(triples)} 耗时:{time.time()-t0:.1f}s")
    sys.stdout.flush()

# 合并所有 LTP 实体
ltp_entity_set = set()
for ents in all_ch_entities.values():
    ltp_entity_set.update(ents)
print(f"\n  LTP 共提取 {len(ltp_entity_set)} 个实体, {len(all_triples)} 个三元组")


# ============================================================
# 4. 合并标题实体 + LTP 实体，统计排序
# ============================================================
print("\n[4/6] 合并实体 + 统计排序...")

# 标题实体的权重（标题是最重要的）
section_entity_set = set()
for ch_num, title, line_no in SECTION_TITLES:
    section_entity_set.add(title)

# 合并：LTP实体 + 标题实体
# 标题自动加入所属章节
for ch_num, title, line_no in SECTION_TITLES:
    all_ch_entities[ch_num].add(title)

# 统计每章实体词频
entity_data = {}  # name -> {ch_num, freq, weight, is_section_title, def, para}

# 1. 先将所有标题加入实体列表（每个标题归到它的章节）
for ch_num, title, line_no in SECTION_TITLES:
    if title not in entity_data:
        entity_data[title] = {
            'ch_num': ch_num,
            'freq': 1000,  # 标题默认高频率
            'is_section_title': True,
            'chapters_mentioned': {ch_num},
        }
    else:
        entity_data[title]['is_section_title'] = True
        entity_data[title]['chapters_mentioned'].add(ch_num)

# 2. 加入 LTP 实体
for ch_num in sorted(CH_RANGES.keys()):
    if ch_num not in all_ch_entities:
        continue
    
    ch_text = get_ch_text(ch_num)
    freq_map = ch_entity_freq.get(ch_num, Counter())
    
    for e in all_ch_entities[ch_num]:
        # 跳过已在标题中的
        if e in entity_data:
            entity_data[e]['freq'] += freq_map.get(e, ch_text.count(e))
            entity_data[e]['chapters_mentioned'].add(ch_num)
            continue
        
        freq = freq_map.get(e, ch_text.count(e))
        # 过滤低频率实体
        if freq < 2:
            continue
        
        entity_data[e] = {
            'ch_num': ch_num,
            'freq': freq,
            'is_section_title': False,
            'chapters_mentioned': {ch_num},
        }

print(f"  共 {len(entity_data)} 个候选实体")

# 3. 跨章过滤 + 每章只保留前 MAX_ENTITIES_PER_CHAPTER 个
# 出现在3章以上的视为通用概念，排除
entity_data = {n:d for n,d in entity_data.items() 
               if len(d['chapters_mentioned']) < 3 
               or d['is_section_title']}

# 按章节重排，每章取 Top N
ch_ordered = {}
for name, d in entity_data.items():
    ch = d['ch_num']
    if ch not in ch_ordered:
        ch_ordered[ch] = []
    ch_ordered[ch].append((name, d['freq'] * (1000 if d['is_section_title'] else 1)))

# 标题自动入选，LTP实体按频率排序后选满
final_candidate_names = set()
for ch in sorted(CH_RANGES.keys()):
    if ch not in ch_ordered:
        continue
    items = ch_ordered[ch]
    # 标题在前面
    titles = [(n,f) for n,f in items if entity_data[n]['is_section_title']]
    others = [(n,f) for n,f in items if not entity_data[n]['is_section_title']]
    others.sort(key=lambda x: -x[1])
    
    selected = set(n for n,_ in titles)
    remaining = MAX_ENTITIES_PER_CHAPTER - len(titles)
    if remaining > 0:
        for n,_ in others[:remaining]:
            selected.add(n)
    final_candidate_names.update(selected)

print(f"  去重和跨章过滤后: {len(final_candidate_names)} 个 (每章 ≤{MAX_ENTITIES_PER_CHAPTER})")

# 统计各章节实体数
for ch in sorted(CH_RANGES.keys()):
    cnt = sum(1 for n in final_candidate_names if entity_data[n]['ch_num'] == ch)
    print(f"    第{ch}章: {cnt} 个")


# ============================================================
# 5. LLM 验证实体质量
# ============================================================
print("\n[5/6] LLM 验证实体质量...")
sys.stdout.flush()

def llm_ask(prompt, timeout=20):
    """调用 Ollama LLM"""
    try:
        r = requests.post(OLLAMA_URL, json={
            'model': LLM_MODEL,
            'prompt': prompt,
            'stream': False,
        }, timeout=timeout)
        return r.json().get('response', '').strip()
    except:
        return ''

def llm_validate_entity(entity):
    """验证实体是否是 KG 领域概念"""
    prompt = f"""判断"{entity}"是否是知识图谱（Knowledge Graph）领域的技术概念或专业术语。
只需回答"是"或"否"。
如果是通用词（如"工作""方法""技术""问题""方面""情况""部分"等）或示例人物（如"小明""小红"等），回答"否"。
如果是知识图谱领域的具体技术概念、算法、模型、方法、应用场景，回答"是"。
回答："""
    resp = llm_ask(prompt, timeout=15)
    return resp == '是'


# 章节标题自动通过验证（不用再问LLM）
section_title_names = set(t for _, t, _ in SECTION_TITLES)

validated_names = set()
for name in final_candidate_names:
    if name in section_title_names:
        validated_names.add(name)

# 其他实体 LLM 验证
others_to_check = [n for n in final_candidate_names if n not in validated_names]
valid_count = len(validated_names)
invalid_count = 0

print(f"  标题实体跳过验证: {len(validated_names)} 个")
print(f"  需要 LLM 验证: {len(others_to_check)} 个")

for i, name in enumerate(others_to_check):
    if llm_validate_entity(name):
        validated_names.add(name)
        valid_count += 1
    else:
        invalid_count += 1
    
    if (i+1) % 10 == 0 or i == len(others_to_check)-1:
        print(f"  LLM 验证: {i+1}/{len(others_to_check)} (累计通过:{valid_count} 过滤:{invalid_count})")
        sys.stdout.flush()

print(f"\n  LLM 验证完成: 通过 {valid_count} 个, 过滤 {invalid_count} 个")


# ============================================================
# 6. 提取定义 + 段落 + 构建关联
# ============================================================
print("\n[6/6] 提取定义 + 段落 + 构建关联...")

def extract_definition(ch_text, entity, max_len=300):
    """从章节文本提取实体的完整定义句子"""
    sents = [s.strip() for s in re.split(r'(?<=[。！？])\s*', ch_text) 
             if s.strip() and len(s.strip()) > 10]
    
    def is_good_sent(sent):
        if len(sent) < 15: return False
        # 跳过含引用标记的
        if 'DBpedia' in sent or 'WordNet' in sent: return False
        if '详细介绍' in sent or '详见' in sent: return False
        return True
    
    # 优先找定义模式
    for i, sent in enumerate(sents):
        if entity not in sent: continue
        if not is_good_sent(sent): continue
        if any(p in sent for p in ['是指','指的是','就是','定义为','称为','即','简称','表示']):
            ctx = sent
            if i > 0 and len(ctx) < 200:
                ctx = sents[i-1][-50:] + ctx
            if i+1 < len(sents) and len(ctx) < 200:
                ctx += sents[i+1][:100]
            return ctx[:max_len]
    
    # 找"XX是"判断句
    for i, sent in enumerate(sents):
        if entity not in sent: continue
        if not is_good_sent(sent): continue
        if entity + '是' in sent:
            ctx = sent
            if i > 0: ctx = sents[i-1][-40:] + ctx
            return ctx[:max_len]
    
    # 包含实体的完整句
    for sent in sents:
        if entity in sent and len(sent) >= 20 and is_good_sent(sent):
            return sent[:max_len]
    
    return ''

def extract_paragraph(ch_text, entity, max_len=500):
    """提取包含实体的完整段落"""
    paras = [p.strip() for p in ch_text.split('\n') 
             if len(p.strip()) >= 30]
    
    best_para = ''
    best_score = 0
    for para in paras:
        if entity in para:
            score = len(para) - abs(len(para) - 300)  # 300字左右最好
            if para.count(entity) > 1:
                score += 50  # 多次出现加分
            if score > best_score:
                best_score = score
                best_para = para
    
    if len(best_para) > max_len:
        # 找到实体位置，取上下文
        pos = best_para.find(entity)
        start = max(0, pos - 100)
        end = min(len(best_para), pos + 300)
        best_para = best_para[start:end]
    
    return best_para[:max_len]


# 为每个通过验证的实体提取定义和段落
ch_texts = {ch_num: get_ch_text(ch_num) for ch_num in CH_RANGES}

final_data = {}
for name in validated_names:
    info = entity_data[name]
    ch_num = info['ch_num']
    ch_text = ch_texts.get(ch_num, full_text)
    
    definition = extract_definition(ch_text, name)
    paragraph = extract_paragraph(ch_text, name)
    
    # 如果是章节标题，尝试在标题下一段找更好的定义
    if info.get('is_section_title') and (not definition or len(definition) < 30):
        # 找标题所在行，取下一行作为定义
        for cn, title, line_no in SECTION_TITLES:
            if title == name and cn == ch_num:
                next_lines = lines[line_no+1:line_no+5]
                next_text = ''.join(next_lines).strip()
                if next_text and len(next_text) > 20:
                    definition = next_text[:300]
                break
    
    # 计算权重
    freq = info.get('freq', 0)
    weight = freq * (1.5 if info.get('is_section_title') else 1.0)
    
    final_data[name] = {
        'ch_num': ch_num,
        'weight': round(weight / (sum(entity_data[n]['freq'] for n in validated_names) or 1), 4),
        'freq': freq,
        'is_section_title': info.get('is_section_title', False),
        'definition': definition or '(暂无定义)',
        'paragraph': paragraph or '(暂无段落)',
        'related_entities': [],
    }


# ── 构建实体关联 ──
# 1. 从 LTP 三元组提取关联
ch_entity_names = defaultdict(set)
for name, d in final_data.items():
    ch_entity_names[d['ch_num']].add(name)

for subj, pred, obj, ch_num in all_triples:
    if subj in final_data and obj in final_data:
        final_data[subj]['related_entities'].append({
            'name': obj, 'type': pred, 'strength': 1
        })
        final_data[obj]['related_entities'].append({
            'name': subj, 'type': pred, 'strength': 1
        })

# 2. 章节标题-子概念关联（结构层级）
for ch_num, title, line_no in SECTION_TITLES:
    if title not in final_data:
        continue
    # 找出本节内的其他实体
    section_end = None
    for other_cn, other_title, other_line_no in SECTION_TITLES:
        if other_cn == ch_num and other_line_no > line_no:
            section_end = other_line_no
            break
    if section_end is None:
        section_end = CH_RANGES.get(ch_num, (line_no, len(lines)))[1]
    
    section_text = '\n'.join(lines[line_no:section_end+1])
    for entity_name in list(final_data.keys()):
        if entity_name == title or final_data[entity_name]['ch_num'] != ch_num:
            continue
        if entity_name in section_text and entity_name not in [r['name'] for r in final_data[title]['related_entities']]:
            final_data[title]['related_entities'].append({
                'name': entity_name, 'type': '包含概念', 'strength': 2
            })
            final_data[entity_name]['related_entities'].append({
                'name': title, 'type': '所属章节', 'strength': 2
            })

# 3. 同章共现实体关联
for ch_num in sorted(CH_RANGES.keys()):
    ch_ents = [n for n, d in final_data.items() if d['ch_num'] == ch_num]
    ch_text = ch_texts.get(ch_num, '')
    
    # 段落共现
    paras = [p.strip() for p in ch_text.split('\n') if len(p.strip()) > 50]
    co_occur = Counter()
    for para in paras:
        found = [e for e in ch_ents if e in para]
        for i in range(len(found)):
            for j in range(i+1, len(found)):
                co_occur[tuple(sorted([found[i], found[j]]))] += 1
    
    for (e1, e2), c in co_occur.items():
        if c >= 2:
            if e2 not in [r['name'] for r in final_data[e1]['related_entities']]:
                final_data[e1]['related_entities'].append({
                    'name': e2, 'type': '相关', 'strength': min(c, 5)
                })
                final_data[e2]['related_entities'].append({
                    'name': e1, 'type': '相关', 'strength': min(c, 5)
                })

# 计算总关系数
total_rels = sum(len(d['related_entities']) for d in final_data.values()) // 2
print(f"  最终: {len(final_data)} 实体, {total_rels} 关系")


# ── 保存 JSON ──
with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(final_data, f, ensure_ascii=False, indent=2)
print(f"  OK 保存: {OUTPUT_JSON} ({len(final_data)} 实体)")


# ============================================================
# 7. 生成交互式 HTML
# ============================================================
print("\n生成 HTML 交互式知识图谱...")

# 按章节组织
chapters = {}
for ch_num in sorted(CH_RANGES.keys()):
    chapters[ch_num] = [n for n, d in final_data.items() if d['ch_num'] == ch_num]

# 生成 vis-network HTML
html = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>知识图谱 V5 - 交互式学习</title>
<script src="lib/vis-9.1.2/vis-network.min.js"></script>
<link href="lib/vis-9.1.2/vis-network.css" rel="stylesheet">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, "Microsoft YaHei", sans-serif; background: #f0f2f5; }
#header { background: linear-gradient(135deg, #1a237e, #283593); color: #fff; padding: 20px 30px; }
#header h1 { font-size: 22px; font-weight: 600; }
#header p { font-size: 13px; opacity: 0.8; margin-top: 4px; }
#main { display: flex; height: calc(100vh - 80px); }
#sidebar { width: 320px; min-width: 320px; background: #fff; border-right: 1px solid #e0e0e0; display: flex; flex-direction: column; }
#chapter-tabs { display: flex; flex-wrap: wrap; gap: 4px; padding: 10px; border-bottom: 1px solid #e0e0e0; }
.ch-tab { padding: 4px 10px; border-radius: 12px; border: 1px solid #ccc; cursor: pointer; font-size: 12px; background: #fff; }
.ch-tab:hover { background: #e3f2fd; }
.ch-tab.active { background: #1a237e; color: #fff; border-color: #1a237e; }
#entity-list { flex: 1; overflow-y: auto; padding: 8px; }
.entity-item { padding: 8px 12px; border-radius: 6px; margin-bottom: 4px; cursor: pointer; font-size: 13px; transition: all 0.2s; border-left: 3px solid transparent; }
.entity-item:hover { background: #e3f2fd; }
.entity-item.selected { border-left-color: #1a237e; background: #e8eaf6; }
.entity-item .badge { display: inline-block; font-size: 10px; background: #c5cae9; color: #1a237e; padding: 1px 6px; border-radius: 8px; margin-left: 6px; }
#graph-container { flex: 1; position: relative; background: #fff; }
#detail-panel { position: absolute; right: 20px; top: 20px; width: 360px; max-height: calc(100vh - 140px); background: #fff; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); padding: 16px; overflow-y: auto; display: none; z-index: 10; }
#detail-panel h3 { font-size: 16px; color: #1a237e; margin-bottom: 6px; }
#detail-panel .meta { font-size: 12px; color: #666; margin-bottom: 8px; }
#detail-panel .section { margin-bottom: 10px; }
#detail-panel .section h4 { font-size: 13px; color: #444; margin-bottom: 4px; }
#detail-panel .section p { font-size: 13px; color: #333; line-height: 1.6; }
#detail-panel .close-btn { position: absolute; right: 12px; top: 12px; cursor: pointer; font-size: 18px; color: #999; }
.empty-state { text-align: center; color: #999; padding: 40px 20px; font-size: 14px; }
#legend { position: absolute; left: 20px; bottom: 20px; background: rgba(255,255,255,0.95); border-radius: 8px; padding: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); font-size: 12px; z-index: 10; }
#legend .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px; }
#legend .row { margin-bottom: 3px; }
</style>
</head>
<body>

<div id="header">
  <h1>📚 知识图谱：方法、实践与应用</h1>
  <p>V5 混合提取 · <span id="stats-text"></span></p>
</div>

<div id="main">
  <div id="sidebar">
    <div id="chapter-tabs"></div>
    <div id="entity-list"></div>
  </div>
  <div id="graph-container">
    <div id="legend">
      <div class="row"><span class="dot" style="background:#e53935;"></span>章节标题</div>
      <div class="row"><span class="dot" style="background:#1565c0;"></span>技术概念</div>
      <div class="row"><span class="dot" style="background:#43a047;"></span>包含/所属关系</div>
      <div class="row"><span class="dot" style="background:#f9a825;"></span>相关关系</div>
    </div>
    <div id="detail-panel">
      <span class="close-btn" onclick="closeDetail()">&times;</span>
      <div id="detail-content"></div>
    </div>
  </div>
</div>

<script>
// ── 图数据 ──
const DATA = ''' + json.dumps(final_data, ensure_ascii=False) + r''';
const CH_RANGES = ''' + json.dumps({str(k): v for k,v in CH_RANGES.items()}, ensure_ascii=False) + r''';

const chapters = {};
const chLabels = ['','第一章 知识图谱概述','第二章 知识图谱表示与建模','第三章 知识图谱存储与查询',
                  '第四章 知识图谱抽取','第五章 知识图谱融合','第六章 知识图谱推理',
                  '第七章 知识图谱搜索','第八章 知识问答','第九章 知识图谱应用'];

for (const [name, d] of Object.entries(DATA)) {
    const ch = d.ch_num;
    if (!chapters[ch]) chapters[ch] = [];
    chapters[ch].push(name);
}

// 渲染章节标签
const tabsEl = document.getElementById('chapter-tabs');
for (const ch of Object.keys(chapters).sort((a,b)=>a-b)) {
    const tab = document.createElement('span');
    tab.className = 'ch-tab';
    tab.textContent = `第${ch}章`;
    tab.onclick = () => showChapter(ch);
    tabsEl.appendChild(tab);
}

let currentChapter = null;
let network = null;

// 显示章节
function showChapter(ch) {
    currentChapter = ch;
    document.querySelectorAll('.ch-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.ch-tab')[Object.keys(chapters).indexOf(String(ch))].classList.add('active');
    
    const names = chapters[ch] || [];
    const listEl = document.getElementById('entity-list');
    listEl.innerHTML = '';
    
    // 先标题后按权重排序
    names.sort((a,b) => {
        const da = DATA[a], db = DATA[b];
        if (da.is_section_title && !db.is_section_title) return -1;
        if (!da.is_section_title && db.is_section_title) return 1;
        return db.weight - da.weight;
    });
    
    names.forEach(name => {
        const d = DATA[name];
        const item = document.createElement('div');
        item.className = 'entity-item';
        item.innerHTML = `<strong>${name}</strong> <span class="badge">${(d.weight*1000).toFixed(0)}</span>`;
        item.onclick = () => { showEntity(name); highlightNode(name); };
        item.id = 'item-' + name.replace(/[^a-zA-Z0-9\u4e00-\u9fff]/g, '_');
        listEl.appendChild(item);
    });
    
    buildGraph(ch);
}

// 详情
function showEntity(name) {
    const d = DATA[name];
    if (!d) return;
    document.querySelectorAll('.entity-item').forEach(e => e.classList.remove('selected'));
    const item = document.getElementById('item-' + name.replace(/[^a-zA-Z0-9\u4e00-\u9fff]/g, '_'));
    if (item) item.classList.add('selected');
    
    document.getElementById('detail-content').innerHTML = `
        <h3>${d.is_section_title ? '📌 ' : ''}${name}</h3>
        <div class="meta">第${d.ch_num}章 · 权重 ${(d.weight*1000).toFixed(0)}${d.is_section_title ? ' · 章节标题' : ''}</div>
        <div class="section">
            <h4>书中定义</h4>
            <p>${d.definition}</p>
        </div>
        <div class="section">
            <h4>原文段落</h4>
            <p>${d.paragraph}</p>
        </div>
        <div class="section">
            <h4>关联实体 (${d.related_entities.length})</h4>
            <p style="font-size:12px;color:#666;">
            ${d.related_entities.slice(0,15).map(r => 
                `<span onclick="showEntity('${r.name}');highlightNode('${r.name}')" style="cursor:pointer;color:#1565c0;text-decoration:underline;">${r.name}</span> (${r.type})`
            ).join(' · ')}
            ${d.related_entities.length > 15 ? `…共${d.related_entities.length}个` : ''}
            </p>
        </div>
    `;
    document.getElementById('detail-panel').style.display = 'block';
}

function closeDetail() {
    document.getElementById('detail-panel').style.display = 'none';
}

// 构建网络图
function buildGraph(ch) {
    const names = chapters[ch] || [];
    const nodes = [];
    const edges = [];
    const nodeSet = new Set(names);
    
    // 横跨实体（出现在其他章但在本章可视化中被引用）
    names.forEach(name => {
        const d = DATA[name];
        d.related_entities.forEach(r => {
            if (DATA[r.name]) nodeSet.add(r.name);
        });
    });
    
    // 创建节点
    Array.from(nodeSet).forEach(name => {
        const d = DATA[name] || {ch_num:ch, is_section_title:false, weight:0, definition:'', paragraph:''};
        const isInChapter = d.ch_num === ch;
        nodes.push({
            id: name,
            label: name,
            title: d.definition || '',
            size: Math.max(12, Math.min(35, (d.weight*1000) * 3 + (d.is_section_title ? 8 : 0))),
            color: d.is_section_title ? {background:'#e53935', border:'#b71c1c'} : 
                   isInChapter ? {background:'#1565c0', border:'#0d47a1'} : 
                   {background:'#78909c', border:'#546e7a'},
            font: {size: d.is_section_title ? 15 : 13, face:'Microsoft YaHei'},
            borderWidth: d.is_section_title ? 3 : 1,
            opacity: isInChapter ? 1.0 : 0.6,
        });
    });
    
    // 创建边
    const addedEdges = new Set();
    names.forEach(name => {
        const d = DATA[name];
        (d.related_entities || []).forEach(r => {
            if (nodeSet.has(r.name)) {
                const key = [name, r.name].sort().join('||');
                if (!addedEdges.has(key)) {
                    addedEdges.add(key);
                    const isContain = r.type === '包含概念' || r.type === '所属章节';
                    edges.push({
                        from: name,
                        to: r.name,
                        label: r.type,
                        width: Math.min(r.strength || 1, 3),
                        color: {color: isContain ? '#43a047' : '#f9a825', opacity: 0.5},
                        font: {size: 10, color:'#666'},
                        arrows: isContain ? {to:{enabled:true, scaleFactor:0.5}} : undefined,
                    });
                }
            }
        });
    });
    
    const container = document.getElementById('graph-container');
    // 移除旧面板
    container.querySelectorAll('.vis-network').forEach(el => el.remove());
    
    const options = {
        nodes: { shape: 'dot', scaling: {min:12, max:35} },
        edges: { smooth: {type:'continuous'}, width: 1 },
        physics: {
            solver: 'forceAtlas2Based',
            forceAtlas2Based: {gravitationalConstant:-40, centralGravity:0.005, springLength:120, springConstant:0.02, damping:0.4},
            stabilization: {iterations:200}
        },
        interaction: { hover: true, tooltipDelay: 200, navigationButtons: true, zoomView: true },
        layout: { improvedLayout: true }
    };
    
    network = new vis.Network(container, {nodes:new vis.DataSet(nodes), edges:new vis.DataSet(edges)}, options);
    
    network.on('click', function(params) {
        if (params.nodes.length > 0) {
            showEntity(params.nodes[0]);
        } else {
            closeDetail();
        }
    });
    
    document.getElementById('stats-text').textContent = `${names.length} 实体 · ${edges.length} 关系 (第${ch}章)`;
    document.getElementById('detail-panel').style.display = 'none';
}

function highlightNode(name) {
    if (network) {
        network.selectNodes([name], true);
        network.focus(name, {scale:1.5, animation:{duration:500}});
    }
}

// 默认显示第1章
const sortedChs = Object.keys(chapters).sort((a,b)=>a-b);
if (sortedChs.length > 0) showChapter(parseInt(sortedChs[0]));
</script>
</body>
</html>'''

with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"  OK HTML: {OUTPUT_HTML}")


# ============================================================
# 完成
# ============================================================
print("\n" + "=" * 60)
print(f"完成! 实体:{len(final_data)} 关系:{total_rels}")
print(f"  JSON: {OUTPUT_JSON}")
print(f"  HTML: {OUTPUT_HTML}")
print("=" * 60)