"""
知识图谱增强器 v3
功能:
  1. 从原文提取每个实体的完整定义段落
  2. LLM 生成通俗概括性解释
  3. 构建实体间关联关系（共现分析 + LLM）
  4. 生成升级版交互式 HTML
"""
import re, json, os, requests
from collections import defaultdict

# ── 配置 ──
BOOK_TEXT = r'e:\nlp\ltp\kg_book_full.txt'
DEFINITIONS_FILE = r'e:\nlp\ltp\kg_entity_definitions_clean.json'
ENTITY_DB_FILE = r'e:\nlp\ltp\kg_entity_db_clean.json'
OUTPUT_ENRICHED = r'e:\nlp\ltp\kg_entity_enriched.json'
OUTPUT_RELATIONS = r'e:\nlp\ltp\kg_entity_relations.json'
OUTPUT_HTML = r'e:\nlp\ltp\kg_book_interactive_v3.html'

OLLAMA_URL = 'http://localhost:11434/api/generate'

# ── 1. 加载数据 ──

with open(DEFINITIONS_FILE, encoding='utf-8') as f:
    definitions = json.load(f)
with open(ENTITY_DB_FILE, encoding='utf-8') as f:
    entity_db = json.load(f)
with open(BOOK_TEXT, encoding='utf-8') as f:
    book_text = f.read()

print(f"📖 加载完成: {len(definitions)} 定义, {sum(len(v) for v in entity_db.values())} 实体")

# ── 2. 从原文提取完整定义段落 ──

def extract_paragraph(text, entity_name, max_len=600):
    """从原文中提取包含实体的最佳定义段落"""
    paras = [p.strip() for p in text.split('\n') if p.strip() and len(p.strip()) > 20]
    
    # 优先找定义模式段落
    def_patterns = [
        rf'{re.escape(entity_name)}.{{0,20}}(是指|指的是|就是|定义为|表示|描述)',
        rf'(所谓|通常|一般).{{0,10}}{re.escape(entity_name)}',
        rf'{re.escape(entity_name)}.{{0,20}}是[一]种',
        rf'{re.escape(entity_name)}.{{0,20}}指[的]?是',
    ]
    
    best_para = ''
    best_score = 0
    
    for para in paras:
        if entity_name not in para:
            continue
        
        score = 0
        # 实体在段落开头加分
        if para.startswith(entity_name) or para.startswith('第' + entity_name):
            score += 3
        # 定义模式加分
        for pat in def_patterns:
            if re.search(pat, para[:300]):
                score += 5
                break
        # 段落长度适中加分
        if 80 <= len(para) <= 500:
            score += 2
        elif len(para) > 500:
            score += 1
        # 包含专业术语加分
        if any(kw in para for kw in ['知识图谱', '方法', '技术', '模型', '系统', '数据']):
            score += 1
        
        if score > best_score:
            best_score = score
            best_para = para
    
    # 没有定义段就找最相关的
    if not best_para:
        for para in paras:
            if entity_name in para:
                if len(para) > len(best_para):
                    best_para = para
    
    # 截断但保持完整句子
    if len(best_para) > max_len:
        cut = best_para[:max_len]
        last_period = max(cut.rfind('。'), cut.rfind('. '))
        if last_period > 50:
            best_para = cut[:last_period+1]
    
    return best_para


# ── 章节范围映射 ──
CHAPTER_RANGES = {
    1: (405, 1733), 2: (1733, 2742), 3: (2742, 3882),
    4: (3882, 5031), 5: (5031, 8087), 6: (8087, 9422),
    7: (9422, 10049), 8: (10049, 11291), 9: (11291, 12304),
}

def get_chapter_text(ch_num):
    """获取指定章节的原文"""
    lines = book_text.split('\n')
    start, end = CHAPTER_RANGES.get(ch_num, (0, len(lines)))
    return '\n'.join(lines[start:end])

def get_chapter_num_from_title(ch_title):
    """从章标题获取章节号"""
    m = re.search(r'\d+', ch_title)
    return int(m.group()) if m else 0


# ── 执行段落提取 ──

