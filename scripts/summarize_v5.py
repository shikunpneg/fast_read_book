"""
V5 概念摘要生成器
=================
为每个实体生成通俗易懂的概念解释。
基于书中定义 + 原文段落 → LLM 生成简洁概括。
"""
import json, re, sys, time
import requests

# ============================================================
# 配置
# ============================================================
JSON_FILE = r'e:\nlp\ltp\kg_entity_v5.json'
BOOK_FILE = r'e:\nlp\ltp\kg_book_full.txt'
OUTPUT_JSON = r'e:\nlp\ltp\kg_entity_v5_summarized.json'
OUTPUT_HTML = r'e:\nlp\ltp\kg_book_interactive_v5.html'

OLLAMA_URL = 'http://localhost:11434/api/generate'
LLM_MODEL = 'qwen2.5:3b'

# ============================================================
# 读取
# ============================================================
print("读取 JSON 和全书文本...")
with open(JSON_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

with open(BOOK_FILE, 'r', encoding='utf-8') as f:
    full_text = f.read()

print(f"  JSON: {len(data)} 实体")
print(f"  全书: {len(full_text)} 字符")

# ============================================================
# 对每章分段落（改善段落提取）
# ============================================================
def split_chapters(text):
    """将全书按章节分割"""
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

def extract_context(ch_text, entity, window=400):
    """找实体在原文中的上下文窗口"""
    if entity not in ch_text:
        return ''
    pos = ch_text.find(entity)
    start = max(0, pos - window)
    end = min(len(ch_text), pos + window + 200)
    return ch_text[start:end]

def extract_paragraphs_robust(ch_text, entity, max_chars=600):
    """提取包含实体的完整段落（改进版）"""
    paras = re.split(r'\n\s*\n', ch_text)
    good_paras = []
    for para in paras:
        para = para.strip()
        if entity in para and len(para) >= 30:
            good_paras.append(para)
    
    if not good_paras:
        # 降级：找包含实体的连续行
        lines = ch_text.split('\n')
        for i, line in enumerate(lines):
            if entity in line and len(line) >= 20:
                # 取前后行
                start = max(0, i-1)
                end = min(len(lines), i+3)
                para = '\n'.join(lines[start:end]).strip()
                if len(para) >= 30:
                    good_paras.append(para)
    
    if not good_paras:
        return ''
    
    # 选最长的（最完整）
    best = max(good_paras, key=len)
    if len(best) > max_chars:
        pos = best.find(entity)
        s = max(0, pos - 200)
        e = min(len(best), pos + 400)
        best = best[s:e]
    return best


# ============================================================
# LLM 生成摘要
# ============================================================
print("\nLLM 为实体生成概念解释...")
sys.stdout.flush()

def llm_summarize(entity, definition, paragraph):
    """用 LLM 生成实体概念的通俗解释"""
    ctx = definition if len(definition) > 20 else paragraph
    if not ctx or ctx == '(暂无定义)' or ctx == '(暂无段落)':
        ctx = ''
    
    if not ctx:
        return ''
    
    # 清理上下文中的噪声
    ctx = re.sub(r'\s+', '', ctx)[:400]
    
    prompt = f"""请用一句话（50-100字）通俗地解释什么是"{entity}"。

参考上下文：{ctx}

要求：
1. 用通俗易懂的语言
2. 抓住核心定义
3. 50-100字左右

解释："""
    
    try:
        r = requests.post(OLLAMA_URL, json={
            'model': LLM_MODEL,
            'prompt': prompt,
            'stream': False,
        }, timeout=30)
        resp = r.json().get('response', '').strip()
        # 去掉可能的引号
        resp = resp.strip('"').strip("'").strip()
        return resp[:200]
    except:
        return ''


summary_count = 0
skip_count = 0

for i, (name, info) in enumerate(data.items()):
    ch_num = info.get('ch_num', 1)
    definition = info.get('definition', '')
    paragraph = info.get('paragraph', '')
    
    # 改进段落提取（如果当前段落是空的或太短）
    if not paragraph or paragraph == '(暂无段落)' or len(paragraph) < 30:
        ch_text = chapters.get(ch_num, '')
        if ch_text:
            new_para = extract_paragraphs_robust(ch_text, name)
            if new_para:
                paragraph = new_para
                data[name]['paragraph'] = new_para
    
    # 改进定义提取（如果太短或没有）
    if not definition or definition == '(暂无定义)' or len(definition) < 20:
        if paragraph and len(paragraph) > len(definition):
            # 用段落前200字作为定义
            data[name]['definition'] = paragraph[:300]
            definition = paragraph[:300]
        else:
            ch_text = chapters.get(ch_num, '')
            ctx = extract_context(ch_text, name, 300)
            if ctx:
                data[name]['definition'] = ctx[:300]
                definition = ctx[:300]
    
    # 生成摘要
    summary = llm_summarize(name, definition, paragraph)
    if summary:
        data[name]['summary'] = summary
        summary_count += 1
    else:
        data[name]['summary'] = ''
        skip_count += 1
    
    if (i+1) % 10 == 0 or i == len(data)-1:
        print(f"  {i+1}/{len(data)} (已生成:{summary_count} 跳过:{skip_count})")
        sys.stdout.flush()

print(f"\n完成: {summary_count} 实体有摘要, {skip_count} 跳过")


# ============================================================
# 更新 JSON
# ============================================================
with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"JSON: {OUTPUT_JSON}")


