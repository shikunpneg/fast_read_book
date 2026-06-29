"""
知识图谱 V4.1 - LTP + 词频统计 精准提取管线（修正版）
"""
import re, json, os, math
from collections import defaultdict, Counter
import jieba
import jieba.analyse

BOOK_TEXT = r'e:\nlp\ltp\kg_book_full.txt'
OUTPUT_ENRICHED = r'e:\nlp\ltp\kg_entity_v4.json'
OUTPUT_HTML = r'e:\nlp\ltp\kg_book_interactive_v4.html'

CHAPTER_RANGES = {
    1: (405, 1733), 2: (1733, 2742), 3: (2742, 3882),
    4: (3882, 5031), 5: (5031, 8087), 6: (8087, 9422),
    7: (9422, 10049), 8: (10049, 11291), 9: (11291, 12304),
}
CHAPTER_NAMES = {
    1: "第1章 知识图谱概述", 2: "第2章 知识图谱表示与建模", 3: "第3章 知识存储",
    4: "第4章 知识抽取与知识挖掘", 5: "第5章 知识图谱融合", 6: "第6章 知识图谱推理",
    7: "第7章 语义搜索", 8: "第8章 知识问答", 9: "第9章 知识图谱应用案例",
}

with open(BOOK_TEXT, encoding='utf-8') as f:
    book_text = f.read()
book_lines = book_text.split('\n')

# ── 强停用词 ──
STOP_WORDS = set("""
的 了 在 是 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着
没有 看 好 自己 这 他 她 它 们 那 与 及 等 之 而 或 被 对 把 被 让
从 向 以 为 由 于 但 如 因为 所以 如果 虽然 然而 而且 不过 只是
可以 可能 应该 需要 能够 必须 基于 通过 利用 使用 采用 进行 包括
具有 分为 称为 作为 用于 其中 以及 所谓 例如 比如 此外 同时 之后
之前 当中 之间 方面 相关 主要 重要 基本 一般 通常 往往 越来越
大量 多个 不同 各种 这些 那些 每个 有的 一些 这个 那个 什么 怎么
如何 是否 不是 就是 而是 还是 或者 没有 可以 这个 问题 方法 技术
系统 数据 模型 信息 任务 过程 方式 结果 目标 特征 元素 类型 形式
结构 内容 关系 概念 能力 领域 研究 分析 实现 提出 定义 描述 表示
一个 两个 三个 多个 不同 同时 例如 可见 引入 存在 需要 给出 利用
基于 通过 使用 用于 包括 具有 分为 称为 作为 开发 支持 提供 计算
发现 得到 可能 处理 搜索 排序 检索 提取 构建 匹配 识别 预测 管理
模块 函数 配置 参数 相应 具体 自然 需要 目前 因此 此外 通常 左右
以下 如下 所示 给出 利用 而言 数据 信息 关系 应用 问题 理解 完成 进行
基于 定义 开发 提供 支持 处理 识别 搜索 计算 融合 排序 检测
描述 变化 操作 考虑 训练 标注 评估 选择 吸引 调整 指定 行为 研究
提高 关注 降低 类 型 特征 元素 集合 分类 包括 具有
""".split())

# ── 1. TextRank + TF-IDF ──

print("="*60)
print("V4.1 精准提取管线")
print("="*60)
print("\n[1/5] 逐章 TextRank + TF-IDF")

