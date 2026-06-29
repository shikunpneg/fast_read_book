"""
知识图谱 · 定义提取器
从全书原文中为每个实体提取对应的定义段落
"""
import re, json, os

BOOK_TEXT = r'e:\nlp\ltp\kg_book_full.txt'
OUTPUT_JSON = r'e:\nlp\ltp\kg_entity_definitions.json'

# ── 第5-9章关键实体（从章节标题和常见知识图谱术语提取） ──
CHAPTER_5_ENTITIES = [
    "知识图谱融合", "本体映射", "实例匹配", "异构问题",
    "语言层不匹配", "模型层不匹配", "本体概念层", "实例层",
    "本体集成", "本体映射方法", "本体映射工具", "本体映射管理",
    "相似度计算", "快速相似度计算", "基于规则的实例匹配",
    "基于分治的实例匹配", "基于学习的实例匹配", "分布式并行处理",
    "LIMES", "实体关系发现",
]

CHAPTER_6_ENTITIES = [
    "知识图谱推理", "演绎推理", "归纳推理", "本体推理",
    "逻辑编程", "查询重写", "产生式规则", "图结构推理",
    "规则学习", "表示学习", "时序预测推理", "强化学习",
    "元学习", "少样本学习", "图神经网络", "Jena", "Drools",
    "知识推理",
]

CHAPTER_7_ENTITIES = [
    "语义搜索", "查询语言", "SPARQL", "数据查询", "数据插入",
    "数据删除", "语义数据搜索", "交互范式", "关键词搜索",
    "分面搜索", "表示学习搜索", "Elasticsearch",
    "知识图谱语义搜索",
]

CHAPTER_8_ENTITIES = [
    "知识问答", "问答系统", "NLIDB", "IRQA", "KBQA",
    "CommunityQA", "FAQ-QA", "混合问答系统", "问题分类",
    "答案类型", "语义解析", "深度学习", "端到端问答",
    "模板方法", "评价指标", "评价数据集", "gAnswer",
    "知识库问答",
]

CHAPTER_9_ENTITIES = [
    "领域知识图谱", "自顶向下构建", "自底向上构建",
    "知识建模", "知识计算", "知识应用", "电商知识图谱",
    "图情知识图谱", "企业商业知识图谱", "创投知识图谱",
    "中医临床知识图谱", "金融知识图谱", "美团知识图谱",
    "领域知识建模", "技术流程",
]

# 各章节已有实体（从KGGen结果补充）
CHAPTER_1_ENTITIES = [
    "知识图谱", "早期知识库项目", "机器推理", "价值", "智能问答",
    "中文开放知识图谱", "区块链", "历史", "相关技术", "推荐系统",
    "垂直领域知识图谱", "互联网时代的知識图谱",
]
CHAPTER_2_ENTITIES = [
    "一阶谓词逻辑", "语义标记表示语言", "Freebase", "框架",
    "霍恩子句和霍恩逻辑", "知识图谱嵌入", "Wikidata", "Protégé",
    "RDF", "知识表示", "开源工具实践",
]
CHAPTER_3_ENTITIES = [
    "Neo4j", "查询语言", "三元组数据库", "开源工具", "gStore",
    "数据模型", "数据库", "原生图数据库", "Apache Jena",
    "存储方法", "关系数据库",
]
CHAPTER_4_ENTITIES = [
    "开源工具", "规则挖掘", "事件抽取", "关系抽取",
    "R2RML", "直接映射", "DeepDive", "知识抽取任务",
    "实体抽取", "相关竞赛", "知识挖掘",
]

# 全部实体按章节组织
ALL_CHAPTER_ENTITIES = {
    "第1章 知识图谱 概述": CHAPTER_1_ENTITIES,
    "第2章 知识图谱 表示与建模": CHAPTER_2_ENTITIES,
    "第3章 知识存储": CHAPTER_3_ENTITIES,
    "第4章 知识抽取 与知识挖掘": CHAPTER_4_ENTITIES,
    "第5章 知识图谱融合": CHAPTER_5_ENTITIES,
    "第6章 知识图谱推理": CHAPTER_6_ENTITIES,
    "第7章 语义搜索": CHAPTER_7_ENTITIES,
    "第8章 知识问答": CHAPTER_8_ENTITIES,
    "第9章 知识图谱应用 案例": CHAPTER_9_ENTITIES,
}


def load_book_text():
    with open(BOOK_TEXT, encoding='utf-8') as f:
        return f.read()


