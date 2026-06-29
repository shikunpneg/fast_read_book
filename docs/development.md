# 开发指南

## 项目结构

```
fast_read_book/
├── kg_core/                  # 核心库（pip 入口）
│   ├── __init__.py
│   ├── builder.py            # KnowledgeGraphBuilder
│   ├── converters.py         # 多格式转换 + OCR
│   ├── text_cleaner.py       # 编码检测
│   ├── summarizer.py         # LLM 摘要
│   └── cli.py                # 命令行
├── kg_app/                   # Web + 桌面
│   ├── desktop.py            # Tkinter
│   ├── main.py               # Flask
│   ├── templates/
│   └── static/
├── scripts/                  # 辅助脚本
├── docs/                     # mkdocs 文档
├── tests/                    # 单元测试
├── .github/workflows/        # CI/CD
├── setup.py
├── mkdocs.yml
└── CHANGELOG.md
```

## 本地开发

```bash
# 克隆
git clone https://github.com/shikunpneg/fast_read_book.git
cd fast_read_book

# 开发模式安装
pip install -e ".[full]"

# 跑测试
pytest tests/ -v

# 跑示例
python examples/demo.py
```

## 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/)：

```text
feat: 新增功能
fix: 修复 bug
docs: 文档变更
style: 格式（不影响代码运行）
refactor: 重构
test: 测试相关
chore: 杂项（构建、CI）
```

## 发版流程

1. 更新 `CHANGELOG.md`
2. 更新 `setup.py` 中的 `version`
3. 提交：`git commit -m "release: v1.0.1"`
4. 打 tag：`git tag v1.0.1`
5. 推送：`git push --tags`
6. GitHub Actions 自动构建 + 发布 PyPI + 创建 Release

## 跑 mkdocs 本地预览

```bash
pip install mkdocs mkdocs-material
mkdocs serve
```

打开 http://localhost:8000