print("\n🔍 步骤1: 从原文提取完整定义段落...")
enriched = {}
for name, info in definitions.items():
    ch_num = get_chapter_num_from_title(info['chapter'])
    if ch_num:
        ch_text = get_chapter_text(ch_num)
        full_para = extract_paragraph(ch_text, name)
    else:
        full_para = extract_paragraph(book_text, name)
    
    enriched[name] = {
        'definition': info['definition'],
        'definition_full': full_para,
        'chapter': info['chapter'],
        'category': info['category'],
        'explanation': '',  # 稍后填充
        'related_entities': [],  # 稍后填充
    }
    if full_para:
        print(f"  ✅ {name}: 找到 {len(full_para)} 字符段落")
    else:
        print(f"  ⚠️ {name}: 未找到定义段落")

para_found = sum(1 for v in enriched.values() if v['definition_full'])
print(f"\n段落提取完成: {para_found}/{len(enriched)} 实体有原文段落")


# ── 3. LLM 生成通俗解释 ──

print("\n🤖 步骤2: LLM 生成通俗概括性解释...")

def generate_explanation(entity_name, definition, context_text, retries=2):
    """用 LLM 生成通俗解释"""
    # 取上下文的前500字作参考
    context = context_text[:500] if context_text else definition
    
    prompt = f'''你是一个知识图谱科普专家。请用最通俗易懂的语言解释以下概念。

概念名称: {entity_name}
定义: {definition}

要求:
1. 用生活化的比喻或例子来解释
2. 让完全没有技术背景的人也能理解
3. 控制在 100-150 字
4. 不要重复定义原文

通俗解释:'''

    for attempt in range(retries):
        try:
            r = requests.post(OLLAMA_URL, json={
                'model': 'qwen2.5:3b',
                'prompt': prompt,
                'stream': False,
                'temperature': 0.3,
                'num_predict': 256,
            }, timeout=120)
            result = r.json().get('response', '').strip()
            if result and len(result) > 20:
                # 清理
                result = re.sub(r'^(通俗解释|解释)[：:\s]*', '', result)
                return result[:300]
        except Exception as e:
            if attempt < retries - 1:
                continue
            return ''
    return ''


# 分批处理，每批5个
entity_list = list(enriched.items())
batch_size = 5
generated = 0

for i in range(0, len(entity_list), batch_size):
    batch = entity_list[i:i+batch_size]
    for name, info in batch:
        if info['explanation']:
            continue
        explanation = generate_explanation(name, info['definition'], info['definition_full'])
        if explanation:
            enriched[name]['explanation'] = explanation
            generated += 1
            print(f"  ✅ [{generated}] {name}: {explanation[:60]}...")
        else:
            print(f"  ⚠️ {name}: 生成失败")
    
    # 每批间隔
    if i + batch_size < len(entity_list):
        print(f"  ... 已生成 {generated}/{len(enriched)}, 继续下一批...\n")

print(f"\n通俗解释生成完成: {generated}/{len(enriched)}")


# ── 4. 构建实体间关联关系 ──

print("\n🔗 步骤3: 构建实体间关联关系...")

def build_entity_relations(enriched_data, entity_db_data, book_text_lines):
    """基于共现分析构建实体关联"""
    relations = []
    
    # 按章节分组实体
    ch_entities = defaultdict(list)
    for name, info in enriched_data.items():
        ch_num = get_chapter_num_from_title(info['chapter'])
        ch_entities[ch_num].append(name)
    
    # 为每章分析共现
    for ch_num, entities in ch_entities.items():
        if ch_num not in CHAPTER_RANGES:
            continue
        start, end = CHAPTER_RANGES[ch_num]
        ch_lines = book_text_lines[start:end]
        
        # 按段落分析
        paras = [p.strip() for p in '\n'.join(ch_lines).split('\n') if p.strip() and len(p.strip()) > 30]
        
        # 共现矩阵
        cooccur = defaultdict(int)
        for para in paras:
            # 找该段落中出现的实体
            found = [e for e in entities if e in para]
            for i in range(len(found)):
                for j in range(i+1, len(found)):
                    pair = tuple(sorted([found[i], found[j]]))
                    cooccur[pair] += 1
        
        # 生成关系
        for (e1, e2), count in cooccur.items():
            if count >= 2:  # 至少共现2次才算关联
                # 判断关系类型
                relation_type = determine_relation_type(e1, e2, count)
                
                # 找关系描述
                relation_desc = ''
                for para in paras:
                    if e1 in para and e2 in para:
                        relation_desc = para[:200]
                        break
                
                relations.append({
                    'source': e1,
                    'target': e2,
                    'type': relation_type,
                    'strength': min(count, 5),
                    'chapter': ch_num,
                    'description': relation_desc[:150] if relation_desc else '',
                })
    
    return relations


