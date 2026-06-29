"""
kg-book-tool - 知识图谱交互书构建工具
将 PDF/EPUB 电子书自动转换为交互式知识图谱 HTML
"""
from setuptools import setup, find_packages

with open("kg_core/__init__.py", encoding="utf-8") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"').strip("'")
            break

setup(
    name="kg-book-tool",
    version=version,
    description="将电子书自动转换为交互式知识图谱 HTML",
    author="KG Book Team",
    packages=find_packages(include=["kg_core", "kg_core.*"]),
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28",
        # 文件解析
        "PyMuPDF>=1.23.0",        # PDF
        "ebooklib>=0.18",         # EPUB
        "lxml>=4.9.0",
        "python-docx>=1.0.0",     # Word
        "python-pptx>=0.6.21",    # PowerPoint
        "openpyxl>=3.1.0",        # Excel
        "beautifulsoup4>=4.12.0", # HTML
        "chardet>=5.0.0",
        # OCR（图像型 PDF / 图片）
        "easyocr>=1.7.0",
        # 编码自动检测
        "charset_normalizer>=3.0",
    ],
    extras_require={
        "server": [
            "flask>=2.3",
            "werkzeug>=2.3",
            "waitress>=2.1",
        ],
        "desktop": [
            "pywebview>=4.0",
            "waitress>=2.1",
            "flask>=2.3",
        ],
        "full": [
            "flask>=2.3",
            "werkzeug>=2.3",
            "pywebview>=4.0",
            "waitress>=2.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "kg-build=kg_core.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
    ],
)