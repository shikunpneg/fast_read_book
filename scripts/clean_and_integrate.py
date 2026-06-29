"""
清洗 LLM+NLP 提取结果，去噪、去重、规范化，
然后集成到交互式 HTML 中
"""
import json, re
from collections import OrderedDict

DEFINITIONS_FILE = r'e:\nlp\ltp\kg_entity_definitions_v2.json'
ENTITY_DB_FILE = r'e:\nlp\ltp\kg_entity_db_v2.py'
OUTPUT_DEFINITIONS = r'e:\nlp\ltp\kg_entity_definitions_clean.json'
OUTPUT_ENTITY_DB = r'e:\nlp\ltp\kg_entity_db_clean.json'

# ── 1. 加载数据 ──

with open(DEFINITIONS_FILE, encoding='utf-8') as f:
    definitions = json.load(f)

# 加载 entity_db
entity_db = {}
exec(open(ENTITY_DB_FILE, encoding='utf-8').read())
# entity_db 变量由 exec 创建
if 'ENTITY_DB' in locals():
    entity_db = ENTITY_DB

# ── 2. 清洗定义 ──

STOP_WORDS = {
    '应用', '分析', '临床', '智能', '企业', '关联', '融合', '行业',
    '生成', '理解', '问题', '答案', '类型', '解析', '表达式', '模板',
    '数据', '关系', '描述', '信息', '场景', '内容', '功能', '任务',
    '模型', '方法', '系统', '技术', '知识', '图谱', '理论', '工具',
    '概念', '一个', '这些', '这个', '那个', '使用', '通过', '进行',
    '不同', '需要', '可以', '基于', '称为', '就是', '实现', '主要',
    '包括', '分为', '过程', '方面', '方式',
}

def clean_category(cat):
    """清洗类别名称"""
    cat = cat.replace('**', '').strip()
    # 标准化复合类别
    composites = {
        '工具/技术': '工具',
        '工具/方法': '工具',
        '工具/资源': '工具',
        '方法/技术': '方法',
        '理论/技术': '理论',
        '任务/案例研究': '任务',
        '应用场景': '任务',
    }
    return composites.get(cat, cat)

def is_entity_name_valid(name):
    """判断实体名称是否有效"""
    if len(name) < 2 or len(name) > 40:
        return False
    if name in STOP_WORDS:
        return False
    # 检查是否只包含标点和空格
    if re.match(r'^[\s,，。、；：""\'（）()\[\]【】\-_/\\]+$', name):
        return False
    # 检查是否包含过多的通用词
    generic_words_in_name = sum(1 for w in STOP_WORDS if w in name and len(w) >= 2)
    if generic_words_in_name >= 3 and len(name) < 10:
        return False
    # 去除"概念："开头
    if '：' in name and len(name.split('：')[0]) <= 2:
        return False
    return True

def clean_entity_name(name):
    """清洗实体名称"""
    # 去除"概念：XXX"前缀
    name = re.sub(r'^(概念|方法|技术|工具|理论|任务)[：:]\s*', '', name)
    # 去除多余空格
    name = re.sub(r'\s+', '', name)
    # 截断过长名称
    if len(name) > 35:
        name = name[:35]
    return name.strip()

# 清洗定义
cleaned_definitions = {}
for name, info in definitions.items():
    clean_name = clean_entity_name(name)
    if not is_entity_name_valid(clean_name):
        continue
    
    # 清理定义文字
    definition = info['definition']
    # 截断不完整的句子（以非句号结尾、字数少于15的）
    if len(definition) > 20 and definition[-1] not in '。！？.!?\n':
        # 找到最后一个句号截断
        last_period = max(definition.rfind('。'), definition.rfind('.'))
        if last_period > 10:
            definition = definition[:last_period+1]
    
    category = clean_category(info['category'])
    chapter = info['chapter']
    
    key = clean_name  # 去重
    if key not in cleaned_definitions or len(definition) > len(cleaned_definitions[key]['definition']):
        cleaned_definitions[key] = {
            'definition': definition,
            'chapter': chapter,
            'category': category,
        }

# ── 3. 清洗实体数据库 ──

cleaned_entity_db = OrderedDict()
for ch_title in sorted(entity_db.keys(), key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0):
    entities = entity_db[ch_title]
    cleaned = []
    for ent in entities:
        clean_name = clean_entity_name(ent)
        if is_entity_name_valid(clean_name) and clean_name not in cleaned:
            cleaned.append(clean_name)
    # 限制每章15个
    cleaned_entity_db[ch_title] = cleaned[:15]

# ── 4. 交叉引用：确保每个实体都有定义 ──

# 为实体数据库中缺少定义的实体自动补充
for ch_title, entities in cleaned_entity_db.items():
    for ent in entities:
        if ent not in cleaned_definitions:
            # 从 entity_db 的原始条目找定义
            for orig_name, info in definitions.items():
                if clean_entity_name(orig_name) == ent:
                    cleaned_definitions[ent] = {
                        'definition': info['definition'],
                        'chapter': info['chapter'],
                        'category': clean_category(info['category']),
                    }
                    break

# ── 5. 统计 ──

print("=" * 50)
print("📊 清洗结果统计")
print("=" * 50)
print(f"清洗前定义数: {len(definitions)}")
print(f"清洗后定义数: {len(cleaned_definitions)}")

ch_counts = {}
for info in cleaned_definitions.values():
    ch = info['chapter']
    ch_counts[ch] = ch_counts.get(ch, 0) + 1

for ch in sorted(ch_counts.keys(), key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0):
    print(f"  {ch}: {ch_counts[ch]} 个定义")

# 类别分布
from collections import Counter
cats = Counter()
for info in cleaned_definitions.values():
    cats[info['category']] += 1
print(f"\n类别分布:")
for cat, count in cats.most_common(10):
    print(f"  {cat}: {count}")

# ── 6. 保存 ──

with open(OUTPUT_DEFINITIONS, 'w', encoding='utf-8') as f:
    json.dump(cleaned_definitions, f, ensure_ascii=False, indent=2)
print(f"\n✅ 清洗后定义保存: {OUTPUT_DEFINITIONS}")

with open(OUTPUT_ENTITY_DB, 'w', encoding='utf-8') as f:
    json.dump(cleaned_entity_db, f, ensure_ascii=False, indent=2)
print(f"✅ 清洗后实体库保存: {OUTPUT_ENTITY_DB}")

# ── 7. 示例展示 ──

print("\n📖 各章实体示例:")
for ch_title in list(cleaned_entity_db.keys())[:3]:
    ents = cleaned_entity_db[ch_title]
    print(f"\n{ch_title}:")
    for ent in ents[:8]:
        defn = cleaned_definitions.get(ent, {}).get('definition', '')
        print(f"  🔹 {ent} [{cleaned_definitions.get(ent, {}).get('category', '')}]")
        if defn:
            print(f"     {defn[:80]}...")