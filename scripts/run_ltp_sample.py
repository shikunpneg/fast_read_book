"""LTP 处理 2K 样本 - 使用 pipeline API（同 kg.py）"""
import sys, os, time, re
from ltp import LTP

ZH_STOP_WORDS = {
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一',
    '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着',
    '没有', '看', '好', '自己', '这', '他', '她', '它', '们', '那', '些',
    '之', '与', '及', '但', '而', '或', '被', '把', '对', '等', '从',
    '以', '为', '所', '如', '将', '能', '可', '已', '还', '又', '并',
    '中', '大', '小', '多', '少', '其', '个', '种', '些', '某', '各',
    '每', '哪', '谁', '怎', '么', '什么', '如何', '为什么', '因为', '所以',
    '如果', '虽然', '但是', '而且', '然后', '并且', '或者', '不过', '关于',
    '事情', '问题', '方法', '方式', '过程', '时候', '地方', '情况', '部分',
    '进行', '使用', '通过', '利用', '根据', '按照', '经过', '以及', '等等',
    '提出', '采用', '包括', '具有', '属于', '成为', '作为', '看作',
    '当前', '目前', '通常', '一般', '基本', '主要', '重要', '直接', '间接',
    '不同', '相同', '一定', '其他', '各种', '相关', '实际', '一定', '需要',
    '领域', '研究', '工作', '技术', '系统', '数据', '信息', '模型', '方法',
    '基于', '提出', '实现', '采用', '进行', '利用', '分析', '处理',
    '这个', '这些', '那个', '那些', '每个', '某个', '各个', '这种', '该类',
    '两类', '其中', '之间', '之内', '之中', '这时', '那里', '这里', '哪些',
    '任何', '所有', '全部', '整个', '一些', '多个', '多种', '若干', '大量',
    '少量', '部分', '整', '半', '零', '两', '三', '四', '五', '六', '七',
    '八', '九', '十', '百', '千', '万', '亿',
    '方面', '角度', '层面', '维度', '情况', '状态',
}

def is_valid_entity(word, lang='zh'):
    if len(word) <= 1: return False
    if word in ZH_STOP_WORDS: return False
    if re.match(r'^[这那每某该各]', word): return False
    if re.match(r'^[识动显抽提取记表定给构建利运形]', word) and len(word) >= 3:
        allowed = {'机器学习','深度学习','强化学习','监督学习','无监督学习',
                    '半监督学习','迁移学习','表示学习','知识图谱','提取特征','提取数据','提取实体'}
        if word not in allowed: return False
    if word.endswith(('出现', '形成', '构成', '产生', '存在', '进行', '表示')) and word not in {'知识表示'}:
        return False
    return True

# 读取样本
text = open(r'e:\nlp\ltp\kg_book_sample_2k.txt', encoding='utf-8').read()
print(f"📖 输入: {len(text)} 字符")

start = time.time()

ltp = LTP()
print("⏳ LTP pipeline（cws+pos+ner+dep）...")
sys.stdout.flush()

# 按句子切分（同 kg.py）
sentences = [s.strip() for s in re.split(r'[。！？；\n]+', text) if len(s.strip()) > 5]
print(f"  句子数: {len(sentences)}")

all_triples = []
all_entities_set = set()

for idx, sent in enumerate(sentences):
    if (idx + 1) % 5 == 0:
        print(f"  ⏳ 句子 {idx+1}/{len(sentences)}...")
        sys.stdout.flush()
    try:
        result = ltp.pipeline([sent], tasks=['cws', 'pos', 'ner', 'dep'], raw_format=True)
        words = result.cws[0]
        postags = result.pos[0]
        ner_tags = result.ner[0]
        dep_heads = result.dep[0]["head"]
        dep_rels = result.dep[0]["label"]
    except:
        continue

    # 提取 NER 实体
    ent_set = set()
    i = 0
    while i < len(words):
        if ner_tags[i] != 'O':
            entity_type = ner_tags[i]
            entity_words = [words[i]]
            i += 1
            while i < len(words) and ner_tags[i] == entity_type:
                entity_words.append(words[i])
                i += 1
            entity_text = ''.join(entity_words)
            if is_valid_entity(entity_text):
                ent_set.add(entity_text)
        else:
            i += 1

    # 复合名词
    i = 0
    while i < len(words) - 1:
        if postags[i].startswith(('n', 'j', 'ws')) and postags[i+1].startswith(('n', 'v', 'j', 'ws')):
            combined = words[i] + words[i+1]
            if len(combined) <= 6 and is_valid_entity(combined):
                ent_set.add(combined)
        i += 1

    all_entities_set.update(ent_set)
    if len(ent_set) < 1:
        continue

    # 依存关系（SBV + VOB）
    for dep_idx, (head, rel) in enumerate(zip(dep_heads, dep_rels)):
        dep_word = words[dep_idx]
        if head == 0:
            continue
        head_word = words[head - 1]
        
        if rel == 'SBV':
            # 找谓语后的 VOB
            for vob_idx, (vhead, vrel) in enumerate(zip(dep_heads, dep_rels)):
                if vrel == 'VOB' and vhead - 1 == dep_idx:
                    obj_word = words[vob_idx]
                    if dep_word in ent_set and obj_word in ent_set:
                        all_triples.append((dep_word, head_word, obj_word))
                    break
        elif rel == 'VOB':
            # 找主语
            for sbv_idx, (shead, srel) in enumerate(zip(dep_heads, dep_rels)):
                if srel == 'SBV' and shead - 1 == dep_idx and shead == head:
                    subj_word = words[sbv_idx]
                    if subj_word in ent_set and dep_word in ent_set:
                        all_triples.append((subj_word, head_word, dep_word))
                    break

elapsed = time.time() - start
print(f"\n⏱️ 耗时: {elapsed:.1f}s")
print(f"实体: {len(all_entities_set)}")
print(f"三元组: {len(all_triples)}")

print(f"\n实体 ({len(all_entities_set)}):")
for e in sorted(all_entities_set, key=lambda x: -len(x)):
    print(f"  - {e}")

print(f"\n三元组 ({len(all_triples)}):")
for s, p, o in all_triples:
    print(f"  ({s}, {p}, {o})")

with open(r'e:\nlp\ltp\kg_book_sample_ltp.txt', 'w', encoding='utf-8') as f:
    f.write(f"LTP 结果 (耗时 {elapsed:.1f}s)\n")
    f.write(f"实体 ({len(all_entities_set)}):\n")
    for e in sorted(all_entities_set, key=lambda x: -len(x)):
        f.write(f"  - {e}\n")
    f.write(f"\n三元组 ({len(all_triples)}):\n")
    for s, p, o in all_triples:
        f.write(f"  ({s}, {p}, {o})\n")

print(f"\n✅ 保存: kg_book_sample_ltp.txt")