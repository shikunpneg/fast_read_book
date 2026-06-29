"""
知识图谱项目全面诊断工具
检查所有组件状态，快速定位问题
"""
import os
import sys
import json
import socket
import subprocess
import importlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

PASS = '\033[92m✓\033[0m'
FAIL = '\033[91m✗\033[0m'
WARN = '\033[93m⚠\033[0m'


def check(label, condition, detail=''):
    status = PASS if condition else FAIL
    print(f"  {status} {label}")
    if detail and not condition:
        print(f"     {detail}")
    return condition


def main():
    all_ok = True

    print("=" * 60)
    print("  知识图谱项目 - 全面诊断")
    print("=" * 60)

    # ── 1. Python 环境 ──
    print("\n[1] Python 环境")
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    all_ok &= check(f"Python 版本: {py_ver}", sys.version_info >= (3, 8))

    # 关键包
    for pkg in ['flask', 'requests', 'jinja2', 'werkzeug']:
        try:
            importlib.import_module(pkg)
            all_ok &= check(f"包 {pkg}", True)
        except ImportError:
            all_ok &= check(f"包 {pkg}", False, f"pip install {pkg}")

    # pywebview
    try:
        importlib.import_module('webview')
        all_ok &= check("包 webview (pywebview)", True)
    except ImportError:
        all_ok &= check("包 webview (pywebview)", False, "pip install pywebview")

    # waitress
    try:
        importlib.import_module('waitress')
        all_ok &= check("包 waitress", True)
    except ImportError:
        all_ok &= check("包 waitress", False, "pip install waitress")

    # kg_core
    try:
        import kg_core
        all_ok &= check(f"包 kg_core v{kg_core.__version__}", True)
    except ImportError:
        all_ok &= check("包 kg_core", False, "pip install -e .")

    # ── 2. 端口检查 ──
    print("\n[2] 端口 5000")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    port_in_use = sock.connect_ex(('127.0.0.1', 5000)) == 0
    sock.close()
    if port_in_use:
        all_ok &= check("端口 5000 已占用 (服务可能正在运行)", True)
    else:
        all_ok &= check("端口 5000 空闲", False, "服务未启动! 运行: python kg_app/main.py")

    # ── 3. Flask 服务响应 ──
    print("\n[3] Flask 服务响应")
    if port_in_use:
        try:
            import urllib.request
            resp = urllib.request.urlopen('http://127.0.0.1:5000', timeout=3)
            all_ok &= check(f"HTTP 响应: {resp.status}", resp.status == 200)
        except Exception as e:
            all_ok &= check(f"HTTP 响应", False, str(e))
    else:
        print(f"  {WARN} 跳过 (服务未启动)")

    # ── 4. Ollama 服务 ──
    print("\n[4] Ollama 服务")
    try:
        import requests
        resp = requests.get('http://localhost:11434/api/tags', timeout=5)
        if resp.status_code == 200:
            models = [m['name'] for m in resp.json().get('models', [])]
            all_ok &= check("Ollama 服务运行中", True)
            has_qwen = any('qwen' in m.lower() for m in models)
            all_ok &= check(f"qwen 模型可用 ({len(models)} 个模型)", has_qwen,
                          "ollama pull qwen2.5:3b" if not has_qwen else "")
        else:
            all_ok &= check("Ollama 服务", False, f"状态码: {resp.status_code}")
    except Exception as e:
        all_ok &= check("Ollama 服务", False, "Ollama 未运行，AI 摘要功能不可用")

    # ── 5. 文件结构 ──
    print("\n[5] 核心文件")

    def file_ok(path, desc):
        exists = Path(path).exists()
        return check(desc, exists, f"缺失: {path}")

    all_ok &= file_ok(BASE_DIR / 'kg_core' / '__init__.py', 'kg_core/__init__.py')
    all_ok &= file_ok(BASE_DIR / 'kg_core' / 'builder.py', 'kg_core/builder.py')
    all_ok &= file_ok(BASE_DIR / 'kg_core' / 'summarizer.py', 'kg_core/summarizer.py')
    all_ok &= file_ok(BASE_DIR / 'kg_core' / 'text_cleaner.py', 'kg_core/text_cleaner.py')
    all_ok &= file_ok(BASE_DIR / 'kg_core' / 'cli.py', 'kg_core/cli.py')
    all_ok &= file_ok(BASE_DIR / 'kg_app' / 'main.py', 'kg_app/main.py')
    all_ok &= file_ok(BASE_DIR / 'kg_app' / 'gui.py', 'kg_app/gui.py')
    all_ok &= file_ok(BASE_DIR / 'setup.py', 'setup.py')
    all_ok &= file_ok(BASE_DIR / 'build_exe.py', 'build_exe.py')

    # ── 6. 模板文件 ──
    print("\n[6] 模板文件")
    all_ok &= file_ok(BASE_DIR / 'kg_app' / 'templates' / 'index.html', 'templates/index.html')
    all_ok &= file_ok(BASE_DIR / 'kg_app' / 'templates' / 'reader.html', 'templates/reader.html')
    all_ok &= file_ok(BASE_DIR / 'kg_app' / 'static' / 'kg_v7.js', 'static/kg_v7.js')
    all_ok &= file_ok(BASE_DIR / 'kg_app' / 'static' / 'kg_v7.css', 'static/kg_v7.css')

    # ── 7. 上传目录 ──
    print("\n[7] 上传目录")
    upload_dir = BASE_DIR / 'kg_app' / 'static' / 'uploads'
    if upload_dir.exists():
        all_ok &= check(f"uploads/ 存在 ({len(list(upload_dir.glob('*')))} 个文件)", True)
    else:
        try:
            upload_dir.mkdir(parents=True, exist_ok=True)
            all_ok &= check("uploads/ 已创建", True)
        except Exception as e:
            all_ok &= check("uploads/", False, str(e))

    # 可写测试
    try:
        test_file = upload_dir / '.write_test'
        test_file.write_text('test')
        test_file.unlink()
        all_ok &= check("uploads/ 可写", True)
    except Exception as e:
        all_ok &= check("uploads/ 可写", False, str(e))

    # ── 8. 数据文件 ──
    print("\n[8] 数据文件")
    v7_json = BASE_DIR / 'kg_entity_v7.json'
    v7_js = BASE_DIR / 'kg_entity_v7.js'

    if v7_json.exists():
        try:
            with open(v7_json, encoding='utf-8') as f:
                data = json.load(f)
            all_ok &= check(f"kg_entity_v7.json ({len(data)} 个实体)", True)
        except Exception as e:
            all_ok &= check("kg_entity_v7.json", False, str(e))
    else:
        all_ok &= check("kg_entity_v7.json", False, "数据文件不存在，需要运行构建")

    if v7_js.exists():
        size_kb = v7_js.stat().st_size / 1024
        all_ok &= check(f"kg_entity_v7.js ({size_kb:.0f} KB)", True)
    else:
        all_ok &= check("kg_entity_v7.js", False, "运行: python scripts/build_v7.py")

    # ── 9. kg-build CLI ──
    print("\n[9] kg-build CLI")
    try:
        result = subprocess.run([sys.executable, '-m', 'kg_core.cli', '--help'],
                              capture_output=True, text=True, timeout=5)
        all_ok &= check("kg-build --help", result.returncode == 0, result.stderr[:200])
    except Exception as e:
        all_ok &= check("kg-build CLI", False, str(e))

    # ── 汇总 ──
    print("\n" + "=" * 60)
    if all_ok:
        print(f"  {PASS} 所有检查通过! 项目状态正常")
    else:
        print(f"  {FAIL} 存在未通过项，请根据上述提示修复")
    print("=" * 60)

    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())