chapters_keywords = {}
for ch_num in range(1, 10):
    start, end = CHAPTER_RANGES[ch_num]
    ch_text = '\n'.join(book_lines[start:end])
    # 保留英文，只清理冗余空白
    ch_text_clean = re.sub(r'\s+', ' ', ch_text.replace('\n', ' ')).strip()
    
    keywords_tr = jieba.analyse.textrank(ch_text_clean, topK=150, withWeight=True,
        allowPOS=('ns','n','vn','v','nr','nt','nz','l','eng'))
    keywords_tfidf = jieba.analyse.extract_tags(ch_text_clean, topK=150, withWeight=True,
        allowPOS=('ns','n','vn','v','nr','nt','nz','l','eng'))
    
    weights = defaultdict(float)
    tr_d = {k:w for k,w in keywords_tr}
    tf_d = {k:w for k,w in keywords_tfidf}
    
    for w in set(list(tr_d.keys()) + list(tf_d.keys())):
        if w in STOP_WORDS or len(w) < 2 or len(w) > 10:
            continue
        # 纯数字/符不要
        if re.match(r'^[\d_]+$', w): continue
        # 纯英文不要（英文专名会单独处理）
        if all(ord(c) < 128 for c in w): continue
        weights[w] = tr_d.get(w,0)*0.4 + tf_d.get(w,0)*0.6
    
    sorted_w = sorted(weights.items(), key=lambda x:-x[1])
    chapters_keywords[ch_num] = sorted_w
    top10 = [w for w,_ in sorted_w[:10]]
    print(f"  第{ch_num}章: {len(sorted_w)} 候选 | Top10: {', '.join(top10)}")

# ── 2. 通用词过滤 ──
print("\n[2/5] 跨章通用词过滤 + 实体质量过滤")

ch_word_count = defaultdict(set)
for ch_num, words in chapters_keywords.items():
    for w,_ in words:
        ch_word_count[w].add(ch_num)

# 出现在3+章的过滤
generic_words = {w for w,chs in ch_word_count.items() if len(chs) >= 3}
print(f"  过滤通用词(3+章): {len(generic_words)} 个")

# 额外过滤：纯动词、太短的
def is_valid_entity(word):
    if len(word) < 2: return False
    if word in STOP_WORDS: return False
    # 纯动词后缀过滤
    verb_suffixes = ['化', '性', '的', '地', '得', '了', '着', '过', '与', '和', '或', '被', '把', '对']
    if word.endswith(tuple(verb_suffixes)) and len(word) <= 3:
        return False
    # 纯数字或字母
    if re.match(r'^[0-9a-zA-Z\s]+$', word): return False
    # 纯英文拼音
    if all(ord(c) < 256 for c in word): return False
    # 额外通用的业务词
    generic_biz = {'商品','形成','集成','体系','找到','词汇','询问','短语','词典','社区',
                   '评价','对话','包含','客户','欺诈','百科','业务','建立','表达',
                   '工作','解答','阅读','统计','人物','回答','服务','商家','大脑','自动',
                   '场景','决策','组合','安装','运行','安装','给定','假设','结论','介绍',
                   '变量','得分','类似','事物','来源','包装','满足','讨论','方面','同时',
                   '方法','问题','技术','水平','开发','不同','需要','通过','利用','进行',
                   '分析','发现','实现','目前','引入','收到','成为','提出','灵巧','访问',
                   '提交','保证','处理','划分','寻找','增加','返回','形成','集成','对应',
                   '获取','加入','面向','关于','提交','访问','使用','采用','写为','有关',
                   '输入','输出','调用','执行','记录','转换','提供','查找','指向','理解',
                   '达到','表示','描述','存在','提出','进行','完成','开发','成为','接受',
                   '写为','设为','看做','归为','名为','兼具','进入','检验','用于','给出',
                   '考虑','作为','目前','特定','大量','其中','之间','不同','各种','相关',
                   '通用','风险','结合','商业','语料','歧义','包装','开放','效率','需求',
                   '质量','操作','模式','基本','联合','运行','依赖','步骤','方案','提示',
                   '元素','顺序','文献','途径','实施','候选','结果','筛选','演变','年份',
                   '能力','引导','背景','走势','大小','互联','海量','形态','菜品','商户',
                   '产品','图情','临床','企业','平台','环境','上下位','示意图','投资',
                   '机构','行业','电商','金融','美团','信息检索','语句','数据源','名称',
                   '插入','指明','在于','删除','导入','格式','数量','电影','洞察',
                   '答案','语法分析','典型','产生','主体','策略','对比','代码',
                   '要求','不能','运动员','姚明','交互','范式','方剂','金融证券',
                   '情况','实验','歌手','表达式'}
    if word in generic_biz:
        return False
    # 2字词但非明显技术词（如合并、验证、同步等一般的动词/名词）
    short_generic = {'合并','验证','同步','更新','划分','寻找','增加','返回',
                     '集成','对应','获取','加入','面向','关于','提交','访问',
                     '写为','有关','输入','输出','调用','记录','转换','查找',
                     '指向','达到','存在','完成','开发','成为','接受','进入',
                     '检验','给出','考虑','作为','目前','特定','大量','其中',
                     '之间','不同','各种','相关','通用','结合','开放','基本',
                     '运行','依赖','步骤','方案','提示','元素','顺序','文献',
                     '途径','实施','候选','结果','筛选','演变','年份','能力',
                     '引导','背景','走势','大小','互联','海量','形态','产品',
                     '图情','临床','企业','自动','菜品','商户',
                     '使用','采用','利用','基于','通过','包括','具有','分为',
                     '称为','作为','开发','支持','提供','计算','虽然','然而',
                     '而且','不过','只是','需要','能够','必须',
                     '用来','资源','流程','确定','字节'}  # 去除技术词
    if len(word) == 2 and word in short_generic:
        return False
    return True