def determine_relation_type(e1, e2, count):
    """判断关系类型"""
    # 基于关键词启发式
    parent_child_pairs = [
        ('知识图谱', '语义网络'), ('知识图谱', 'RDF'), ('知识图谱', '知识表示'),
        ('知识图谱', '知识抽取'), ('知识图谱', '知识融合'), ('知识图谱', '知识存储'),
        ('知识图谱', '知识推理'), ('知识图谱', '知识问答'), ('知识图谱', '语义搜索'),
    ]
    for p, c in parent_child_pairs:
        if (e1 == p and e2 == c):
            return '包含'
        if (e1 == c and e2 == p):
            return '属于'
    
    tool_pairs = [
        ('Neo4j', '图数据库'), ('Neo4j', '三元组'), ('Neo4j', '属性图'),
        ('RDF', '三元组'), ('RDFS', 'OWL'), ('RDF', 'OWL'),
    ]
    for a, b in tool_pairs:
        if {e1, e2} == {a, b}:
            return '关联'
    
    return '相关'


# 执行
book_lines = book_text.split('\n')
relations = build_entity_relations(enriched, entity_db, book_lines)

# 将关系写回 enriched
rel_db = defaultdict(list)
for rel in relations:
    rel_db[rel['source']].append(rel)
    rel_db[rel['target']].append(rel)
    
    if rel['source'] in enriched:
        enriched[rel['source']]['related_entities'].append({
            'name': rel['target'],
            'type': rel['type'],
            'strength': rel['strength'],
        })
    if rel['target'] in enriched:
        enriched[rel['target']]['related_entities'].append({
            'name': rel['source'],
            'type': rel['type'] if rel['type'] in ['相关'] else ('被包含' if rel['type'] == '包含' else '包含' if rel['type'] == '属于' else '相关'),
            'strength': rel['strength'],
        })

print(f"关系构建完成: {len(relations)} 条")
rel_count = sum(1 for v in enriched.values() if v['related_entities'])
print(f"有关系的实体: {rel_count}/{len(enriched)}")


# ── 5. 保存 ──

with open(OUTPUT_ENRICHED, 'w', encoding='utf-8') as f:
    json.dump(enriched, f, ensure_ascii=False, indent=2)
print(f"\n✅ 增强数据保存: {OUTPUT_ENRICHED}")

with open(OUTPUT_RELATIONS, 'w', encoding='utf-8') as f:
    json.dump(relations, f, ensure_ascii=False, indent=2)
print(f"✅ 关系数据保存: {OUTPUT_RELATIONS}")


# ── 6. 生成升级版 HTML ──

print("\n📄 步骤4: 生成升级版交互式 HTML...")

def generate_enriched_html():
    """生成升级版交互式 HTML"""
    all_entities_data = []
    for name, info in enriched.items():
        ch_num = get_chapter_num_from_title(info['chapter'])
        all_entities_data.append({
            'name': name,
            'category': info['category'],
            'chapter': info['chapter'],
            'ch_num': ch_num,
            'definition': info['definition'],
            'definition_full': info['definition_full'],
            'explanation': info['explanation'],
            'related': info['related_entities'][:8],
        })
    
    data_json = json.dumps(all_entities_data, ensure_ascii=False)
    
    html_template = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>知识图谱 - 全书增强版 v3</title>