# ============================================================
# 重新生成 HTML（核心修改：突出显示概念解释）
# ============================================================
print("\n重新生成 HTML（突出概念解释）...")

html = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>知识图谱 V5 - 概念解释版</title>
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
#detail-panel { position: absolute; right: 20px; top: 20px; width: 400px; max-height: calc(100vh - 120px); background: #fff; border-radius: 10px; box-shadow: 0 4px 24px rgba(0,0,0,0.18); padding: 0; overflow: hidden; display: none; z-index: 10; flex-direction: column; }
#detail-panel .dp-header { background: linear-gradient(135deg, #1a237e, #3949ab); color: #fff; padding: 14px 16px; position: relative; }
#detail-panel .dp-header h3 { font-size: 16px; font-weight: 600; margin: 0; }
#detail-panel .dp-header .meta { font-size: 11px; opacity: 0.8; margin-top: 3px; }
#detail-panel .close-btn { position: absolute; right: 12px; top: 12px; cursor: pointer; font-size: 20px; opacity: 0.7; }
#detail-panel .close-btn:hover { opacity: 1; }
#detail-content { padding: 16px; overflow-y: auto; max-height: calc(100vh - 220px); }
.dp-section { margin-bottom: 14px; }
.dp-section h4 { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
.dp-section .summary-text { font-size: 15px; color: #1a237e; line-height: 1.7; font-weight: 500; background: #e8eaf6; padding: 10px 14px; border-radius: 8px; border-left: 3px solid #3949ab; }
.dp-section .raw-text { font-size: 13px; color: #444; line-height: 1.6; background: #f5f5f5; padding: 10px 14px; border-radius: 6px; }
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
  <p>V5 概念解释 · <span id="stats-text"></span></p>
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
    
    names.forEach(name => {
        const d = DATA[name];
        const item = document.createElement('div');
        item.className = 'entity-item';
        const preview = d.summary ? d.summary.slice(0, 40) + (d.summary.length > 40 ? '...' : '') : '';
        item.innerHTML = `<strong>${name}</strong> <span class="badge">${(d.weight*1000).toFixed(0)}</span><br><small style="color:#999;">${preview}</small>`;
        item.onclick = () => { showEntity(name); highlightNode(name); };
        item.id = 'item-' + name.replace(/[^a-zA-Z0-9\u4e00-\u9fff]/g, '_');
        listEl.appendChild(item);
    });
    
    buildGraph(ch);
}

function showEntity(name) {
    const d = DATA[name];
    if (!d) return;
    document.querySelectorAll('.entity-item').forEach(e => e.classList.remove('selected'));
    const item = document.getElementById('item-' + name.replace(/[^a-zA-Z0-9\u4e00-\u9fff]/g, '_'));
    if (item) item.classList.add('selected');
    
    document.getElementById('dp-title').textContent = (d.is_section_title ? '📌 ' : '') + name;
    document.getElementById('dp-meta').textContent = `第${d.ch_num}章 · 权重 ${(d.weight*1000).toFixed(0)}${d.is_section_title ? ' · 章节标题' : ''}`;
    
    let html = '';
    
    // 核心：概念解释
    if (d.summary) {
        html += `<div class="dp-section"><h4>理解</h4><div class="summary-text">${d.summary}</div></div>`;
    }
    
    // 书中定义（折叠）
    if (d.definition && d.definition !== '(暂无定义)') {
        html += `<div class="dp-section"><h4>书中定义 <small style="cursor:pointer;color:#1565c0;" onclick="toggleDef(this)">[展开]</small></h4><div class="raw-text" style="display:none;">${d.definition}</div></div>`;
    }
    
    // 原文段落（折叠）
    if (d.paragraph && d.paragraph !== '(暂无段落)') {
        html += `<div class="dp-section"><h4>原文段落 <small style="cursor:pointer;color:#1565c0;" onclick="toggleDef(this)">[展开]</small></h4><div class="raw-text" style="display:none;">${d.paragraph}</div></div>`;
    }
    
    // 关联实体
    if (d.related_entities && d.related_entities.length > 0) {
        html += `<div class="dp-section"><h4>关联实体 (${d.related_entities.length})</h4><div class="rels">`;
        d.related_entities.slice(0, 20).forEach(r => {
            html += `<a onclick="showEntity('${r.name.replace(/'/g, "\\'")}');highlightNode('${r.name.replace(/'/g, "\\'")}')">${r.name}</a> (${r.type})<br>`;
        });
        if (d.related_entities.length > 20) {
            html += `<small>…共${d.related_entities.length}个关联</small>`;
        }
        html += `</div></div>`;
    }
    
    document.getElementById('detail-content').innerHTML = html;
    document.getElementById('detail-panel').style.display = 'flex';
}

function toggleDef(el) {
    const div = el.parentElement.nextElementSibling;
    if (div) {
        div.style.display = div.style.display === 'none' ? 'block' : 'none';
        el.textContent = div.style.display === 'block' ? '[收起]' : '[展开]';
    }
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
            label: name,
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
print(f"HTML: {OUTPUT_HTML}")
print("\n完成!")