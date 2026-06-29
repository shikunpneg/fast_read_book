"""
kg_app - 知识图谱交互书 Web 应用
提供文件上传、知识图谱构建、在线阅读功能
"""
import os
import sys
import json
import uuid
import threading
from pathlib import Path

from flask import Flask, request, render_template, jsonify, send_from_directory, url_for

# 确保 kg_core 可导入
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from kg_core import KnowledgeGraphBuilder, SummaryGenerator

# 显式指定模板和静态文件路径（解决 CWD 导致的路径解析问题）
APP_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = str(APP_DIR / 'templates')
STATIC_DIR = str(APP_DIR / 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)


@app.after_request
def add_no_cache(response):
    """禁用浏览器缓存，确保每次获取最新内容"""
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
app.secret_key = 'kg-book-tool-secret-key'

# 配置
UPLOAD_FOLDER = APP_DIR / 'static' / 'uploads'
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

# 任务状态存储
tasks = {}


@app.route('/')
def index():
    """首页 - 上传界面"""
    return render_template('index.html')


@app.route('/reader')
def reader():
    """阅读页面 - 展示知识图谱"""
    book_id = request.args.get('book', '')
    data_file = request.args.get('data', f'{book_id}_data.js')
    text_file = request.args.get('text', f'{book_id}_book.md')

    # 从任务或文件名推断书名
    book_name = request.args.get('name', '知识图谱')
    book_title = request.args.get('title', '点击节点查看详情')

    return render_template('reader.html',
                           BOOK_NAME=book_name,
                           BOOK_TITLE=book_title,
                           data_file=data_file,
                           text_file=text_file)


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传书籍文件"""
    if 'file' not in request.files:
        return jsonify({'error': '未选择文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '文件名为空'}), 400

    # 保存文件
    task_id = str(uuid.uuid4())[:8]
    ext = Path(file.filename).suffix
    safe_name = f"{task_id}{ext}"
    filepath = UPLOAD_FOLDER / safe_name
    file.save(str(filepath))

    tasks[task_id] = {
        'id': task_id,
        'filename': file.filename,
        'filepath': str(filepath),
        'status': 'uploaded',
        'progress': 0,
        'message': '文件上传成功',
    }

    return jsonify({'task_id': task_id, 'filename': file.filename})


@app.route('/api/build', methods=['POST'])
def build_knowledge_graph():
    """启动知识图谱构建任务"""
    data = request.get_json()
    task_id = data.get('task_id')
    enable_summary = data.get('summary', False)
    model_name = data.get('model', 'qwen2.5:3b')

    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404

    task = tasks[task_id]
    if task['status'] not in ('uploaded', 'failed'):
        return jsonify({'error': f'任务状态异常: {task["status"]}'}), 400

    task['status'] = 'building'
    task['progress'] = 0
    task['message'] = '开始构建...'

    # 异步构建
    def build_async():
        try:
            task['message'] = '正在加载书籍...'
            task['progress'] = 10

            builder = KnowledgeGraphBuilder(task['filepath'], model_name=model_name)
            builder.load_book()

            task['message'] = '正在提取实体...'
            task['progress'] = 30

            # 检查是否有已有数据
            builder.extract_entities()

            task['message'] = '正在提取定义和段落...'
            task['progress'] = 50
            builder.extract_definitions_and_paragraphs()

            task['message'] = '正在构建关系...'
            task['progress'] = 70
            builder.build_relations()

            if enable_summary:
                task['message'] = '正在生成 LLM 摘要...'
                task['progress'] = 80
                gen = SummaryGenerator(builder.data, model=model_name)
                gen.generate(heading_only=True)
                task['progress'] = 95

            # 保存结果
            output_json = str(UPLOAD_FOLDER / f"{task_id}_result.json")
            builder.save_json(output_json)

            # 保存 JS 数据文件
            output_js = str(UPLOAD_FOLDER / f"{task_id}_data.js")
            builder.save_js(output_js)

            # 保存原始 Markdown 文件（供阅读页面加载原文）
            book_name = task.get('filename', task_id)
            output_md = str(UPLOAD_FOLDER / f"{task_id}_book.md")
            builder.save_md(output_md, book_name=Path(book_name).stem)

            stats = builder.get_stats()

            task['status'] = 'completed'
            task['progress'] = 100
            task['message'] = '构建完成'
            task['result'] = {
                'json_path': f'/static/uploads/{task_id}_result.json',
                'js_path': f'/static/uploads/{task_id}_data.js',
                'md_path': f'/static/uploads/{task_id}_book.md',
                'data_file': f'{task_id}_data.js',
                'text_file': f'{task_id}_book.md',
                'book_name': Path(book_name).stem,
                'stats': stats,
            }

        except Exception as e:
            task['status'] = 'failed'
            task['message'] = f'构建失败: {str(e)}'

    thread = threading.Thread(target=build_async)
    thread.daemon = True
    thread.start()

    return jsonify({'task_id': task_id, 'status': 'building'})


@app.route('/api/status/<task_id>')
def get_status(task_id):
    """查询构建任务状态"""
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404

    task = tasks[task_id]
    return jsonify({
        'id': task['id'],
        'status': task['status'],
        'progress': task['progress'],
        'message': task['message'],
        'result': task.get('result'),
    })


def read_file_safe(filepath):
    """安全读取文件，自动检测编码"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin-1']
    for enc in encodings:
        try:
            with open(filepath, encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    with open(filepath, encoding='utf-8', errors='replace') as f:
        return f.read()


@app.route('/api/entities/<task_id>')
def get_entities(task_id):
    """获取实体数据"""
    filepath = UPLOAD_FOLDER / f"{task_id}_result.json"
    if not filepath.exists():
        return jsonify({'error': '数据文件不存在'}), 404

    for enc in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
        try:
            with open(filepath, encoding=enc) as f:
                data = json.load(f)
            break
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    else:
        return jsonify({'error': '无法读取数据文件'}), 500
    return jsonify(data)


@app.route('/api/text/<task_id>')
def get_text(task_id):
    """获取书籍原文"""
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404

    filepath = Path(tasks[task_id]['filepath'])
    if not filepath.exists():
        return jsonify({'error': '文件不存在'}), 404

    text = read_file_safe(str(filepath))
    return jsonify({'content': text})


@app.route('/static/<path:filename>')
def static_files(filename):
    """静态文件服务"""
    return send_from_directory(str(BASE_DIR / 'kg_app' / 'static'), filename)


# ============================================================
# Ollama LLM 管理 API
# ============================================================
@app.route('/api/llm/models')
def api_llm_models():
    """获取 Ollama 已安装的模型列表"""
    try:
        import requests
        resp = requests.get('http://localhost:11434/api/tags', timeout=5)
        if resp.status_code != 200:
            return jsonify({'error': f'Ollama 返回 {resp.status_code}'}), 502
        models = resp.json().get('models', [])
        return jsonify({
            'ok': True,
            'models': [{
                'name': m.get('name', ''),
                'size': m.get('size', 0),
                'size_gb': round(m.get('size', 0) / 1024 / 1024 / 1024, 2),
                'modified': m.get('modified_at', ''),
            } for m in models]
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': f'Ollama 未运行: {e}'}), 503


@app.route('/api/llm/pull', methods=['POST'])
def api_llm_pull():
    """异步拉取 Ollama 模型。SSE 推送进度。"""
    from flask import Response, stream_with_context
    data = request.get_json() or {}
    model_name = data.get('name', '').strip()
    if not model_name:
        return jsonify({'error': '模型名不能为空'}), 400

    def generate():
        try:
            import requests
            with requests.post(
                'http://localhost:11434/api/pull',
                json={'name': model_name, 'stream': True},
                stream=True, timeout=600
            ) as resp:
                for line in resp.iter_lines():
                    if not line:
                        continue
                    try:
                        payload = json.loads(line.decode('utf-8'))
                        status = payload.get('status', '')
                        completed = payload.get('completed', 0)
                        total = payload.get('total', 0)
                        pct = round(completed / total * 100, 1) if total else 0
                        msg = f"{status} {pct}%" if total else status
                        yield f"data: {json.dumps({'status': status, 'pct': pct, 'msg': msg}, ensure_ascii=False)}\n\n"
                        if status == 'success':
                            yield f"data: {json.dumps({'status': 'success', 'pct': 100, 'msg': '下载完成'})}\n\n"
                            break
                    except Exception as e:
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': f'拉取失败: {e}'})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


# ============================================================
# 系统诊断 API
# ============================================================
@app.route('/api/diag')
def api_diag():
    """运行系统诊断，返回 JSON 结果"""
    import importlib
    import socket
    results = []

    # 1. Python 环境
    results.append({'name': 'Python 环境', 'items': [
        {'label': 'Python 版本', 'ok': True, 'detail': f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'},
    ]})

    # 关键包
    for pkg in ['flask', 'requests', 'jinja2', 'werkzeug', 'webview', 'waitress']:
        try:
            importlib.import_module(pkg)
            results[-1]['items'].append({'label': f'包 {pkg}', 'ok': True})
        except ImportError:
            results[-1]['items'].append({'label': f'包 {pkg}', 'ok': False, 'detail': '未安装'})

    # kg_core
    try:
        import kg_core
        results[-1]['items'].append({'label': f'kg_core v{kg_core.__version__}', 'ok': True})
    except ImportError:
        results[-1]['items'].append({'label': 'kg_core', 'ok': False, 'detail': '未安装'})

    # 2. 端口
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    port_ok = sock.connect_ex(('127.0.0.1', 5000)) == 0
    sock.close()
    results.append({'name': '服务端口', 'items': [
        {'label': '端口 5000', 'ok': port_ok, 'detail': '已占用 (服务运行中)' if port_ok else '空闲'},
    ]})

    # 3. Ollama
    try:
        import requests as req
        resp = req.get('http://localhost:11434/api/tags', timeout=5)
        if resp.status_code == 200:
            models = [m['name'] for m in resp.json().get('models', [])]
            has_qwen = any('qwen' in m.lower() for m in models)
            results.append({'name': 'Ollama 服务', 'items': [
                {'label': 'Ollama 运行状态', 'ok': True},
                {'label': 'qwen 模型', 'ok': has_qwen, 'detail': f'{len(models)} 个模型可用' if has_qwen else '未安装 qwen 模型'},
            ]})
        else:
            results.append({'name': 'Ollama 服务', 'items': [
                {'label': 'Ollama', 'ok': False, 'detail': f'状态码 {resp.status_code}'},
            ]})
    except Exception as e:
        results.append({'name': 'Ollama 服务', 'items': [
            {'label': 'Ollama', 'ok': False, 'detail': '未运行，AI 摘要不可用'},
        ]})

    # 4. 文件结构
    core_files = [
        ('kg_core/__init__.py', BASE_DIR / 'kg_core' / '__init__.py'),
        ('kg_core/builder.py', BASE_DIR / 'kg_core' / 'builder.py'),
        ('kg_core/summarizer.py', BASE_DIR / 'kg_core' / 'summarizer.py'),
        ('kg_core/cli.py', BASE_DIR / 'kg_core' / 'cli.py'),
        ('kg_app/main.py', BASE_DIR / 'kg_app' / 'main.py'),
        ('kg_app/gui.py', BASE_DIR / 'kg_app' / 'gui.py'),
        ('templates/index.html', BASE_DIR / 'kg_app' / 'templates' / 'index.html'),
        ('templates/reader.html', BASE_DIR / 'kg_app' / 'templates' / 'reader.html'),
        ('static/kg_v7.js', BASE_DIR / 'kg_app' / 'static' / 'kg_v7.js'),
        ('static/kg_v7.css', BASE_DIR / 'kg_app' / 'static' / 'kg_v7.css'),
    ]
    items = []
    for name, path in core_files:
        items.append({'label': name, 'ok': path.exists(), 'detail': '缺失' if not path.exists() else ''})
    results.append({'name': '核心文件', 'items': items})

    # 5. 上传目录
    upload_ok = UPLOAD_FOLDER.exists()
    writable = False
    if upload_ok:
        try:
            test = UPLOAD_FOLDER / '.w_test'
            test.write_text('t')
            test.unlink()
            writable = True
        except Exception:
            pass
    results.append({'name': '上传目录', 'items': [
        {'label': '目录存在', 'ok': upload_ok},
        {'label': '可写', 'ok': writable},
    ]})

    # 汇总
    all_ok = all(item['ok'] for group in results for item in group['items'])
    return jsonify({'ok': all_ok, 'results': results})


# ============================================================
# 启动入口
# ============================================================
def main():
    print("=" * 50)
    print("知识图谱交互书 - Web 应用")
    print("=" * 50)
    print(f"  上传目录: {UPLOAD_FOLDER}")
    print(f"  访问地址: http://localhost:5000")
    print("=" * 50)

    # 尝试使用 waitress 生产服务器
    try:
        from waitress import serve
        print("使用 waitress 生产服务器")
        serve(app, host='127.0.0.1', port=5000, threads=4)
    except ImportError:
        print("使用 Flask 开发服务器")
        app.run(host='127.0.0.1', port=5000, debug=True)


if __name__ == '__main__':
    main()