<script src="https://unpkg.com/vis-network@9.1.6/standalone/umd/vis-network.min.js"></script>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:'Microsoft YaHei',sans-serif; background:#f0f2f5; height:100vh; overflow:hidden; }
  #header { background:linear-gradient(135deg,#4A90D9,#2E5A8A); color:#fff; padding:12px 24px; display:flex; align-items:center; justify-content:space-between; }
  #header h1 { font-size:20px; font-weight:600; }
  #main { display:flex; height:calc(100vh - 52px); }
  #graph-container { flex:1; background:#fff; position:relative; }
  #graph { width:100%; height:100%; }
  #sidebar { width:420px; background:#fff; border-left:1px solid #e0e0e0; display:flex; flex-direction:column; }
  #sidebar-header { padding:14px 16px; border-bottom:1px solid #eee; font-weight:bold; font-size:14px; color:#333; display:flex; justify-content:space-between; align-items:center; }
  #sidebar-header a { color:#4A90D9; cursor:pointer; font-weight:normal; font-size:12px; text-decoration:none; }
  #sidebar-content { flex:1; padding:16px; overflow-y:auto; }
  #empty { color:#999; text-align:center; padding:60px 20px; font-size:14px; line-height:2; }
  .entity-header { margin-bottom:12px; }
  .entity-header .name { font-size:20px; font-weight:bold; color:#2c3e50; }
  .entity-header .meta { margin-top:4px; }
  .entity-header .category-badge { display:inline-block; font-size:11px; padding:2px 12px; border-radius:10px; margin-right:6px; }
  .entity-header .chapter-tag { font-size:11px; color:#888; }
  .cat-concept { background:#E3F2FD; color:#1565C0; }
  .cat-method { background:#E8F5E9; color:#2E7D32; }
  .cat-tool { background:#FFF3E0; color:#E65100; }
  .cat-theory { background:#F3E5F5; color:#7B1FA2; }
  .cat-technology { background:#E0F7FA; color:#00838F; }
  .cat-task { background:#FFF8E1; color:#F57F17; }
  .section-card { background:#f8fafb; border-radius:8px; padding:12px 14px; margin-bottom:10px; }
  .section-card .label { font-size:11px; font-weight:bold; margin-bottom:6px; display:flex; align-items:center; gap:4px; }
  .section-card .text { font-size:13px; color:#333; line-height:1.8; }
  .def-original { border-left:3px solid #4A90D9; }
  .def-short { border-left:3px solid #50C878; }
  .def-explain { border-left:3px solid #FF8C42; background:#FFF8F0; }
  .related-list { display:flex; flex-wrap:wrap; gap:4px; margin-top:6px; }
  .related-chip { display:inline-flex; align-items:center; gap:4px; padding:4px 10px; border-radius:14px; font-size:12px; cursor:pointer; transition:all .15s; }
  .related-chip:hover { transform:scale(1.05); }
  .rel-相关 { background:#f0f0f0; color:#555; }
  .rel-包含 { background:#E3F2FD; color:#1565C0; }
  .rel-属于 { background:#E8F5E9; color:#2E7D32; }
  .rel-被包含 { background:#FFF3E0; color:#E65100; }
  .rel-关联 { background:#F3E5F5; color:#7B1FA2; }
  .search-box { padding:10px 16px; border-bottom:1px solid #eee; }
  .search-box input { width:100%; padding:6px 10px; border:1px solid #ddd; border-radius:5px; font-size:12px; font-family:inherit; outline:none; }
  .search-box input:focus { border-color:#4A90D9; }
  #controls { position:absolute; top:12px; right:12px; z-index:10; display:flex; gap:6px; }
  #controls button { padding:6px 14px; border:1px solid #ccc; background:#fff; border-radius:6px; cursor:pointer; font-size:12px; font-family:inherit; }
  #controls button:hover { background:#f0f4ff; border-color:#4A90D9; }
  #controls button.active { background:#4A90D9; color:#fff; border-color:#4A90D9; }
  .legend { position:absolute; bottom:16px; left:16px; z-index:10; background:rgba(255,255,255,.95); padding:10px 14px; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,.12); font-size:12px; }
</style>
</head>
<body>
<div id="header">
  <h1>知识图谱 方法、实践与应用</h1>
  <div style="font-size:13px;opacity:.85;"><span id="stats"></span></div>
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
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
        <span><span style="display:inline-block;width:12px;height:12px;background:#4A90D9;border-radius:2px;"></span> 章</span>
        <span><span style="display:inline-block;width:12px;height:12px;background:#fff8e1;border:1px solid #FF8C42;border-radius:2px;"></span> 概念</span>
      </div>
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
        点击图中概念节点查看<br>
        原文定义 + 通俗解释 + 关联关系<br><br>
        <small>快捷键: [1]树形 [2]网状 [F]适应</small>
      </div>
      <div id="detail" style="display:none;"></div>
      <div id="searchResults" style="display:none;"></div>
    </div>
  </div>
</div>

<script>
// ============ 实体数据 ============
const ENTITIES = __DATA_JSON__;

function makeCat(cat) {
  const m = {'概念':'cat-concept','方法':'cat-method','工具':'cat-tool','理论':'cat-theory','技术':'cat-technology','任务':'cat-task'};
  return '<span class="category-badge ' + (m[cat]||'cat-concept') + '">' + cat + '</span>';
}

function renderDetail(entity) {
  let html = '<div class="entity-header">';
  html += '<div class="name">' + entity.name + '</div>';
  html += '<div class="meta">' + makeCat(entity.category) + '<span class="chapter-tag"> ' + entity.chapter + '</span></div>';
  html += '</div>';

  if (entity.explanation) {
    html += '<div class="section-card def-explain">';
    html += '<div class="label"><span class="icon">[通俗理解]</span></div>';
    html += '<div class="text">' + entity.explanation + '</div>';
    html += '</div>';
  }

  if (entity.definition) {
    html += '<div class="section-card def-short">';
    html += '<div class="label"><span class="icon">[书中定义]</span></div>';
    html += '<div class="text">' + entity.definition + '</div>';
    html += '</div>';
  }

  if (entity.definition_full) {
    html += '<div class="section-card def-original">';
    html += '<div class="label"><span class="icon">[原文段落]</span></div>';
    html += '<div class="text">' + entity.definition_full + '</div>';
    html += '</div>';
  }

  if (entity.related && entity.related.length > 0) {
    html += '<div class="section-card" style="border-left:3px solid #9B59B6;">';
    html += '<div class="label"><span class="icon">[关联概念] (' + entity.related.length + ')</span></div>';
    html += '<div class="related-list">';
    entity.related.forEach(function(rel) {
      html += '<span class="related-chip rel-' + rel.type + '" onclick="focusEntity(\'' + rel.name + '\')">' + rel.name + ' <small>(' + rel.type + ')</small></span>';
    });
    html += '</div></div>';
  }
  return html;
}

function focusEntity(name) { showNodeDetail(name); }
function getEntityByName(name) { return ENTITIES.find(function(e) { return e.name === name; }); }

function searchNodes(query) {
  var res = document.getElementById('searchResults');
  var det = document.getElementById('detail');
  var emp = document.getElementById('empty');
  if (!query.trim()) { res.style.display='none'; if (det.style.display!='block') emp.style.display='block'; return; }
  var q = query.toLowerCase();
  var matches = ENTITIES.filter(function(e) {
    return e.name.toLowerCase().includes(q) || e.definition.toLowerCase().includes(q) || (e.explanation && e.explanation.toLowerCase().includes(q));
  }).slice(0, 30);
  emp.style.display='none'; det.style.display='none'; res.style.display='block';
  if (matches.length===0) { res.innerHTML='<div style="color:#999;padding:20px;text-align:center;">未找到匹配概念</div>'; return; }
  var html = '<div style="font-size:13px;color:#555;margin-bottom:8px;">找到 ' + matches.length + ' 个匹配概念：</div>';
  matches.forEach(function(e) {
    html += '<div class="related-chip rel-相关" onclick="showNodeDetail(\'' + e.name + '\')" style="margin:3px;padding:6px 12px;">' + e.name + ' <small style="color:#999;">[' + e.category + ']</small></div>';
  });
  res.innerHTML = html;
}

function clearSelection() {
  document.getElementById('detail').style.display='none';
  document.getElementById('empty').style.display='block';
  document.getElementById('searchResults').style.display='none';
  document.getElementById('searchInput').value='';
  if (network) network.selectNodes([],false);
}

function showNodeDetail(nodeId) {
  var det = document.getElementById('detail');
  var emp = document.getElementById('empty');
  var res = document.getElementById('searchResults');
  emp.style.display='none'; res.style.display='none'; det.style.display='block';
  var entity = null;
  if (typeof nodeId==='string' && nodeId.startsWith('ent_')) {
    entity = getEntityByName(decodeURIComponent(nodeId.substring(4)));
  } else if (typeof nodeId==='string') {
    entity = getEntityByName(nodeId);
  }
  if (!entity) entity = getEntityByName(nodeId);
  if (!entity) {
    var node = nodesData.get(nodeId);
    if (node) { det.innerHTML = '<div class="entity-header"><div class="name">' + (node.fullLabel||node.label) + '</div></div>'; return; }
    det.innerHTML = '<div style="color:#999;">未找到信息</div>'; return;
  }
  det.innerHTML = renderDetail(entity);
}

// ============ vis-network ============
var nodes = [];
var edges = [];
var chGroups = {};
var addedEntities = new Set();

var chNames = ['知识图谱概述','知识图谱表示与建模','知识存储','知识抽取与知识挖掘','知识图谱融合','知识图谱推理','语义搜索','知识问答','知识图谱应用案例'];
var chColors = ['#4A90D9','#50C878','#FF8C42','#9B59B6','#E74C3C','#1ABC9C','#F39C12','#3498DB','#2ECC71'];

for (var n=1; n<=9; n++) {
  var cid = 'ch_'+n;
  chGroups[n] = cid;
  var ents = ENTITIES.filter(function(e) { return e.ch_num===n; });
  nodes.push({ id: cid, label: chNames[n-1], group:'chapter', color:{background:chColors[n-1],border:'#fff'}, font:{color:'#fff',size:16,face:'Microsoft YaHei',bold:true}, shape:'box', borderWidth:3, level:0, entityCount:ents.length, fullLabel:'第'+n+'章 '+chNames[n-1] });
  if (n>1) edges.push({ from:'ch_'+(n-1), to:cid, arrows:{to:{enabled:true,scaleFactor:0.5}}, color:'#aaa', width:2, dashes:true });
}

ENTITIES.forEach(function(e) {
  if (addedEntities.has(e.name)) return;
  addedEntities.add(e.name);
  var nid = 'ent_'+encodeURIComponent(e.name);
  var pid = chGroups[e.ch_num] || 'ch_'+e.ch_num;
  nodes.push({
    id: nid, label: e.name.length>12 ? e.name.substring(0,12)+'..' : e.name,
    fullLabel: e.name, group:'entity',
    color:{background:'#fff8e1',border:'#FF8C42'},
    font:{color:'#e65100',size:11,face:'Microsoft YaHei'},
    shape:'dot', size:18, borderWidth:1.5, level:2
  });
  edges.push({ from:pid, to:nid, color:'#ddd', width:0.8, dashes:true });
});

var nodesData = new vis.DataSet(nodes);
var edgesData = new vis.DataSet(edges);

var baseOpts = {
  physics: { solver:'barnesHut', barnesHut:{gravitationalConstant:-5000,centralGravity:0.2,springLength:180,springConstant:0.03}, stabilization:{iterations:200} },
  interaction: { hover:true, hoverConnectedEdges:true, selectConnectedEdges:false, tooltipDelay:200 },
  edges: { smooth:{type:'continuous'} }
};
var hierOpts = Object.assign({}, baseOpts, { layout:{hierarchical:{enabled:true,direction:'LR',sortMethod:'directed',levelSeparation:280,nodeSpacing:120,treeSpacing:160}}, physics:false });
var netOpts = Object.assign({}, baseOpts, { layout:{} });

var currentLayout = 'hierarchical';
var network = null;

function init() {
  var container = document.getElementById('graph');
  network = new vis.Network(container, { nodes:nodesData, edges:edgesData }, hierOpts);
  network.on('click', function(params) {
    if (params.nodes.length>0) {
      var nid = params.nodes[0];
      if (nid.startsWith('ent_')) {
        var name = decodeURIComponent(nid.substring(4));
        var entity = getEntityByName(name);
        if (entity) { showNodeDetail(name); document.getElementById('stats').innerHTML = '概念: ' + entity.name; return; }
      }
      showNodeDetail(nid);
    } else { clearSelection(); }
  });
  document.getElementById('stats').innerHTML = ENTITIES.length + ' 概念 | 边 ' + edges.length + ' 条';
}

function setLayout(mode) {
  if (mode===currentLayout) return;
  currentLayout=mode;
  document.getElementById('btnTree').className=mode==='hierarchical'?'active':'';
  document.getElementById('btnNet').className=mode==='network'?'active':'';
  network.setOptions(mode==='hierarchical'?hierOpts:netOpts);
  if (mode==='network') { network.setOptions({physics:true}); setTimeout(function(){network.stopSimulation();},3000); }
}
function fitAll() { network.fit({animation:true}); }

init();
</script>
</body>
</html>'''
    
    html = html_template.replace('__DATA_JSON__', data_json)
    
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ 升级版 HTML: {OUTPUT_HTML}")
    print(f"   实体: {len(all_entities_data)}")

generate_enriched_html()

print("\n" + "=" * 50)
print("🎉 全部完成！三步升级汇总：")
print("=" * 50)
print(f"   📖 原文段落提取: {para_found}/{len(enriched)}")
print(f"   💡 通俗解释生成: {generated}/{len(enriched)}")
print(f"   🔗 关联关系构建: {len(relations)} 条")
print(f"   🖥️  升级版 HTML: {OUTPUT_HTML}")