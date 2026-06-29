"""
PyInstaller 打包脚本 - 将 kg_app 打包为独立 Windows .exe
用法:
    python build_exe.py          # 打包为单文件 .exe
    python build_exe.py --dir    # 打包为目录 (启动更快)
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR / 'kg_app'
DIST_DIR = BASE_DIR / 'dist'

# PyInstaller 参数
APP_NAME = '知识图谱交互书'
ENTRY_SCRIPT = str(APP_DIR / 'gui.py')

# 需要包含的数据文件
DATAS = [
    (str(APP_DIR / 'templates'), 'templates'),
    (str(APP_DIR / 'static'), 'static'),
]

# 隐藏导入
HIDDEN_IMPORTS = [
    'kg_core',
    'kg_core.builder',
    'kg_core.summarizer',
    'kg_core.text_cleaner',
    'flask',
    'werkzeug',
    'jinja2',
    'markupsafe',
    'click',
    'itsdangerous',
    'blinker',
    'webview',
    'webview.platforms.winforms',
    'waitress',
    'clr_loader',
    'pythonnet',
]


def build_onefile():
    """打包为单个 .exe 文件"""
    print("=" * 60)
    print(f"打包 {APP_NAME} (单文件模式)")
    print("=" * 60)

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--name', APP_NAME,
        '--console',
        '--clean',
        '--noconfirm',
    ]

    # 添加数据文件
    for src, dst in DATAS:
        cmd.extend(['--add-data', f'{src}{os.pathsep}{dst}'])

    # 添加隐藏导入
    for imp in HIDDEN_IMPORTS:
        cmd.extend(['--hidden-import', imp])

    cmd.append(ENTRY_SCRIPT)

    print(f"  命令: {' '.join(cmd[:6])} ...")
    subprocess.run(cmd, cwd=str(BASE_DIR), check=True)

    exe_path = DIST_DIR / f'{APP_NAME}.exe'
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n打包成功!")
        print(f"  输出: {exe_path}")
        print(f"  大小: {size_mb:.1f} MB")
    else:
        print("\n打包失败: .exe 文件未生成")


def build_onedir():
    """打包为目录 (包含多个文件，启动更快)"""
    print("=" * 60)
    print(f"打包 {APP_NAME} (目录模式)")
    print("=" * 60)

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onedir',
        '--name', APP_NAME,
        '--console',
        '--clean',
        '--noconfirm',
    ]

    for src, dst in DATAS:
        cmd.extend(['--add-data', f'{src}{os.pathsep}{dst}'])

    for imp in HIDDEN_IMPORTS:
        cmd.extend(['--hidden-import', imp])

    cmd.append(ENTRY_SCRIPT)

    print(f"  命令: {' '.join(cmd[:6])} ...")
    subprocess.run(cmd, cwd=str(BASE_DIR), check=True)

    exe_dir = DIST_DIR / APP_NAME
    exe_path = exe_dir / f'{APP_NAME}.exe'
    if exe_path.exists():
        print(f"\n打包成功!")
        print(f"  输出目录: {exe_dir}")
        print(f"  可执行文件: {exe_path}")
    else:
        print("\n打包失败: .exe 文件未生成")


def clean():
    """清理构建文件"""
    for d in ['build', 'dist', '__pycache__']:
        path = BASE_DIR / d
        if path.exists():
            shutil.rmtree(path)
            print(f"  已清理: {d}")
    for spec in BASE_DIR.glob('*.spec'):
        spec.unlink()
        print(f"  已清理: {spec.name}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='打包知识图谱交互书为 .exe')
    parser.add_argument('--dir', action='store_true', help='打包为目录模式 (启动更快)')
    parser.add_argument('--clean', action='store_true', help='仅清理构建文件')
    args = parser.parse_args()

    if args.clean:
        clean()
    elif args.dir:
        build_onedir()
    else:
        build_onefile()