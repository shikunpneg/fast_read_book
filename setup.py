"""
kg-book-tool - 知识图谱交互书构建工具
将 PDF/EPUB 电子书自动转换为交互式知识图谱 HTML
"""
from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", encoding="utf-8") as f:
    requirements = [
        line.strip()
        for line in f
        if line.strip() and not line.startswith("#")
    ]

with open("kg_core/__init__.py", encoding="utf-8") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"').strip("'")
            break

setup(
    name="kg-book-tool",
    version=version,
    description="将电子书自动转换为交互式知识图谱 HTML",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="shikunpneg",
    author_email="145889015+shikunpneg@users.noreply.github.com",
    url="https://github.com/shikunpneg/fast_read_book",
    project_urls={
        "Bug Tracker": "https://github.com/shikunpneg/fast_read_book/issues",
        "Documentation": "https://shikunpneg.github.io/fast_read_book/",
        "Source": "https://github.com/shikunpneg/fast_read_book",
        "Changelog": "https://github.com/shikunpneg/fast_read_book/blob/main/CHANGELOG.md",
    },
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
        "docs": [
            "mkdocs>=1.5",
            "mkdocs-material>=9.0",
            "mkdocstrings[python]>=0.24",
            "pymdown-extensions>=10.0",
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
            "kg-desktop=kg_app.desktop:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "Topic :: Text Processing :: Markup",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Natural Language :: Chinese (Simplified)",
        "Natural Language :: English",
    ],
    keywords="ebook pdf epub knowledge-graph ocr nlp",
)