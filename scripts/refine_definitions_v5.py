"""
改进的定义提取 Pipeline：指示词匹配 + 近距打分 + 上下文窗口
===========================================================
核心逻辑（按你的要求）：
1. 指示词匹配：中文"是、称为、指的是、即、定义为、是指"
              英文"is、refers to、means、is defined as、called"
2. 近距打分：多候选时选离概念首次出现最近的句子
3. 上下文窗口法：定位概念出现的句子，取整段作为定义候选
4. 原文段落准确引用
"""
import json, re, sys, os
from collections import defaultdict

# ============================================================
# 配置
# ============================================================
JSON_FILE = r'e:\nlp\ltp\kg_entity_v5_summarized.json'
BOOK_FILE = r'e:\nlp\ltp\kg_book_full.txt'
OUTPUT_JSON = r'e:\nlp\ltp\kg_entity_v5_refined.json'
OUTPUT_HTML = r'e:\nlp\ltp\kg_book_interactive_v5.html'

SKIP_LLM = True  # 设为True跳过LLM摘要重生成（仅做定义/段落提取）

# ============================================================
# 定义指示词（按优先级排列，越靠前权重越高）
# ============================================================
INDICATORS_ZH = [
    '是指',     # 最高优先级
    '指的是',
    '定义为',
    '即',
    '称为',
    '就是',
    '是',       # "X是Y"结构
    '表示',
    '描述',
    '简称',
]

INDICATORS_EN = [
    'is defined as',
    'refers to',
    'is',
    'means',
    'called',
    'refers',
]

def get_indicator_score(sent):
    """返回 (优先级分, 匹配到的指示词)"""
    for score, ind in enumerate(reversed(INDICATORS_ZH)):
        if ind in sent:
            return (len(INDICATORS_ZH) - score, ind)
    for score, ind in enumerate(reversed(INDICATORS_EN)):
        if ind.lower() in sent.lower():
            return (len(INDICATORS_EN) - score, ind)
    return (0, None)


# ============================================================
# 改进的定义提取
# ============================================================
def split_sentences(text):
    """切句子，保留标点"""
    sents = re.split(r'(?<=[。！？；\n])\s*', text)
    return [s.strip() for s in sents if len(s.strip()) > 5]

def extract_definition_v2(ch_text, entity, max_len=400):
    """
    自动术语定义识别 Pipeline（V2改进版）:
    1. 定位概念出现的所有句子
    2. 用指示词匹配找定义句
    3. 按近距 + 模式质量打分
    4. 返回最佳定义句及其前后上下文
    """
    if entity not in ch_text:
        return ''
    
    sents = split_sentences(ch_text)
    
    # 概念首次出现位置（在整个ch_text中的字符偏移）
    first_pos = ch_text.find(entity)
    
    candidates = []  # [(total_score, sent_idx, sent_text, indicator)]
    
    for i, sent in enumerate(sents):
        if entity not in sent:
            continue
        
        # 句子的字符偏移
        sent_pos = ch_text.find(sent)
        if sent_pos < 0:
            continue
        
        # 距首次出现的距离（越近越好）
        distance = abs(sent_pos - first_pos)
        
        # 指示词匹配
        ind_score, indicator = get_indicator_score(sent)
        
        if ind_score > 0:
            # 总分 = 指示词权重 * 500 - 距离 * 0.5
            total = ind_score * 500 - distance * 0.5
            candidates.append((total, i, sent, indicator))
    
    # 按总分排序
    candidates.sort(key=lambda x: -x[0])
    
    if candidates:
        best_idx = candidates[0][1]
        best_sent = candidates[0][2]
        
        # 上下文窗口：取前后各一句 + 当前句
        ctx_parts = []
        if best_idx > 0:
            ctx_parts.append(sents[best_idx - 1][-80:])
        ctx_parts.append(best_sent)
        if best_idx + 1 < len(sents):
            next_sent = sents[best_idx + 1]
            # 只取当前句的后半段（不超过200字）
            ctx_parts.append(next_sent[:200])
        
        ctx = ''.join(ctx_parts)
        # 仅折叠多余空行，保留单空格和换行
        ctx = re.sub(r'\n{3,}', '\n\n', ctx)
        # 去掉上下文中的"图X-X"、"表X-X"等噪声
        ctx = re.sub(r'^(图\d+[-–—]\d+.*?[。；\n])', '', ctx)
        ctx = re.sub(r'^(表\d+[-–—]\d+.*?[。；\n])', '', ctx)
        # 去掉以 "X.X" 开头的残篇（仅限开头40字内的章节编号前缀，不过度匹配）
        ctx = re.sub(r'^\d+(\.\d+)+\s*\S{1,40}\n', '', ctx)
        return ctx[:max_len]
    
    # ---------- 降级策略 ----------
    # 包含"X是"判断句
    for i, sent in enumerate(sents):
        if entity in sent and entity + '是' in sent:
            ctx = re.sub(r'\n{3,}', '\n\n', sent)
            return ctx[:max_len]
    
    # 包含实体的完整句（长度适中）
    for sent in sents:
        if entity in sent and 20 <= len(sent) <= 400:
            ctx = re.sub(r'\n{3,}', '\n\n', sent)
            return ctx[:max_len]
    
    return ''


