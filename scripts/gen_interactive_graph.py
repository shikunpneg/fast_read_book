"""
《知识图谱 方法、实践与应用》交互式知识图谱生成器（带原文定义）

用法:
  python gen_interactive_graph.py                    # 全书（带原文定义）
  python gen_interactive_graph.py 3                  # 第3章
  python gen_interactive_graph.py 1-5                # 第1~5章
  python gen_interactive_graph.py 2 4 6              # 第2、4、6章
  python gen_interactive_graph.py 3 --mmd            # 同时输出 Mermaid
"""
import re, sys, os, argparse, json

# ── 路径 ──
BOOK_TEXT = r'e:\nlp\ltp\kg_book_full.txt'
KGGEN_RESULT = r'e:\nlp\ltp\kg_book_5ch_kggen.txt'
DEFINITIONS_FILE = r'e:\nlp\ltp\kg_entity_definitions_clean.json'
ENTITY_DB_FILE = r'e:\nlp\ltp\kg_entity_db_clean.json'

# ── 颜色方案 ──
CH_COLORS = [
    "#4A90D9", "#50C878", "#FF8C42", "#9B59B6", "#E74C3C",
    "#1ABC9C", "#F39C12", "#3498DB", "#2ECC71",
]
CH_STROKES = CH_COLORS
CH_NAMES_SHORT = [
    "知识图谱概述", "知识图谱表示与建模", "知识存储",
    "知识抽取与知识挖掘", "知识图谱融合", "知识图谱推理",
    "语义搜索", "知识问答", "知识图谱应用案例",
]


# =========================================================
#  1. 数据解析
# =========================================================

def parse_toc(text):
    """解析目录，返回 [(level, title, ch_num), ...]"""
    lines = text.split('\n')
    seen = set()
    toc = []
    for line in lines:
        ls = line.strip()
        if not ls:
            continue
        m = re.match(r'^第([一二三四五六七八九十\d]+)章\s+(.+)$', ls)
        if m:
            title = f"第{m.group(1)}章 {m.group(2)}"
            if title not in seen:
                seen.add(title)
                toc.append((0, title, m.group(1)))
            continue
        m = re.match(r'^(\d+)\.(\d+)\s+(.+)$', ls)
        if m:
            title = f"{m.group(1)}.{m.group(2)} {m.group(3)}"
            key = f"sec-{m.group(1)}.{m.group(2)}"
            if key not in seen and m.group(1).isdigit():
                seen.add(key)
                toc.append((1, title, m.group(1)))
    return toc


