"""
kg_app 桌面启动器
直接启动原生 Tkinter 桌面应用，无需浏览器/网页
"""
import os
import sys
from pathlib import Path

# 确保导入路径
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


def main():
    """启动原生桌面应用"""
    from kg_app.desktop import DesktopApp
    app = DesktopApp()
    app.run()


if __name__ == '__main__':
    main()