# ============================================================
# 改进的段落提取：找实体所在的文本段落
# ============================================================
def extract_paragraph_v2(ch_text, entity, max_len=800):
    """
    上下文窗口法提取完整段落：
    1. 定位实体在全文中的位置
    2. 向前找到段落起始（双换行或章节标题前面）
    3. 向后找到段落结束
    4. 返回完整段落
    """
    if entity not in ch_text:
        return ''
    
    pos = ch_text.find(entity)
    
    # 向前找段落起始（双换行前面或章节标题后面）
    # 看pos之前的文本，找最近的 \n\n
    before = ch_text[:pos]
    
    para_start = 0
    # 先找双换行
    dnl = before.rfind('\n\n')
    if dnl >= 0:
        para_start = dnl + 2
    else:
        # 不行就找章节标题格式（X.X.X）
        sec_match = list(re.finditer(r'\d+\.\d+\.\d+\s+\S', before))
        if sec_match:
            para_start = sec_match[-1].start()
    
    # 向后找段落结束（找段落结尾标记之后的位置）
    after = ch_text[pos:]
    
    # 找段落结尾（双换行或章节标题）
    para_end = len(ch_text)
    dnl = after.find('\n\n')
    if dnl >= 0 and dnl < 800:
        para_end = pos + dnl
    
    # 找下一个小节标题
    next_sec = re.search(r'\d+\.\d+\.\d+\s+\S', after)
    if next_sec and next_sec.start() < 800:
        para_end = min(para_end, pos + next_sec.start())
    
    paragraph = ch_text[para_start:para_end].strip()
    
    # 如果段落太长，从pos前后截取
    if len(paragraph) > max_len:
        start = max(0, pos - para_start - 200)
        end = min(len(paragraph), pos - para_start + 500)
        paragraph = paragraph[start:end]
    
    # 清理多余空白
    paragraph = re.sub(r' +\n', '\n', paragraph)
    paragraph = re.sub(r'\n{3,}', '\n\n', paragraph)
    
    return paragraph[:max_len]


# ============================================================
# 主流程
# ============================================================
print("=" * 60)
print("定义提取改进 Pipeline")
print("=" * 60)

# 读取数据
print("\n[1] 读取 JSON 和全书文本...")
with open(JSON_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

with open(BOOK_FILE, 'r', encoding='utf-8') as f:
    full_text = f.read()

print(f"  实体: {len(data)}")
print(f"  全书: {len(full_text)} 字符")

# 文本按章节分割
def split_chapters(text):
    lines = text.split('\n')
    chapters = {}
    current_ch = None
    ch_map = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}
    CH_PAT = re.compile(r'第([一二三四五六七八九十\d+])章')
    
    for i, line in enumerate(lines):
        m = CH_PAT.match(line.lstrip('\ufeff').strip())
        if m:
            cn = ch_map.get(m.group(1)) or int(m.group(1))
            if current_ch is not None:
                chapters[current_ch] = '\n'.join(chapter_lines)
            current_ch = cn
            chapter_lines = [line]
        elif current_ch is not None:
            chapter_lines.append(line)
    if current_ch is not None:
        chapters[current_ch] = '\n'.join(chapter_lines)
    return chapters