def load_definitions():
    """加载定义数据"""
    if os.path.exists(DEFINITIONS_FILE):
        with open(DEFINITIONS_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {}


# =========================================================
#  2. 实体定义（9章全覆盖）
# =========================================================

def load_entity_db():
    """从 JSON 加载清洗后的实体数据库"""
    if os.path.exists(ENTITY_DB_FILE):
        with open(ENTITY_DB_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {}

ENTITY_DB = load_entity_db()


def get_chapter_entities(ch_name):
    """按章节名模糊匹配获取实体列表"""
    cn = ch_name.replace(' ', '')
    for key, ents in ENTITY_DB.items():
        kn = key.replace(' ', '')
        if re.search(r'\d+', cn) and re.search(r'\d+', kn):
            if re.search(r'\d+', cn).group() == re.search(r'\d+', kn).group():
                return ents
    return []


# =========================================================
#  3. TOC 工具
# =========================================================

def select_chapters(toc, chapter_nums):
    if not chapter_nums:
        return toc
    target = set(str(n) for n in chapter_nums)
    selected = []
    cur = None
    for item in toc:
        if item[0] == 0:
            m = re.search(r'\d+', item[1])
            n = m.group() if m else ""
            cur = n if n in target else None
            if cur:
                selected.append(item)
        elif item[0] == 1 and cur and item[2] == cur:
            selected.append(item)
    return selected


# =========================================================
#  4. 构建交互图数据
# =========================================================

def build_graph_data(toc, definitions, chapter_nums=None):
    """构建 vis-network 数据，带定义信息"""
    filtered = select_chapters(toc, chapter_nums) if chapter_nums else toc
    chapters = [item for item in filtered if item[0] == 0]
    ch_names = [c[1] for c in chapters]
    if not ch_names:
        return [], []

    nodes = []
    edges = []
    ch_id_map = {}
    sec_count = 0
    ent_id_set = set()

    # ── 章节点 ──
    for i, ch_name in enumerate(ch_names):
        nid = f"ch_{i}"
        ch_id_map[ch_name] = nid
        ch_idx = int(re.search(r'\d+', ch_name).group() if re.search(r'\d+', ch_name) else "1") - 1
        ch_short = CH_NAMES_SHORT[ch_idx] if ch_idx < len(CH_NAMES_SHORT) else ch_name
        color = CH_COLORS[ch_idx] if ch_idx < len(CH_COLORS) else "#999"

        entities = get_chapter_entities(ch_name)
        ent_badge = f" [{len(entities)}概念]" if entities else ""

        nodes.append({
            "id": nid,
            "label": ch_short,
            "fullLabel": ch_name,
            "group": "chapter",
            "color": {"background": color, "border": "#fff",
                      "highlight": {"background": color, "border": "#fff"}},
            "font": {"color": "#fff", "size": 18, "face": "Microsoft YaHei", "bold": True},
            "shape": "box",
            "size": 40,
            "borderWidth": 3,
            "borderWidthSelected": 4,
            "level": 0,
            "entityCount": len(entities),
            "type": "chapter",
        })

    # ── 章间链接 ──
    for i in range(len(ch_names) - 1):
        edges.append({
            "from": ch_id_map[ch_names[i]],
            "to": ch_id_map[ch_names[i + 1]],
            "label": "→",
            "arrows": {"to": {"enabled": True, "scaleFactor": 0.6}},
            "color": {"color": "#aaa", "highlight": "#FF8C42"},
            "dashes": False, "width": 2,
            "smooth": {"type": "curvedCW", "roundness": 0.1},
        })

    # ── 节节点 ──
    for item in filtered:
        if item[0] == 1:
            nid = f"sec_{sec_count}"
            sec_count += 1
            ch_num_str = item[2]
            parent_ch = None
            for c in ch_names:
                if re.search(r'\d+', c) and re.search(r'\d+', c).group() == ch_num_str:
                    parent_ch = c
                    break
            parent_id = ch_id_map.get(parent_ch) if parent_ch else None

            nodes.append({
                "id": nid,
                "label": item[1],
                "fullLabel": item[1],
                "group": "section",
                "color": {"background": "#f0f4ff", "border": "#4A90D9",
                          "highlight": {"background": "#dbe8ff", "border": "#4A90D9"}},
                "font": {"color": "#2c3e50", "size": 13, "face": "Microsoft YaHei"},
                "shape": "box", "size": 20,
                "borderWidth": 1.5, "level": 1,
                "parent": parent_id, "type": "section",
            })
            if parent_id:
                edges.append({
                    "from": parent_id, "to": nid,
                    "color": {"color": "#bbb", "highlight": "#4A90D9"},
                    "width": 1, "smooth": True,
                })

    # ── 实体节点 ──
    for ch_name in ch_names:
        parent_id = ch_id_map.get(ch_name)
        if not parent_id:
            continue
        entities = get_chapter_entities(ch_name)
        for ent in entities:
            if not ent or len(ent) > 25:
                continue
            eid = f"ent_{ent.replace(' ', '_')}"
            if eid in ent_id_set:
                continue
            ent_id_set.add(eid)

            # 获取定义
            def_data = definitions.get(ent, {})
            definition_text = def_data.get("definition", "") if isinstance(def_data, dict) else ""
            def_chapter = def_data.get("chapter", ch_name) if isinstance(def_data, dict) else ch_name

            nodes.append({
                "id": eid,
                "label": ent[:18],
                "fullLabel": ent,
                "group": "entity",
                "color": {"background": "#fff8e1", "border": "#FF8C42",
                          "highlight": {"background": "#ffecb3", "border": "#FF8C42"}},
                "font": {"color": "#e65100", "size": 12, "face": "Microsoft YaHei"},
                "shape": "ellipse", "size": 15,
                "borderWidth": 1.5, "level": 2,
                "parent": parent_id, "type": "entity",
                "definition": definition_text[:600] if definition_text else "",
                "defChapter": def_chapter,
            })
            edges.append({
                "from": parent_id, "to": eid,
                "color": {"color": "#ddd", "highlight": "#FF8C42"},
                "width": 0.8, "dashes": True, "smooth": True,
            })

    return nodes, edges


# =========================================================
#  5. 生成交互式 HTML
# =========================================================

def generate_interactive_html(nodes, edges, chapter_nums=None):
    if chapter_nums:
        title_suffix = f"第{'、'.join(str(n) for n in chapter_nums)}章"
    else:
        title_suffix = "全书"

    ch_count = sum(1 for n in nodes if n.get("group") == "chapter")
    sec_count = sum(1 for n in nodes if n.get("group") == "section")
    ent_count = sum(1 for n in nodes if n.get("group") == "entity")
    def_count = sum(1 for n in nodes if n.get("definition", ""))

    nodes_json = json.dumps(nodes, ensure_ascii=False)
    edges_json = json.dumps(edges, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>知识图谱 · {title_suffix}</title>
<script src="https://unpkg.com/vis-network@9.1.6/standalone/umd/vis-network.min.js"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Microsoft YaHei',sans-serif; background:#f0f2f5; height:100vh; overflow:hidden; }}
  #header {{ background:linear-gradient(135deg,#4A90D9,#2E5A8A); color:#fff; padding:12px 24px; display:flex; align-items:center; justify-content:space-between; }}
  #header h1 {{ font-size:20px; font-weight:600; }}
  #header .stats {{ font-size:13px; opacity:.85; }}
  #header .stats span {{ margin-left:16px; }}
  #main {{ display:flex; height:calc(100vh - 52px); }}
  #graph-container {{ flex:1; background:#fff; position:relative; }}
  #graph {{ width:100%; height:100%; }}
  #sidebar {{ width:380px; background:#fff; border-left:1px solid #e0e0e0; display:flex; flex-direction:column; }}
  #sidebar-header {{ padding:14px 16px; border-bottom:1px solid #eee; font-weight:bold; font-size:14px; color:#333; display:flex; justify-content:space-between; align-items:center; }}
  #sidebar-header a {{ color:#4A90D9; cursor:pointer; font-weight:normal; font-size:12px; text-decoration:none; }}
  #sidebar-content {{ flex:1; padding:16px; overflow-y:auto; }}
  #empty {{ color:#999; text-align:center; padding:60px 20px; font-size:14px; line-height:2; }}
  .detail-card {{ margin-bottom:16px; }}
  .detail-title {{ font-size:18px; font-weight:bold; color:#2c3e50; margin-bottom:4px; }}
  .detail-type {{ display:inline-block; font-size:11px; padding:2px 12px; border-radius:10px; margin-bottom:10px; }}
  .type-chapter {{ background:#4A90D9; color:#fff; }}
  .type-section {{ background:#E8F4FD; color:#2980B9; border:1px solid #4A90D9; }}
  .type-entity {{ background:#FFF3E0; color:#E65100; border:1px solid #FF8C42; }}
  /* 定义卡片 */
  .def-box {{ background:#f8fafb; border-left:3px solid #FF8C42; padding:12px 14px; border-radius:0 6px 6px 0; margin:10px 0; }}
  .def-box .def-label {{ font-size:11px; color:#E65100; font-weight:bold; margin-bottom:4px; }}
  .def-box .def-text {{ font-size:13px; color:#333; line-height:1.7; }}
  .def-box .def-source {{ font-size:11px; color:#999; margin-top:6px; text-align:right; }}
  /* 关系列表 */
  .detail-relations {{ margin-top:12px; }}
  .detail-relations h4 {{ font-size:13px; color:#555; margin-bottom:6px; padding-bottom:4px; border-bottom:1px solid #eee; }}
  .relation-item {{ padding:6px 10px; background:#f8f9fa; border-radius:6px; margin-bottom:4px; font-size:12px; display:flex; align-items:center; gap:8px; cursor:pointer; transition:background .1s; }}
  .relation-item:hover {{ background:#eef2ff; }}
  .rel-subject {{ color:#4A90D9; font-weight:bold; }}
  .rel-predicate {{ color:#FF8C42; font-style:italic; font-size:11px; }}
  .rel-object {{ color:#50C878; font-weight:bold; }}
  #controls {{ position:absolute; top:12px; right:12px; z-index:10; display:flex; gap:6px; }}
  #controls button {{ padding:6px 14px; border:1px solid #ccc; background:#fff; border-radius:6px; cursor:pointer; font-size:12px; font-family:inherit; transition:all .15s; }}
  #controls button:hover {{ background:#f0f4ff; border-color:#4A90D9; }}
  #controls button.active {{ background:#4A90D9; color:#fff; border-color:#4A90D9; }}
  .legend {{ position:absolute; bottom:16px; left:16px; z-index:10; background:rgba(255,255,255,.95); padding:10px 14px; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,.12); font-size:12px; }}
  .legend-item {{ display:flex; align-items:center; gap:6px; margin:3px 0; }}
  .legend-dot {{ width:12px; height:12px; border-radius:3px; display:inline-block; }}
  .search-box {{ padding:10px 16px; border-bottom:1px solid #eee; }}
  .search-box input {{ width:100%; padding:6px 10px; border:1px solid #ddd; border-radius:5px; font-size:12px; font-family:inherit; outline:none; }}
  .search-box input:focus {{ border-color:#4A90D9; }}
  .entity-tag {{ display:inline-block; background:#FFF3E0; color:#E65100; padding:1px 8px; border-radius:8px; font-size:11px; margin:2px; }}
</style>
</head>
<body>
<div id="header">
  <h1>📚 《知识图谱 方法、实践与应用》</h1>
  <div class="stats">
    <span id="titleSuffix">{title_suffix}</span>
    <span>📘 <strong>{ch_count}</strong> 章</span>
    <span>📄 <strong>{sec_count}</strong> 节</span>
    <span>🏷️ <strong>{ent_count}</strong> 概念</span>
    <span>📖 <strong>{def_count}</strong> 带原文定义</span>
  </div>
</div>
<div id="main">
  <div id="graph-container">
    <div id="graph"></div>
    <div id="controls">
      <button id="btnTree" class="active" onclick="setLayout('hierarchical')">🌲 树形</button>
      <button id="btnNet" onclick="setLayout('network')">🕸️ 网状</button>
      <button onclick="fitAll()">🔍 适应</button>
    </div>
    <div class="legend">
      <div class="legend-item"><span class="legend-dot" style="background:#4A90D9;"></span> 章</div>
      <div class="legend-item"><span class="legend-dot" style="background:#f0f4ff;border:1px solid #4A90D9;"></span> 节</div>
      <div class="legend-item"><span class="legend-dot" style="background:#fff8e1;border:1px solid #FF8C42;"></span> 概念/实体</div>
      <div class="legend-item"><span style="border-bottom:2px dashed #ddd;width:20px;"></span> 关联</div>
    </div>
  </div>
  <div id="sidebar">
    <div id="sidebar-header">
      <span>📋 详情</span>
      <a onclick="clearSelection()">清除</a>
    </div>
    <div class="search-box">
      <input type="text" id="searchInput" placeholder="🔍 搜索节点..." oninput="searchNodes(this.value)">
    </div>
    <div id="sidebar-content">
      <div id="empty">👆 点击图中的节点查看详情<br>📖 概念节点会显示书中原文定义<br>🔍 支持搜索、拖拽、缩放<br><br>💡 快捷键:<br>[1] 树形  [2] 网状<br>[F] 适应  [Esc] 取消</div>
      <div id="detail" style="display:none;"></div>
      <div id="searchResults" style="display:none;"></div>
    </div>
  </div>
</div>

<script>
const nodesData = new vis.DataSet(__NODES_DATA__);
const edgesData = new vis.DataSet(__EDGES_DATA__);

const baseOptions = {{
  physics: {{
    solver: 'barnesHut',
    barnesHut: {{ gravitationalConstant: -5000, centralGravity: 0.2, springLength: 180, springConstant: 0.03 }},
    stabilization: {{ iterations: 200 }},
  }},
  interaction: {{
    hover: true, hoverConnectedEdges: true, selectConnectedEdges: false,
    tooltipDelay: 200, zoomView: true,
  }},
  edges: {{ smooth: {{ type: 'continuous' }} }},
}};

const hierarchicalOptions = {{
  ...baseOptions,
  layout: {{
    hierarchical: {{
      enabled: true, direction: 'LR', sortMethod: 'directed',
      levelSeparation: 280, nodeSpacing: 120, treeSpacing: 160,
      blockShifting: true, edgeMinimization: true, parentCentralization: false,
    }}
  }},
  physics: false,
}};

const networkOptions = {{ ...baseOptions, layout: {{}} }};

let currentLayout = 'hierarchical';
let network = null;

function init() {{
  const container = document.getElementById('graph');
  network = new vis.Network(container, {{ nodes: nodesData, edges: edgesData }}, hierarchicalOptions);

  network.on('click', function(params) {{
    if (params.nodes.length > 0) showNodeDetail(params.nodes[0]);
    else clearSelection();
  }});

  network.on('doubleClick', function(params) {{
    if (params.nodes.length > 0)
      network.focus(params.nodes[0], {{ scale: 1.5, animation: true }});
  }});

  network.on('hoverNode', function() {{ document.body.style.cursor = 'pointer'; }});
  network.on('blurNode', function() {{ document.body.style.cursor = 'default'; }});
}}

function setLayout(mode) {{
  if (mode === currentLayout) return;
  currentLayout = mode;
  document.getElementById('btnTree').className = mode === 'hierarchical' ? 'active' : '';
  document.getElementById('btnNet').className = mode === 'network' ? 'active' : '';
  network.setOptions(mode === 'hierarchical' ? hierarchicalOptions : networkOptions);
  if (mode === 'network') {{
    network.setOptions({{ physics: true }});
    setTimeout(() => network.stopSimulation(), 3000);
  }}
}}

function fitAll() {{ network.fit({{ animation: true }}); }}

function showNodeDetail(nodeId) {{
  const node = nodesData.get(nodeId);
  if (!node) return;

  const detail = document.getElementById('detail');
  const empty = document.getElementById('empty');
  const searchRes = document.getElementById('searchResults');
  empty.style.display = 'none';
  searchRes.style.display = 'none';
  detail.style.display = 'block';

  const isChapter = node.group === 'chapter';
  const isSection = node.group === 'section';
  const isEntity  = node.group === 'entity';

  let typeLabel = isChapter ? '章' : (isSection ? '节' : '概念');
  let typeClass = isChapter ? 'type-chapter' : (isSection ? 'type-section' : 'type-entity');

  let html = `<div class="detail-card">`;
  html += `<div class="detail-title">${{node.fullLabel || node.label}}</div>`;
  html += `<span class="detail-type ${{typeClass}}">${{typeLabel}}</span>`;
  if (node.entityCount > 0) html += `<span style="margin-left:8px;font-size:12px;color:#888;">${{node.entityCount}} 个概念</span>`;
  html += `</div>`;

  // ── 定义展示（实体节点核心功能）──
  if (isEntity && node.definition) {{
    html += `<div class="def-box">
      <div class="def-label">📖 书中原文定义</div>
      <div class="def-text">${{node.definition}}</div>
      <div class="def-source">来源：${{node.defChapter || ''}}</div>
    </div>`;
  }}

  // ── 子节点列表 ──
  const neighbors = network.getConnectedNodes(nodeId);
  const connectedEdges = network.getConnectedEdges(nodeId);

  if (isChapter) {{
    const sections = neighbors.filter(nid => {{ const n = nodesData.get(nid); return n && n.group === 'section'; }});
    const entities = neighbors.filter(nid => {{ const n = nodesData.get(nid); return n && n.group === 'entity'; }});
    if (sections.length > 0) {{
      html += `<div class="detail-relations"><h4>📖 包含节 (${{sections.length}})</h4>`;
      sections.forEach(sid => {{
        const s = nodesData.get(sid);
        if (s) html += `<div class="relation-item" onclick="focusNode('${{sid}}')"><span class="rel-subject">▸ ${{s.label}}</span></div>`;
      }});
      html += `</div>`;
    }}
    if (entities.length > 0) {{
      html += `<div class="detail-relations"><h4>🏷️ 核心概念 (${{entities.length}})</h4>`;
      entities.forEach(eid => {{
        const e = nodesData.get(eid);
        if (e) html += `<div class="relation-item" onclick="focusNode('${{eid}}')"><span class="rel-object">● ${{e.fullLabel || e.label}}</span></div>`;
      }});
      html += `</div>`;
    }}
  }}

  if (isSection) {{
    const parent = neighbors.filter(nid => {{ const n = nodesData.get(nid); return n && n.group === 'chapter'; }});
    if (parent.length > 0) {{
      html += `<div class="detail-relations"><h4>🔗 所属章节</h4>`;
      parent.forEach(pid => {{
        const p = nodesData.get(pid);
        if (p) html += `<div class="relation-item" onclick="focusNode('${{pid}}')"><span class="rel-subject">▸ ${{p.fullLabel || p.label}}</span></div>`;
      }});
      html += `</div>`;
    }}
  }}

  if (isEntity) {{
    // 找同章其他概念
    const siblings = neighbors.filter(nid => {{ const n = nodesData.get(nid); return n && (n.group === 'chapter' || n.group === 'entity'); }});
    const chNode = siblings.find(nid => {{ const n = nodesData.get(nid); return n && n.group === 'chapter'; }});
    if (chNode) {{
      const chAllEntities = nodesData.get().filter(n => n.group === 'entity' && n.parent === chNode);
      if (chAllEntities.length > 1) {{
        html += `<div class="detail-relations"><h4>🏷️ 同章其他概念</h4>`;
        chAllEntities.forEach(e => {{
          if (e.id !== nodeId) {{
            html += `<div class="relation-item" onclick="focusNode('${{e.id}}')"><span class="entity-tag">${{e.fullLabel || e.label}}</span></div>`;
          }}
        }});
        html += `</div>`;
      }}
    }}
  }}

  detail.innerHTML = html;
  network.selectNodes([nodeId], false);
  network.setSelection({{ nodes: [nodeId], edges: connectedEdges }});
}}

function focusNode(nodeId) {{
  network.focus(nodeId, {{ scale: 1.5, animation: true }});
  showNodeDetail(nodeId);
}}

function clearSelection() {{
  document.getElementById('detail').style.display = 'none';
  document.getElementById('empty').style.display = 'block';
  document.getElementById('searchResults').style.display = 'none';
  document.getElementById('searchInput').value = '';
  network.selectNodes([], false);
  network.setSelection({{ nodes: [], edges: [] }});
}}

function searchNodes(query) {{
  const searchRes = document.getElementById('searchResults');
  const detail = document.getElementById('detail');
  const empty = document.getElementById('empty');

  if (!query.trim()) {{
    searchRes.style.display = 'none';
    if (detail.style.display !== 'block') empty.style.display = 'block';
    return;
  }}

  const q = query.toLowerCase();
  const allNodes = nodesData.get();
  const matches = allNodes.filter(n =>
    (n.fullLabel && n.fullLabel.toLowerCase().includes(q)) ||
    (n.label && n.label.toLowerCase().includes(q)) ||
    (n.definition && n.definition.toLowerCase().includes(q))
  ).slice(0, 30);

  empty.style.display = 'none';
  detail.style.display = 'none';
  searchRes.style.display = 'block';

  if (matches.length === 0) {{
    searchRes.innerHTML = '<div style="color:#999;padding:20px;text-align:center;">未找到匹配节点</div>';
    return;
  }}

  let html = `<div style="font-size:13px;color:#555;margin-bottom:8px;">找到 ${{matches.length}} 个匹配节点：</div>`;
  matches.forEach(n => {{
    const icon = n.group === 'chapter' ? '📘' : (n.group === 'section' ? '📄' : '🏷️');
    html += `<div class="relation-item" onclick="focusNode('${{n.id}}')">
      <span>${{icon}}</span>
      <span class="${{n.group === 'entity' ? 'rel-object' : 'rel-subject'}}">${{n.fullLabel || n.label}}</span>
      <span style="font-size:11px;color:#999;">[${{n.group === 'chapter' ? '章' : n.group === 'section' ? '节' : '概念'}}]</span>
    </div>`;
  }});
  searchRes.innerHTML = html;
}}

document.addEventListener('keydown', function(e) {{
  if (e.key === 'Escape') clearSelection();
  if (e.key === 'f' || e.key === 'F') fitAll();
  if (e.key === '1') setLayout('hierarchical');
  if (e.key === '2') setLayout('network');
}});

init();
</script>
</body>
</html>'''

    html = html.replace('__NODES_DATA__', nodes_json)
    html = html.replace('__EDGES_DATA__', edges_json)

    return html


# =========================================================
#  6. Mermaid 生成（保留原功能）
# =========================================================

def generate_mermaid(toc, chapter_nums=None):
    filtered = select_chapters(toc, chapter_nums) if chapter_nums else toc
    chapters = [item for item in filtered if item[0] == 0]
    ch_names = [c[1] for c in chapters]
    if not ch_names:
        return "flowchart TD\n    A[\"无数据\"]"

    lines = ["flowchart TD", "",
             "    classDef ch fill:#4A90D9,color:#fff,stroke:#2E5A8A,stroke-width:2px",
             "    classDef sec fill:#E8F4FD,color:#333,stroke:#50C878,stroke-width:1px", ""]

    if len(ch_names) == 1:
        ch_name = ch_names[0]
        ch_num = re.search(r'\d+', ch_name).group() if re.search(r'\d+', ch_name) else "0"
        ch_idx = int(ch_num) - 1
        c = CH_COLORS[ch_idx] if ch_idx < len(CH_COLORS) else "#4A90D9"
        s = CH_STROKES[ch_idx] if ch_idx < len(CH_STROKES) else "#2E5A8A"
        lines.append(f'    subgraph {ch_name.replace(" ","_")}["{ch_name}"]')
        lines.append('        direction TB')
        lines.append(f'        classDef sub_ch fill:{c},color:#fff,stroke:{s},stroke-width:2px')
        lines.append(f'        classDef sub_sec fill:#E8F4FD,color:#333,stroke:{s},stroke-width:1px')
        lines.append(f'        CH_{ch_num}["{ch_name}"]:::sub_ch')
        lines.append('')
        sc = 0
        for item in filtered:
            if item[0] == 1:
                lb = item[1].replace('"', "'")
                lines.append(f'        SEC_{ch_num}_{sc}["{lb}"]:::sub_sec')
                lines.append(f'        CH_{ch_num} --> SEC_{ch_num}_{sc}')
                sc += 1
        # 实体
        ents = get_chapter_entities(ch_name)
        if ents:
            for i, ent in enumerate(ents):
                if len(ent) <= 20:
                    eid = f"ENT_{ch_num}_{i}"
                    lines.append(f'        {eid}["{ent}"]:::entity')
                    lines.append(f'        CH_{ch_num} -.-> {eid}')
        lines.append('    end')
    else:
        ch_nodes = {}
        for i, cn in enumerate(ch_names):
            nid = f"CH_{i}"
            ch_nodes[cn] = nid
            ents = get_chapter_entities(cn)
            suf = f" (E:{len(ents)})" if ents else ""
            lines.append(f'    {nid}["{cn}{suf}"]:::ch')
        lines.append('')
        ci = -1
        cur = None
        for item in filtered:
            if item[0] == 0:
                cur = item[1]; ci += 1; continue
            if item[0] == 1 and cur:
                nid = f"SEC_{ci}_{abs(hash(item[1]))%10000}"
                pid = ch_nodes.get(cur)
                if pid:
                    lines.append(f'    {nid}["{item[1]}"]:::sec')
                    lines.append(f'    {pid} --> {nid}')
        lines.append('')
        cnl = list(ch_nodes.keys())
        for i in range(len(cnl) - 1):
            lines.append(f'    {ch_nodes[cnl[i]]} ==> {ch_nodes[cnl[i+1]]}')

    return '\n'.join(lines)


# =========================================================
#  7. 主入口
# =========================================================

def main():
    parser = argparse.ArgumentParser(
        description="《知识图谱 方法、实践与应用》交互式知识图谱（带原文定义）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python gen_interactive_graph.py              → 全书交互图谱（带定义）
  python gen_interactive_graph.py 3            → 第3章
  python gen_interactive_graph.py 1-5          → 第1~5章
  python gen_interactive_graph.py 2 4 6        → 第2、4、6章
  python gen_interactive_graph.py 3 --mmd      → 同时输出 Mermaid""",
    )
    parser.add_argument("chapters", nargs="*")
    parser.add_argument("-o", "--output")
    parser.add_argument("--mmd", action="store_true")
    args = parser.parse_args()

    # 解析章节
    chapter_nums = set()
    for arg in args.chapters:
        if '-' in arg:
            parts = arg.split('-')
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                chapter_nums.update(range(int(parts[0]), int(parts[1]) + 1))
        elif arg.isdigit():
            chapter_nums.add(int(arg))
    if chapter_nums:
        invalid = [n for n in chapter_nums if n < 1 or n > 9]
        if invalid:
            print(f"⚠️ 无效章节号: {invalid}（有效范围 1-9）")
            sys.exit(1)
    chapter_nums = sorted(chapter_nums) if chapter_nums else None

    # 加载数据
    with open(BOOK_TEXT, encoding='utf-8') as f:
        toc = parse_toc(f.read())

    definitions = load_definitions()
    print(f"📖 已加载 {len(definitions)} 个实体定义")

    # 构建图数据
    nodes, edges = build_graph_data(toc, definitions, chapter_nums)

    if not nodes:
        print("⚠️ 未找到数据")
        sys.exit(1)

    # 输出 HTML
    if args.output:
        html_path = args.output
    elif chapter_nums and len(chapter_nums) == 1:
        html_path = rf'e:\nlp\ltp\kg_ch{chapter_nums[0]}_interactive.html'
    elif chapter_nums:
        label = '-'.join(str(n) for n in chapter_nums[:3])
        label += f'+{len(chapter_nums)-3}' if len(chapter_nums) > 3 else ''
        html_path = rf'e:\nlp\ltp\kg_ch{label}_interactive.html'
    else:
        html_path = rf'e:\nlp\ltp\kg_book_interactive.html'

    html = generate_interactive_html(nodes, edges, chapter_nums)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    ch_count = sum(1 for n in nodes if n.get("group") == "chapter")
    sec_count = sum(1 for n in nodes if n.get("group") == "section")
    ent_count = sum(1 for n in nodes if n.get("group") == "entity")
    def_count = sum(1 for n in nodes if n.get("definition", ""))
    ch_label = f"第{'、'.join(str(n) for n in chapter_nums)}章" if chapter_nums else "全书"
    print(f"✅ 交互式 HTML: {html_path}")
    print(f"   图谱: {ch_label} | 章:{ch_count} 节:{sec_count} 概念:{ent_count} | 带定义:{def_count}/{ent_count} | 边:{len(edges)}")

    # Mermaid
    if args.mmd:
        mmd = generate_mermaid(toc, chapter_nums)
        mmd_path = html_path.replace('.html', '.mmd')
        with open(mmd_path, 'w', encoding='utf-8') as f:
            f.write(mmd)
        print(f"✅ Mermaid: {mmd_path}")

    print(f"\n💡 快捷键: [1]树形 [2]网状 [F]适应 [Esc]取消选中 | 搜索框支持全文搜索")


if __name__ == '__main__':
    main()