# ── 3. 每章选实体 ──
print("\n[3/5] 按频次选实体")

CH_COUNT = 20
chapter_entities = {}
entity_chapters = {}

for ch_num in range(1, 10):
    words = [(w,wt) for w,wt in chapters_keywords[ch_num]
             if w not in generic_words and is_valid_entity(w)]
    selected = words[:CH_COUNT]
    chapter_entities[ch_num] = selected
    for w,wt in selected:
        if w not in entity_chapters:
            entity_chapters[w] = ch_num
    print(f"  第{ch_num}章: {', '.join(f'{w}({wt:.3f})' for w,wt in selected)}")

# ── 4. 定义提取 ──
print("\n[4/5] 提取完整定义句子")

def classify_entity(name):
    if re.match(r'^[A-Z]', name): return '工具'
    if any(kw in name for kw in ['算法','方法','模型','方式','策略','框架']): return '方法'
    if any(kw in name for kw in ['系统','工具','库','平台']): return '工具'
    if any(kw in name for kw in ['推理','学习','抽取','挖掘','搜索','融合','预测','嵌入']): return '技术'
    if any(kw in name for kw in ['理论','逻辑','原理']) or name.endswith('论'): return '理论'
    if any(kw in name for kw in ['评价','实验','分类','任务']): return '任务'
    return '概念'

def find_def(text, entity, max_len=300):
    """严格找完整定义句子（扩充上下文）"""
    sents = re.split(r'(?<=[。！？])\s*', text)
    
    def is_good_def(sent):
        """判断句子是否像真正的定义"""
        # 太短不算
        if len(sent) < 15: return False
        # 含有"详细介绍""详见"这类引用不算
        if any(p in sent for p in ['详细介绍', '详见', '参见', '参考']): return False
        # 含有项目列表不算
        if 'DBpedia' in sent or 'WordNet' in sent or 'ConceptNet' in sent: return False
        return True
    
    # 1. 优先找定义模式句
    for i, sent in enumerate(sents):
        if entity not in sent: continue
        if not is_good_def(sent): continue
        if any(pat in sent for pat in ['是指','指的是','就是','定义为','表示','描述','称为','即','简称']):
            ctx = sent
            if i > 0: ctx = sents[i-1][-60:] + ctx
            if i+1 < len(sents) and len(ctx) < 200: ctx += sents[i+1]
            return ctx[:max_len]
    
    # 2. 找含"是"的判断句
    for i, sent in enumerate(sents):
        if entity not in sent: continue
        if not is_good_def(sent): continue
        if entity + '是' in sent or '是' + entity in sent:
            ctx = sent
            if i > 0: ctx = sents[i-1][-60:] + ctx
            if i+1 < len(sents) and len(ctx) < 200: ctx += sents[i+1]
            return ctx[:max_len]
    
    # 3. 取包含实体的完整句 + 前句（跳过质量差的）
    for i, sent in enumerate(sents):
        if entity not in sent: continue
        if not is_good_def(sent): continue
        if len(sent) >= 20:
            ctx = sent
            if i > 0: ctx = sents[i-1][-40:] + ctx
            return ctx[:max_len]
    
    # 4. 实在没有好的，返回第一个不含坏标记的
    for sent in sents:
        if entity in sent and len(sent) >= 20:
            if 'DBpedia' not in sent and '详细介绍' not in sent:
                return sent[:max_len]
    
    return ''