chapters = split_chapters(full_text)
print(f"  章节: {sorted(chapters.keys())}")

# 为每个实体重新提取定义和段落
print("\n[2] 重新提取定义和段落（指示词 + 近距打分 + 上下文窗口）...")

stats = {'def_improved': 0, 'para_improved': 0, 'def_ok': 0, 'def_empty_kept': 0}
changed_entities = set()

for i, (name, info) in enumerate(data.items()):
    ch_num = info.get('ch_num', 1)
    ch_text = chapters.get(ch_num, full_text)
    
    old_def = info.get('definition', '')
    old_para = info.get('paragraph', '')
    
    # 提取新定义
    new_def = extract_definition_v2(ch_text, name)
    
    # 提取新段落
    new_para = extract_paragraph_v2(ch_text, name)
    
    # 更新定义
    if new_def and len(new_def) > 20:
        should_replace = False
        if not old_def or old_def == '(暂无定义)':
            should_replace = True
        elif len(new_def) < len(old_def) * 0.6 and len(new_def) >= 20:
            should_replace = True
        elif len(old_def) > 300:
            should_replace = True
        if should_replace:
            data[name]['definition'] = new_def
            changed_entities.add(name)
        stats['def_ok'] += 1
    elif old_def:
        stats['def_ok'] += 1
    else:
        stats['def_empty_kept'] += 1
    
    # 更新段落
    if new_para and len(new_para) > 30:
        if not old_para or old_para == '(暂无段落)' or len(new_para) > len(old_para):
            data[name]['paragraph'] = new_para
            changed_entities.add(name)
            stats['para_improved'] += 1
    
    if (i+1) % 30 == 0:
        print(f"  进度: {i+1}/{len(data)}")

stats['def_improved'] = sum(1 for n in changed_entities if n in data)

print(f"\n  统计:")
print(f"    定义 OK: {stats['def_ok']}  (改进: {stats['def_improved']})")
print(f"    段落改进: {stats['para_improved']}")
print(f"    定义仍空: {stats['def_empty_kept']}")

# 更新 summary（只重新生成有变化的实体）
if not SKIP_LLM:
    print("\n[3] 用新定义更新 LLM 摘要（仅变更实体）...")
    import requests
    OLLAMA_URL = 'http://localhost:11434/api/generate'
    LLM_MODEL = 'qwen2.5:3b'
    
    def llm_summarize(entity, definition, paragraph):
        ctx = definition if len(definition) > 20 else paragraph
        if not ctx or len(ctx) < 15:
            return ''
        ctx = re.sub(r'\n{3,}', '\n\n', ctx).strip()[:400]
        
        prompt = f"""请用通俗易懂的语言，用一句话解释什么是"{entity}"。

原文参考：{ctx}

要求：
1. 基于原文准确概括
2. 通俗易懂
3. 50-100字

解释："""
        try:
            r = requests.post(OLLAMA_URL, json={
                'model': LLM_MODEL,
                'prompt': prompt,
                'stream': False,
            }, timeout=10)
            resp = r.json().get('response', '').strip()
            return resp.strip('"').strip("'").strip()[:200]
        except:
            return ''
    
    update_count = 0
    total_changed = len(changed_entities)
    for i, name in enumerate(changed_entities):
        info = data[name]
        definition = info.get('definition', '')
        paragraph = info.get('paragraph', '')
        old_summary = info.get('summary', '')
        
        if definition and len(definition) > 30:
            new_summary = llm_summarize(name, definition, paragraph)
            if new_summary and len(new_summary) > 10:
                data[name]['summary'] = new_summary
                update_count += 1
        
        if (i+1) % 20 == 0 or i == total_changed - 1:
            print(f"  摘要更新: {update_count}/{i+1}")
    
    print(f"  摘要更新: {update_count}")
else:
    print("\n[3] 跳过 LLM 摘要重生成（SKIP_LLM=True）")