def split_into_chapters(text):
    """将全书按章节分割"""
    lines = text.split('\n')
    chapters = {}
    cur_ch = None
    cur_text = []

    for line in lines:
        m = re.match(r'^(第[一二三四五六七八九十\d]+章\s+.+)$', line.strip())
        if m:
            if cur_ch:
                chapters[cur_ch] = '\n'.join(cur_text)
            cur_ch = m.group(1).strip()
            cur_text = [line]
        elif cur_ch:
            cur_text.append(line)

    if cur_ch and cur_text:
        chapters[cur_ch] = '\n'.join(cur_text)
    return chapters


def extract_paragraphs(text):
    """将文本分割为段落"""
    paras = []
    current = []
    for line in text.split('\n'):
        ls = line.strip()
        if not ls:
            if current:
                paras.append(' '.join(current))
                current = []
        else:
            current.append(ls)
    if current:
        paras.append(' '.join(current))
    return paras


def find_definition(paragraph, entity):
    """判断段落是否为实体的定义段落"""
    para = paragraph.strip()
    if not para or len(para) < 10:
        return None

    # 定义模式
    def_patterns = [
        rf'{re.escape(entity)}(是指|指的是|就是|定义为|可以定义为|可定义为|表示|描述了|是[一种类套个])',
        rf'(所谓|我们称|通常称|一般将|我们把).{{0,20}}{re.escape(entity)}',
        rf'{re.escape(entity)}.{0,20}(是指|指的是|定义为|表示)',
        rf'{re.escape(entity)}.{0,50}(方法|技术|任务|过程|系统|工具|模型|框架|算法|问题)',
    ]

    for pattern in def_patterns:
        if re.search(pattern, para):
            return para[:500]  # 截取前500字

    # 如果段落包含实体且较短（像是定义段）
    if entity in para and len(para) < 300:
        return para

    return None


def find_best_definition(paragraphs, entity):
    """在段落列表中找最佳定义"""
    best = None
    best_score = -1

    for i, para in enumerate(paragraphs):
        if entity not in para:
            continue

        result = find_definition(para, entity)
        if result:
            score = 0
            # 定义模式加分
            for p in ['是指', '指的是', '定义为', '表示', '是一种', '是—种']:
                if p in para:
                    score += 10
            # 靠近段落开头加分
            score += max(0, 20 - i)
            # 段落长度适中加分（太短说明信息不足）
            if 50 <= len(para) <= 400:
                score += 5

            if score > best_score:
                best_score = score
                best = result

    # 回退：只要包含实体的段落
    if not best:
        for para in paragraphs:
            if entity in para and len(para) >= 20:
                # 取实体附近上下文
                idx = para.index(entity)
                start = max(0, idx - 60)
                end = min(len(para), idx + len(entity) + 150)
                snippet = para[start:end]
                if start > 0:
                    snippet = '...' + snippet
                if end < len(para):
                    snippet = snippet + '...'
                return snippet

    return best


def extract_all_definitions():
    print("📖 加载全书文本...")
    text = load_book_text()
    print(f"   总字数: {len(text)}")

    print("📑 按章节分割...")
    chapters = split_into_chapters(text)
    print(f"   章节数: {len(chapters)}")

    # 构建实体 → 定义的映射
    entity_defs = {}  # {entity: {definition, chapter, source}}

    for ch_name, ch_text in chapters.items():
        # 在章节中查找匹配的实体
        matched = []
        for ch_title, entities in ALL_CHAPTER_ENTITIES.items():
            if ch_name.replace(' ', '') in ch_title.replace(' ', '') or ch_title.replace(' ', '') in ch_name.replace(' ', ''):
                matched = entities
                break

        if not matched:
            # 模糊匹配
            for ch_title, entities in ALL_CHAPTER_ENTITIES.items():
                # 取第一个数字匹配
                n1 = re.search(r'\d+', ch_name)
                n2 = re.search(r'\d+', ch_title)
                if n1 and n2 and n1.group() == n2.group():
                    matched = entities
                    break

        if not matched:
            continue

        print(f"\n🔍 {ch_name}")
        paras = extract_paragraphs(ch_text)

        for entity in matched:
            defn = find_best_definition(paras, entity)
            if defn:
                entity_defs[entity] = {
                    "definition": defn,
                    "chapter": ch_name,
                }
                status = "✅" if any(p in defn for p in ['是指', '指的是', '定义为', '表示', '是一种']) else "📎"
                print(f"   {status} {entity}")
            else:
                print(f"   ⚠️  {entity} 未找到定义")

    # 保存
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(entity_defs, f, ensure_ascii=False, indent=2)
    print(f"\n💾 定义已保存: {OUTPUT_JSON}")
    print(f"   共 {len(entity_defs)} 个实体找到定义")

    return entity_defs


if __name__ == '__main__':
    extract_all_definitions()