def find_para(text, entity, max_len=500):
    """找包含实体的完整段落"""
    paras = [p.strip() for p in text.split('\n') if p.strip() and len(p.strip()) >= 30]
    best = ''
    best_score = 0
    
    for para in paras:
        if entity not in para: continue
        score = 0
        if any(p in para[:300] for p in ['是指','指的是','定义为','表示','称为']): score += 5
        if entity == para[:len(entity)]: score += 3
        if 60 <= len(para) <= 400: score += 2
        if score > best_score: best_score, best = score, para
    
    if not best:
        for para in paras:
            if entity in para and len(para) > len(best): best = para
    
    if len(best) > max_len:
        cut = best[:max_len]
        lp = max(cut.rfind('。'), cut.rfind('.'))
        if lp > 30: best = cut[:lp+1]
    return best.strip()

def get_ch_text(n):
    s,e = CHAPTER_RANGES[n]
    return '\n'.join(book_lines[s:e])

v4_data = {}
for ch_num in range(1, 10):
    ch_text = get_ch_text(ch_num)
    for word, weight in chapter_entities[ch_num]:
        if word in v4_data: continue
        
        def_sent = find_def(ch_text, word)
        para = find_para(ch_text, word)
        
        v4_data[word] = {
            'name': word, 'chapter': CHAPTER_NAMES[ch_num], 'ch_num': ch_num,
            'weight': round(weight,4), 'definition': def_sent, 'definition_full': para,
            'explanation': '', 'category': classify_entity(word), 'related_entities': [],
        }
        s = 'OK' if def_sent else '--'
        print(f"  {s} [{ch_num}] {word}: {def_sent[:60] if def_sent else '无定义句'}")

# ── 5. 实体关联 ──
print("\n[5/5] 构建实体关联")

def build_rels(data):
    rels = set()
    full_text = '\n'.join(book_lines)
    
    for cn in range(1, 10):
        ch_ents = [e for e,d in data.items() if d['ch_num']==cn]
        ch_text = get_ch_text(cn)
        
        # 1) 段落共现
        paras = [p.strip() for p in ch_text.split('\n') if p.strip() and len(p)>50]
        co = Counter()
        for p in paras:
            f = [e for e in ch_ents if e in p]
            for i in range(len(f)):
                for j in range(i+1,len(f)):
                    co[tuple(sorted([f[i],f[j]]))] += 1
        
        for (e1,e2),c in co.items():
            if c >= 2:
                rels.add((e1, e2, '相关', min(c,5), cn))
        
        # 2) 跨章共现（全文中窗口内出现）
        if cn < 9:
            other_ents = [e for e,d in data.items() if d['ch_num']!=cn]
            sents = re.split(r'(?<=[。！？])\s*', ch_text)
            for sent in sents:
                cur = [e for e in ch_ents if e in sent]
                other = [e for e in other_ents if e in sent]
                if cur and other:
                    for c in cur:
                        for o in other[:2]:
                            rels.add((c, o, '关联', 1, cn))
    
    # 3) 全文中句子级别共现（任意章节之间）
    all_ents = list(data.keys())
    sents = re.split(r'(?<=[。！？])\s*', full_text)
    co_all = Counter()
    for sent in sents:
        found = [e for e in all_ents if e in sent]
        if len(found) >= 3:
            for i in range(len(found)):
                for j in range(i+1, len(found)):
                    co_all[tuple(sorted([found[i], found[j]]))] += 1
    
    for (e1,e2),c in co_all.items():
        if c >= 3:
            cn1 = data[e1]['ch_num']
            cn2 = data[e2]['ch_num']
            rels.add((e1, e2, '相关', min(c,5), cn1 if cn1==cn2 else 0))
    
    # 写入 data
    for e1, e2, rtype, strength, cn in rels:
        data[e1]['related_entities'].append({'name': e2, 'type': rtype, 'strength': strength})
        data[e2]['related_entities'].append({'name': e1, 'type': rtype, 'strength': strength})
    
    return list(rels)

