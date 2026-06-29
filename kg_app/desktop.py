"""
kg_app 原生桌面应用 - 基于 Tkinter 的 Windows 原生 GUI
直接调用核心引擎，内置 Flask 服务（线程内启动）
"""
import os
import sys
import json
import time
import threading
import socket
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from urllib.parse import quote

# 确保导入路径
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from kg_core import KnowledgeGraphBuilder, SummaryGenerator


def start_flask_server():
    """在后台线程启动 Flask 服务"""
    from kg_app.main import app
    try:
        from waitress import serve
        serve(app, host='127.0.0.1', port=5000, threads=4)
    except ImportError:
        app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)


def is_port_open(port=5000):
    """检查端口是否已开放"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = s.connect_ex(('127.0.0.1', port)) == 0
    s.close()
    return result


class DesktopApp:
    """知识图谱交互书 - 原生桌面应用"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("知识图谱交互书")
        self.root.geometry("700x520")
        self.root.minsize(600, 460)
        self.root.resizable(True, True)

        # 居中
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 700, 520
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        self.style = ttk.Style()
        self.style.theme_use('clam')

        # 变量
        self.file_path = tk.StringVar()
        self.enable_summary = tk.BooleanVar(value=False)
        self.model_name = tk.StringVar(value='qwen2.5:3b')
        self.status_text = tk.StringVar(value='正在启动服务...')
        self.server_status = tk.StringVar(value='')
        self.building = False
        self._last_task_id = None

        self._build_ui()

        # 启动 Flask 服务线程
        self._start_server()

    def _start_server(self):
        """启动 Flask 服务线程并等待就绪"""
        if not is_port_open(5000):
            t = threading.Thread(target=start_flask_server, daemon=True)
            t.start()
            # 等待服务就绪
            for _ in range(30):  # 最多等 15 秒
                time.sleep(0.5)
                if is_port_open(5000):
                    self._set_status('准备就绪 - 服务已启动')
                    self._set_server_status('服务运行中', True)
                    return
            self._set_status('服务启动超时')
            self._set_server_status('服务未启动', False)
        else:
            self._set_status('准备就绪 - 服务运行中')
            self._set_server_status('服务运行中', True)

    def _set_server_status(self, text, ok):
        color = '#2e7d32' if ok else '#c62828'
        self.root.after(0, lambda: self.server_status.set(text))
        self.root.after(0, lambda: self.lbl_server.configure(foreground=color))

    def _build_ui(self):
        """构建界面"""
        main = ttk.Frame(self.root, padding=20)
        main.pack(fill='both', expand=True)

        # === 标题 ===
        ttk.Label(main, text="知识图谱交互书", font=('Microsoft YaHei', 18, 'bold')).pack(anchor='center')
        ttk.Label(main, text="将电子书转换为可交互的知识图谱", font=('Microsoft YaHei', 10),
                  foreground='#666').pack(anchor='center', pady=(4, 20))

        # === 文件选择 ===
        file_frame = ttk.LabelFrame(main, text="选择文件", padding=12)
        file_frame.pack(fill='x', pady=(0, 12))

        file_row = ttk.Frame(file_frame)
        file_row.pack(fill='x')
        ttk.Entry(file_row, textvariable=self.file_path, font=('Microsoft YaHei', 10)).pack(
            side='left', fill='x', expand=True, padx=(0, 8))
        ttk.Button(file_row, text="浏览...", command=self._browse_file).pack(side='right')

        ttk.Label(file_frame, text="支持: PDF / EPUB / DOCX / PPTX / XLSX / HTML / 图片 / TXT / MD | 图像型PDF自动OCR",
                  font=('Microsoft YaHei', 8), foreground='#999').pack(anchor='w', pady=(6, 0))

        # === 选项 ===
        opt_frame = ttk.LabelFrame(main, text="构建选项", padding=12)
        opt_frame.pack(fill='x', pady=(0, 12))

        sum_row = ttk.Frame(opt_frame)
        sum_row.pack(fill='x', pady=(0, 8))
        ttk.Checkbutton(sum_row, text="生成 AI 摘要 (调用 Ollama LLM)", variable=self.enable_summary).pack(side='left')
        ttk.Label(sum_row, text="(需 Ollama 运行中)", font=('Microsoft YaHei', 8),
                  foreground='#999').pack(side='left', padx=8)

        model_row = ttk.Frame(opt_frame)
        model_row.pack(fill='x')
        ttk.Label(model_row, text="LLM 模型:", font=('Microsoft YaHei', 10)).pack(side='left', padx=(0, 8))
        model_combo = ttk.Combobox(model_row, textvariable=self.model_name, state='readonly',
                                   values=['qwen2.5:3b', 'qwen2.5:7b', 'llama3', 'deepseek-r1:7b'],
                                   font=('Microsoft YaHei', 10), width=18)
        model_combo.pack(side='left')

        # === 操作按钮 ===
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill='x', pady=(0, 12))

        self.btn_build = ttk.Button(btn_frame, text="开始构建", command=self._start_build)
        self.btn_build.pack(side='left', fill='x', expand=True, padx=(0, 6))

        self.btn_diag = ttk.Button(btn_frame, text="系统诊断", command=self._run_diag)
        self.btn_diag.pack(side='left', fill='x', expand=True, padx=(0, 6))

        self.btn_read = ttk.Button(btn_frame, text="打开阅读器", command=self._open_reader, state='disabled')
        self.btn_read.pack(side='left', fill='x', expand=True, padx=(0, 6))

        self.btn_llm = ttk.Button(btn_frame, text="下载LLM", command=self._show_llm_dialog)
        self.btn_llm.pack(side='left', fill='x', expand=True)

        # === 进度条 ===
        self.progress = ttk.Progressbar(main, mode='determinate', length=660)
        self.progress.pack(fill='x', pady=(0, 6))

        # === 状态 ===
        status_row = ttk.Frame(main)
        status_row.pack(fill='x')
        ttk.Label(status_row, textvariable=self.status_text, font=('Microsoft YaHei', 9),
                  foreground='#666').pack(side='left')

        self.lbl_server = ttk.Label(status_row, textvariable=self.server_status, font=('Microsoft YaHei', 8))
        self.lbl_server.pack(side='right', padx=(0, 8))

        ttk.Label(status_row, text="v1.0.0", font=('Microsoft YaHei', 8),
                  foreground='#bbb').pack(side='right')

    def _browse_file(self):
        """打开文件选择对话框"""
        path = filedialog.askopenfilename(
            title="选择电子书文件",
            filetypes=[
                ("所有支持格式", "*.pdf *.epub *.docx *.pptx *.xlsx *.html *.htm *.md *.txt *.png *.jpg *.jpeg *.bmp *.tiff *.webp"),
                ("PDF 文件", "*.pdf"),
                ("EPUB 文件", "*.epub"),
                ("Word 文档", "*.docx"),
                ("PowerPoint", "*.pptx"),
                ("Excel 表格", "*.xlsx"),
                ("网页文件", "*.html *.htm"),
                ("Markdown", "*.md"),
                ("图片 (OCR)", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp"),
                ("文本文件", "*.txt"),
                ("所有文件", "*.*"),
            ]
        )
        if path:
            self.file_path.set(path)
            self._set_status('文件已选择')

    def _set_status(self, msg):
        self.root.after(0, lambda: self.status_text.set(msg))

    def _set_progress(self, val):
        self.root.after(0, lambda: self.progress.configure(value=val))

    def _set_buttons(self, enabled):
        self.root.after(0, lambda: self.btn_build.configure(
            state='normal' if enabled else 'disabled',
            text='开始构建' if enabled else '构建中...'))
        self.root.after(0, lambda: self.btn_diag.configure(state='normal' if enabled else 'disabled'))

    def _start_build(self):
        """开始构建"""
        path = self.file_path.get().strip()
        if not path:
            messagebox.showwarning("提示", "请先选择文件")
            return
        if not os.path.exists(path):
            messagebox.showerror("错误", f"文件不存在:\n{path}")
            return

        self.building = True
        self._set_buttons(False)
        self._set_progress(0)
        self.btn_read.configure(state='disabled')

        thread = threading.Thread(target=self._do_build, args=(path,), daemon=True)
        thread.start()

    def _do_build(self, filepath):
        """后台构建线程"""
        try:
            self._set_status('正在加载文件...')
            self._set_progress(10)

            builder = KnowledgeGraphBuilder(filepath, model_name=self.model_name.get())
            builder.load_book()

            self._set_status('正在提取实体...')
            self._set_progress(30)
            builder.extract_entities()

            self._set_status('正在提取定义和段落...')
            self._set_progress(50)
            builder.extract_definitions_and_paragraphs()

            self._set_status('正在构建关系...')
            self._set_progress(70)
            builder.build_relations()

            stats = builder.get_stats()

            if self.enable_summary.get():
                self._set_status('正在生成 AI 摘要...')
                self._set_progress(80)
                gen = SummaryGenerator(builder.data, model=self.model_name.get())
                gen.generate(heading_only=True)
                self._set_progress(95)

            # 保存结果
            output_dir = BASE_DIR / 'kg_app' / 'static' / 'uploads'
            output_dir.mkdir(parents=True, exist_ok=True)

            # 使用 UUID 作为 task_id（ASCII），避免中文路径问题
            import uuid as _uuid
            task_id = _uuid.uuid4().hex[:8]
            output_json = str(output_dir / f"{task_id}_result.json")
            output_js = str(output_dir / f"{task_id}_data.js")
            output_md = str(output_dir / f"{task_id}_book.md")

            builder.save_json(output_json)
            builder.save_js(output_js)
            builder.save_md(output_md, book_name=Path(filepath).stem)

            self._set_progress(100)
            self._set_status(f'构建完成! {stats["total_entities"]} 个实体, {stats["total_relations"]} 条关系')

            self._last_task_id = task_id
            self._book_name = Path(filepath).stem
            self.root.after(0, lambda: self.btn_read.configure(state='normal'))

            messagebox.showinfo("完成",
                f"知识图谱构建完成!\n\n实体数: {stats['total_entities']}\n关系数: {stats['total_relations']}")

        except Exception as e:
            import traceback
            self._set_progress(0)
            self._set_status(f'构建失败: {e}')
            self.root.after(0, lambda: messagebox.showerror("构建失败",
                f"{e}\n\n详情请查看终端输出"))
            traceback.print_exc()
        finally:
            self.building = False
            self._set_buttons(True)

    def _run_diag(self):
        """运行系统诊断"""
        import importlib

        results = []

        # 1. Python 包
        items = [('Python 版本', True, f'{sys.version_info.major}.{sys.version_info.minor}')]
        for pkg in ['flask', 'requests', 'webview', 'waitress', 'fitz', 'ebooklib']:
            try:
                importlib.import_module(pkg)
                items.append((f'包 {pkg}', True, ''))
            except ImportError:
                items.append((f'包 {pkg}', False, '未安装'))
        try:
            import kg_core
            items.append((f'kg_core v{kg_core.__version__}', True, ''))
        except ImportError:
            items.append(('kg_core', False, '未安装'))
        results.append(('Python 环境', items))

        # 2. 端口
        port_ok = is_port_open(5000)
        results.append(('服务端口', [('端口 5000', port_ok, '已占用' if port_ok else '空闲')]))

        # 3. Ollama
        try:
            import requests
            resp = requests.get('http://localhost:11434/api/tags', timeout=5)
            has_qwen = any('qwen' in m['name'].lower() for m in resp.json().get('models', []))
            results.append(('Ollama', [
                ('服务运行', True, ''),
                ('qwen 模型', has_qwen, '' if has_qwen else '未安装'),
            ]))
        except Exception:
            results.append(('Ollama', [('服务运行', False, '未运行')]))

        # 4. 文件
        core_files = ['kg_core/__init__.py', 'kg_core/builder.py', 'kg_core/cli.py',
                      'kg_app/main.py', 'kg_app/gui.py', 'kg_app/desktop.py']
        file_items = []
        for f in core_files:
            ok = (BASE_DIR / f).exists()
            file_items.append((f, ok, '' if ok else '缺失'))
        results.append(('核心文件', file_items))

        # 显示对话框
        all_ok = all(item[1] for group in results for item in group[1])

        lines = []
        for group_name, items in results:
            lines.append(f"\n【{group_name}】")
            for label, ok, detail in items:
                icon = 'V' if ok else 'X'
                extra = f'  ({detail})' if detail else ''
                lines.append(f"  {icon} {label}{extra}")

        lines.append(f"\n{'='*40}")
        lines.append(f"{'V 所有检查通过' if all_ok else 'X 存在未通过项'}")
        messagebox.showinfo("系统诊断", '\n'.join(lines))

    def _show_llm_dialog(self):
        """LLM 模型下载对话框"""
        if not is_port_open(5000):
            messagebox.showerror("错误", "Flask 服务未启动，请重启应用")
            return

        import requests as req

        # 创建对话框
        dlg = tk.Toplevel(self.root)
        dlg.title("LLM 模型管理")
        dlg.geometry("520x420")
        dlg.transient(self.root)
        dlg.grab_set()

        ttk.Label(dlg, text="Ollama LLM 模型管理", font=('Microsoft YaHei', 14, 'bold')).pack(pady=10)

        # 已安装列表
        list_frame = ttk.LabelFrame(dlg, text="已安装的模型", padding=8)
        list_frame.pack(fill='both', expand=True, padx=12, pady=6)

        installed_list = tk.Listbox(list_frame, font=('Consolas', 10), height=6)
        installed_list.pack(fill='both', expand=True)

        def refresh_models():
            installed_list.delete(0, 'end')
            try:
                resp = req.get('http://127.0.0.1:5000/api/llm/models', timeout=5)
                data = resp.json()
                if data.get('ok'):
                    for m in data['models']:
                        installed_list.insert('end', f"{m['name']:30s}  {m['size_gb']:>6.2f} GB")
                    if not data['models']:
                        installed_list.insert('end', '(暂无已安装的模型)')
                else:
                    installed_list.insert('end', f"[错误] {data.get('error', '未知')}")
            except Exception as e:
                installed_list.insert('end', f"[错误] {e}")

        ttk.Button(list_frame, text="刷新列表", command=refresh_models).pack(pady=4)

        # 下载区
        download_frame = ttk.LabelFrame(dlg, text="下载新模型", padding=8)
        download_frame.pack(fill='x', padx=12, pady=6)

        row = ttk.Frame(download_frame)
        row.pack(fill='x', pady=4)
        ttk.Label(row, text="模型名:").pack(side='left')
        model_var = tk.StringVar(value='qwen2.5:3b')
        ttk.Entry(row, textvariable=model_var, font=('Consolas', 10)).pack(side='left', fill='x', expand=True, padx=6)

        # 进度条
        progress_var = tk.DoubleVar(value=0)
        progress = ttk.Progressbar(download_frame, variable=progress_var, maximum=100)
        progress.pack(fill='x', pady=4)

        status_var = tk.StringVar(value='就绪')
        ttk.Label(download_frame, textvariable=status_var, font=('Microsoft YaHei', 9)).pack()

        def do_pull():
            name = model_var.get().strip()
            if not name:
                return
            progress_var.set(0)
            status_var.set(f'开始下载 {name}...')
            btn_pull.configure(state='disabled')

            def stream():
                try:
                    with req.post('http://127.0.0.1:5000/api/llm/pull',
                                  json={'name': name}, stream=True, timeout=600) as resp:
                        for line in resp.iter_lines():
                            if not line:
                                continue
                            line = line.decode('utf-8', errors='replace')
                            if line.startswith('data:'):
                                payload = line[5:].strip()
                                try:
                                    obj = json.loads(payload)
                                    if 'pct' in obj:
                                        progress_var.set(obj['pct'])
                                    if 'msg' in obj:
                                        status_var.set(obj['msg'])
                                    if obj.get('status') == 'success':
                                        status_var.set('下载完成！')
                                        refresh_models()
                                        break
                                    if 'error' in obj:
                                        status_var.set(f"错误: {obj['error']}")
                                        break
                                except Exception:
                                    pass
                except Exception as e:
                    status_var.set(f"请求失败: {e}")
                finally:
                    btn_pull.configure(state='normal')

            threading.Thread(target=stream, daemon=True).start()

        btn_pull = ttk.Button(download_frame, text="开始下载", command=do_pull)
        btn_pull.pack(pady=4)

        # 推荐模型
        ttk.Label(download_frame, text="推荐: qwen2.5:3b (1.9G)  llama3 (4.7G)  deepseek-r1:7b (4.7G)",
                  font=('Microsoft YaHei', 8), foreground='#888').pack()

        refresh_models()

    def _open_reader(self):
        """打开阅读器 - 在浏览器中打开"""
        if not self._last_task_id:
            messagebox.showwarning("提示", "请先完成构建")
            return

        if not is_port_open(5000):
            messagebox.showerror("错误", "Flask 服务未启动，请重启应用")
            return

        # URL 编码中文文件名
        task_id = self._last_task_id
        book_name = getattr(self, '_book_name', task_id)
        data_file = quote(f"{task_id}_data.js")
        text_file = quote(f"{task_id}_book.md")
        name = quote(book_name)
        url = (f'http://127.0.0.1:5000/reader'
               f'?book={quote(task_id)}'
               f'&data={data_file}'
               f'&text={text_file}'
               f'&name={name}'
               f'&title={quote("点击节点查看详情")}')
        webbrowser.open(url)

    def run(self):
        """启动应用"""
        self.root.mainloop()


def main():
    app = DesktopApp()
    app.run()


if __name__ == '__main__':
    main()