# ============================================================
# 保存 JSON
# ============================================================
print("\n[4] 保存 JSON...")
with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"  {OUTPUT_JSON} ({len(data)} 实体)")


# ============================================================
# 重新生成 HTML（保留概念解释版的设计）
# ============================================================
print("\n[5] 再生 HTML...")

html = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>知识图谱 V5 - 精确引用版</title>
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
#detail-panel { position: absolute; right: 20px; top: 20px; width: 420px; max-height: calc(100vh - 120px); background: #fff; border-radius: 10px; box-shadow: 0 4px 24px rgba(0,0,0,0.18); padding: 0; overflow: hidden; display: none; z-index: 10; flex-direction: column; }
#detail-panel .dp-header { background: linear-gradient(135deg, #1a237e, #3949ab); color: #fff; padding: 14px 16px; position: relative; }
#detail-panel .dp-header h3 { font-size: 16px; font-weight: 600; margin: 0; }
#detail-panel .dp-header .meta { font-size: 11px; opacity: 0.8; margin-top: 3px; }
#detail-panel .close-btn { position: absolute; right: 12px; top: 12px; cursor: pointer; font-size: 20px; opacity: 0.7; }
#detail-panel .close-btn:hover { opacity: 1; }
#detail-content { padding: 16px; overflow-y: auto; max-height: calc(100vh - 220px); }
.dp-section { margin-bottom: 14px; }
.dp-section h4 { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
.dp-section .summary-text { font-size: 15px; color: #1a237e; line-height: 1.7; font-weight: 500; background: #e8eaf6; padding: 10px 14px; border-radius: 8px; border-left: 3px solid #3949ab; }
.dp-section .raw-text { font-size: 13px; color: #444; line-height: 1.6; background: #f5f5f5; padding: 10px 14px; border-radius: 6px; white-space: pre-wrap; }
.dp-section .citation { font-size: 12px; color: #888; margin-top: 2px; font-style: italic; }
.dp-section .rels { font-size: 12px; color: #555; line-height: 1.8; }
.dp-section .rels a { color: #1565c0; cursor: pointer; text-decoration: underline; }
#legend { position: absolute; left: 20px; bottom: 20px; background: rgba(255,255,255,0.95); border-radius: 8px; padding: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); font-size: 12px; z-index: 10; }
#legend .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px; }
#legend .row { margin-bottom: 3px; }
</style>
</head>
<body>

<div id="header">
  <h1>知识图谱：方法、实践与应用</h1>
  <p>V5 精确引用 · <span id="stats-text"></span></p>
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
      <div class="dp-header">
        <span class="close-btn" onclick="closeDetail()">&times;</span>
        <h3 id="dp-title"></h3>
        <div class="meta" id="dp-meta"></div>
      </div>
      <div id="detail-content"></div>
    </div>
  </div>
</div>

<script>
const DATA = ''' + json.dumps(data, ensure_ascii=False) + r''';

const chapters = {};
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

let network = null;

function showChapter(ch) {
    document.querySelectorAll('.ch-tab').forEach(t => t.classList.remove('active'));
    const tabs = document.querySelectorAll('.ch-tab');
    const chKeys = Object.keys(chapters).sort((a,b)=>a-b);
    const idx = chKeys.indexOf(String(ch));
    if (idx >= 0) tabs[idx].classList.add('active');
    
    const names = chapters[ch] || [];
    const listEl = document.getElementById('entity-list');
    listEl.innerHTML = '';
    
    names.sort((a,b) => {
        const da = DATA[a], db = DATA[b];
        if (da.is_section_title && !db.is_section_title) return -1;
        if (!da.is_section_title && db.is_section_title) return 1;
        return db.weight - da.weight;
    });
    
    names.forEach((name, idx) => {
        const d = DATA[name];
        const item = document.createElement('div');
        item.className = 'entity-item';
        const preview = d.summary ? d.summary.slice(0, 50) + (d.summary.length > 50 ? '...' : '') : '';
        item.innerHTML = `<strong>${name}</strong> <span class="badge">${(d.weight*1000).toFixed(0)}</span><br><small style="color:#999;">${preview}</small>`;
        item.onclick = () => { showEntity(name); highlightNode(name); };
        item.dataset.index = idx;
        listEl.appendChild(item);
    });
    
    buildGraph(ch);
}

function showEntity(name) {
    const d = DATA[name];
    if (!d) return;
    document.querySelectorAll('.entity-item').forEach(e => e.classList.remove('selected'));
    // 遍历所有 entity-item，将文本匹配的标为 selected
    const items = document.querySelectorAll('.entity-item');
    for (const item of items) {
        if (item.querySelector('strong')?.textContent === name) {
            item.classList.add('selected');
            break;
        }
    }
    
    document.getElementById('dp-title').textContent = (d.is_section_title ? '📌 ' : '') + name;
    document.getElementById('dp-meta').textContent = `第${d.ch_num}章 · 权重 ${(d.weight*1000).toFixed(0)}${d.is_section_title ? ' · 章节标题' : ''}`;
    
    let html = '';
    
    // [1] 概念解释（LLM摘要）
    if (d.summary) {
        html += `<div class="dp-section"><h4>理解</h4><div class="summary-text">${d.summary}</div></div>`;
    }
    
    // [2] 书中准确引用（定义句）
    if (d.definition && d.definition !== '(暂无定义)') {
        html += `<div class="dp-section"><h4>书中定义 <span class="citation">(原文引用)</span></h4><div class="raw-text">${d.definition}</div></div>`;
    }
    
    // [3] 原文段落
    if (d.paragraph && d.paragraph !== '(暂无段落)') {
        html += `<div class="dp-section"><h4>原文段落 <span class="citation">(上下文窗口)</span></h4><div class="raw-text">${d.paragraph}</div></div>`;
    }
    
    // [4] 关联实体
    if (d.related_entities && d.related_entities.length > 0) {
        html += `<div class="dp-section"><h4>关联实体 (${d.related_entities.length})</h4><div class="rels">`;
        d.related_entities.slice(0, 20).forEach(r => {
            const encoded = encodeURIComponent(r.name);
            html += `<a data-entity="${encoded}" onclick="showEntity(decodeURIComponent(this.dataset.entity));highlightNode(decodeURIComponent(this.dataset.entity))">${r.name}</a> (${r.type})<br>`;
        });
        if (d.related_entities.length > 20) {
            html += `<small>…共${d.related_entities.length}个关联</small>`;
        }
        html += `</div></div>`;
    }
    
    document.getElementById('detail-content').innerHTML = html;
    document.getElementById('detail-panel').style.display = 'flex';
}

function closeDetail() {
    document.getElementById('detail-panel').style.display = 'none';
}

function buildGraph(ch) {
    const names = chapters[ch] || [];
    const nodes = [];
    const edges = [];
    const nodeSet = new Set(names);
    
    names.forEach(name => {
        const d = DATA[name];
        if (d.related_entities) {
            d.related_entities.forEach(r => {
                if (DATA[r.name]) nodeSet.add(r.name);
            });
        }
    });
    
    Array.from(nodeSet).forEach(name => {
        const d = DATA[name] || {ch_num:ch, is_section_title:false, weight:0};
        const isInChapter = d.ch_num === ch;
        nodes.push({
            id: name,
            label: name.length > 12 ? name.slice(0, 10) + '…' : name,
            title: d.summary || d.definition || '',
            size: Math.max(12, Math.min(35, (d.weight*1000) * 3 + (d.is_section_title ? 8 : 0))),
            color: d.is_section_title ? {background:'#e53935', border:'#b71c1c'} : 
                   isInChapter ? {background:'#1565c0', border:'#0d47a1'} : 
                   {background:'#78909c', border:'#546e7a'},
            font: {size: d.is_section_title ? 15 : 13, face:'Microsoft YaHei'},
            borderWidth: d.is_section_title ? 3 : 1,
            opacity: isInChapter ? 1.0 : 0.6,
        });
    });
    
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

print(f"\n[6] 完成!")
print(f"  JSON: {OUTPUT_JSON}")
print(f"  HTML: {OUTPUT_HTML}")
print("=" * 60)