rels = build_rels(v4_data)
rc = sum(1 for v in v4_data.values() if v['related_entities'])
print(f"  关系: {len(rels)} 条, {rc}/{len(v4_data)} 实体有关联")

# ── 保存 ──
with open(OUTPUT_ENRICHED,'w',encoding='utf-8') as f:
    json.dump(v4_data,f,ensure_ascii=False,indent=2)
print(f"\nOK 保存: {OUTPUT_ENRICHED} ({len(v4_data)} 实体)")

# ── 6. HTML ──
print("\n生成 HTML...")

el = list(v4_data.values())
data_json = json.dumps(el, ensure_ascii=False)

html_template = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>知识图谱 V4 - 词频精准提取</title>
<script src="https://unpkg.com/vis-network@9.1.6/standalone/umd/vis-network.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Microsoft YaHei',sans-serif;background:#f0f2f5;height:100vh;overflow:hidden}
#header{background:linear-gradient(135deg,#4A90D9,#2E5A8A);color:#fff;padding:12px 24px;display:flex;align-items:center;justify-content:space-between}
#header h1{font-size:18px;font-weight:600}
#main{display:flex;height:calc(100vh - 52px)}
#graph-container{flex:1;background:#fff;position:relative}
#graph{width:100%;height:100%}
#sidebar{width:420px;background:#fff;border-left:1px solid #e0e0e0;display:flex;flex-direction:column}
#sidebar-header{padding:14px 16px;border-bottom:1px solid #eee;font-weight:bold;font-size:14px;color:#333;display:flex;justify-content:space-between;align-items:center}
#sidebar-header a{color:#4A90D9;cursor:pointer;font-size:12px;text-decoration:none}
#sidebar-content{flex:1;padding:16px;overflow-y:auto}
#empty{color:#999;text-align:center;padding:60px 20px;font-size:14px;line-height:2}
.entity-header{margin-bottom:12px}
.entity-header .name{font-size:20px;font-weight:bold;color:#2c3e50}
.entity-header .meta{font-size:12px;color:#888;margin-top:4px}
.section-card{background:#f8fafb;border-radius:8px;padding:12px 14px;margin-bottom:10px}
.section-card .label{font-size:11px;font-weight:bold;margin-bottom:6px}
.section-card .text{font-size:13px;color:#333;line-height:1.8}
.def-def{border-left:3px solid #50C878}
.def-para{border-left:3px solid #4A90D9}
.related-list{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}
.related-chip{display:inline-flex;padding:4px 10px;border-radius:14px;font-size:12px;cursor:pointer;background:#f0f0f0;color:#555}
.related-chip:hover{background:#E3F2FD;color:#1565C0;transform:scale(1.05)}
.search-box{padding:10px 16px;border-bottom:1px solid #eee}
.search-box input{width:100%;padding:6px 10px;border:1px solid #ddd;border-radius:5px;font-size:12px;outline:none}
.search-box input:focus{border-color:#4A90D9}
#controls{position:absolute;top:12px;right:12px;z-index:10;display:flex;gap:6px}
#controls button{padding:6px 14px;border:1px solid #ccc;background:#fff;border-radius:6px;cursor:pointer;font-size:12px}
#controls button:hover{background:#f0f4ff;border-color:#4A90D9}
#controls button.active{background:#4A90D9;color:#fff;border-color:#4A90D9}
.legend{position:absolute;bottom:16px;left:16px;z-index:10;background:rgba(255,255,255,.95);padding:10px 14px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.12);font-size:12px}
.wt{display:inline-block;font-size:10px;padding:1px 6px;border-radius:4px;background:#E8F5E9;color:#2E7D32;margin-left:6px}
</style>
</head>
<body>
<div id="header">
  <h1>知识图谱 方法、实践与应用 (V4 · 词频精准提取)</h1>
  <div style="font-size:13px;opacity:.85"><span id="stats"></span></div>
</div>
<div id="main">
  <div id="graph-container">
    <div id="graph"></div>
    <div id="controls">
      <button id="btnTree" class="active" onclick="setLayout('hierarchical')">树形</button>
      <button id="btnNet" onclick="setLayout('network')">网状</button>
      <button onclick="fitAll()">适应</button>
    </div>
    <div class="legend">
      <span><span style="display:inline-block;width:12px;height:12px;background:#4A90D9;border-radius:2px"></span> 章</span>
      <span style="margin-left:8px"><span style="display:inline-block;width:12px;height:12px;background:#fff8e1;border:1px solid #FF8C42;border-radius:2px"></span> 概念</span>
    </div>
  </div>
  <div id="sidebar">
    <div id="sidebar-header">
      <span>知识点详情</span>
      <a onclick="clearSelection()">清除</a>
    </div>
    <div class="search-box">
      <input type="text" id="searchInput" placeholder="搜索概念..." oninput="searchNodes(this.value)">
    </div>
    <div id="sidebar-content">
      <div id="empty">
        点击图中的概念节点<br>
        查看完整定义句 + 原文段落 + 关联概念<br>
        <small>节点大小 = 词频权重 | [1]树形 [2]网状 [F]适应</small>
      </div>
      <div id="detail" style="display:none"></div>
      <div id="searchResults" style="display:none"></div>
    </div>
  </div>
</div>
<script>
const ENTITIES = __DATA_JSON__;

function renderDetail(e){
  var h='<div class="entity-header"><div class="name">'+e.name+'<span class="wt">'+e.weight+'</span></div>';
  h+='<div class="meta">'+e.chapter+' | '+e.category+'</div></div>';
  if(e.definition) h+='<div class="section-card def-def"><div class="label">[定义句]</div><div class="text">'+e.definition+'</div></div>';
  if(e.definition_full) h+='<div class="section-card def-para"><div class="label">[原文段落]</div><div class="text">'+e.definition_full+'</div></div>';
  if(e.related_entities&&e.related_entities.length>0){
    h+='<div class="section-card" style="border-left:3px solid #9B59B6"><div class="label">[关联概念] ('+e.related_entities.length+')</div><div class="related-list">';
    e.related_entities.forEach(function(r){h+='<span class="related-chip" onclick="focusEntity(\''+r.name+'\')">'+r.name+'</span>';});
    h+='</div></div>';
  }
  return h;
}

function ge(name){return ENTITIES.find(function(e){return e.name===name;});}
function fe(name){sn(name);}

function sn(q){
  var det=document.getElementById('detail'),emp=document.getElementById('empty'),res=document.getElementById('searchResults');
  if(typeof q!=='string'){
    var nid=q;
    emp.style.display='none';res.style.display='none';det.style.display='block';
    var e=null;
    if(typeof nid==='string'&&nid.startsWith('ent_')) e=ge(decodeURIComponent(nid.substring(4)));
    else if(typeof nid==='string') e=ge(nid);
    if(!e) e=ge(nid);
    if(!e){var nd=nodesData.get(nid);if(nd){det.innerHTML='<div class="entity-header"><div class="name">'+(nd.fullLabel||nd.label)+'</div></div>';return;}det.innerHTML='<div style="color:#999">未找到</div>';return;}
    det.innerHTML=renderDetail(e);return;
  }
  if(!q.trim()){res.style.display='none';if(det.style.display!='block')emp.style.display='block';return;}
  var qt=q.toLowerCase();
  var ms=ENTITIES.filter(function(e){return e.name.toLowerCase().includes(qt)||(e.definition||'').toLowerCase().includes(qt);}).slice(0,30);
  emp.style.display='none';det.style.display='none';res.style.display='block';
  if(ms.length===0){res.innerHTML='<div style="color:#999;padding:20px;text-align:center">未找到匹配</div>';return;}
  var h='<div style="font-size:13px;color:#555;margin-bottom:8px">找到 '+ms.length+' 个：</div>';
  ms.forEach(function(e){h+='<span class="related-chip" onclick="showNodeDetail(\''+e.name+'\')" style="margin:3px;padding:6px 12px">'+e.name+' <small style="color:#999">['+e.category+']</small></span>';});
  res.innerHTML=h;
}

function showNodeDetail(q){sn(q);}

function cs(){
  document.getElementById('detail').style.display='none';
  document.getElementById('empty').style.display='block';
  document.getElementById('searchResults').style.display='none';
  document.getElementById('searchInput').value='';
  if(network) network.selectNodes([],false);
}

function clearSelection(){cs();}

// vis-network
var nodes=[],edges=[],chGroups={},added=new Set();
var cNames=['知识图谱概述','知识图谱表示与建模','知识存储','知识抽取与挖掘','知识图谱融合','知识图谱推理','语义搜索','知识问答','应用案例'];
var cCols=['#4A90D9','#50C878','#FF8C42','#9B59B6','#E74C3C','#1ABC9C','#F39C12','#3498DB','#2ECC71'];

for(var n=1;n<=9;n++){
  var cid='ch_'+n;
  chGroups[n]=cid;
  nodes.push({id:cid,label:cNames[n-1],group:'chapter',color:{background:cCols[n-1],border:'#fff'},font:{color:'#fff',size:16,face:'Microsoft YaHei',bold:true},shape:'box'});
  if(n>1) edges.push({from:'ch_'+(n-1),to:cid,arrows:{to:{enabled:true,scaleFactor:0.5}},color:'#aaa',width:2,dashes:true});
}

ENTITIES.forEach(function(e){
  if(added.has(e.name)) return;
  added.add(e.name);
  var nid='ent_'+encodeURIComponent(e.name),pid=chGroups[e.ch_num]||'ch_'+e.ch_num;
  var sz=Math.min(28,Math.max(10,e.weight*80));
  nodes.push({id:nid,label:e.name.length>12?e.name.substring(0,12)+'..':e.name,fullLabel:e.name,group:'entity',color:{background:'#fff8e1',border:'#FF8C42'},font:{color:'#e65100',size:11,face:'Microsoft YaHei'},shape:'dot',size:sz});
  edges.push({from:pid,to:nid,color:'#ddd',width:0.8,dashes:true});
});

var nd=new vis.DataSet(nodes),ed=new vis.DataSet(edges);
var bo={physics:{solver:'barnesHut',barnesHut:{gravitationalConstant:-5000,centralGravity:0.2,springLength:180,springConstant:0.03},stabilization:{iterations:200}},interaction:{hover:true,hoverConnectedEdges:true,tooltipDelay:200},edges:{smooth:{type:'continuous'}}};
var ho=Object.assign({},bo,{layout:{hierarchical:{enabled:true,direction:'LR',sortMethod:'directed',levelSeparation:280,nodeSpacing:120,treeSpacing:160}},physics:false});
var no=Object.assign({},bo,{layout:{}});
var cl='hierarchical',network=null;

function init(){
  var c=document.getElementById('graph');
  network=new vis.Network(c,{nodes:nd,edges:ed},ho);
  network.on('click',function(p){
    if(p.nodes.length>0){
      var nid=p.nodes[0];
      if(nid.startsWith('ent_')){var e=ge(decodeURIComponent(nid.substring(4)));if(e){sn(e.name);document.getElementById('stats').innerHTML=ENTITIES.length+' 概念';return;}}
      sn(nid);
    }else cs();
  });
  document.getElementById('stats').innerHTML=ENTITIES.length+' 概念 | '+edges.length+' 关联';
}

function setLayout(m){if(m===cl)return;cl=m;document.getElementById('btnTree').className=m==='hierarchical'?'active':'';document.getElementById('btnNet').className=m==='network'?'active':'';network.setOptions(m==='hierarchical'?ho:no);if(m==='network'){network.setOptions({physics:true});setTimeout(function(){network.stopSimulation();},3000);}}
function fitAll(){network.fit({animation:true});}

init();
</script>
</body>
</html>'''

with open(OUTPUT_HTML,'w',encoding='utf-8') as f:
    f.write(html_template.replace('__DATA_JSON__', data_json))

print(f"\nOK HTML: {OUTPUT_HTML} ({len(el)} 实体)")
print("\n"+"="*60)
print(f"完成! 实体:{len(v4_data)} 关系:{len(rels)} 定义句:{sum(1 for v in v4_data.values() if v['definition'])} 段落:{sum(1 for v in v4_data.values() if v['definition_full'])}")
print("="*60)