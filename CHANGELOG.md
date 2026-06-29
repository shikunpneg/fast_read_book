# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- 多语言界面（英文）
- 在线部署版（Docker）
- 性能基准测试

## [1.0.0] - 2026-06-29

### Added
- 多格式电子书支持：PDF、EPUB、DOCX、PPTX、XLSX、HTML、Markdown、TXT、图片
- EasyOCR 自动回退处理图像型 PDF
- 文本编码自动检测：UTF-8 / GBK / GB2312 / GB18030 / Big5 / Latin-1
- 参考文献小节自动识别为实体（`[n] Author Title` 格式）
- 章节标题、定义、段落自动提取
- `KnowledgeGraphBuilder` 统一 API
- `kg-build` 命令行工具
- `kg-desktop` 桌面应用入口
- Tkinter 桌面 GUI（多线程构建不卡顿）
- Flask Web 后端 + 三视图阅读器（实体列表、思维导图、原文对照）
- pip 一键安装（`pip install kg-book-tool`）
- 完整 GitHub Actions CI/CD（自动测试 + 自动发布 PyPI + 自动 GitHub Release）
- mkdocs-material 文档站点（自动部署到 GitHub Pages）
- MIT License
- 完整的中文文档（DEPLOY.md + 项目升级.md 等）

### Changed
- 项目从 `kg.py` 单文件重构为 `kg_core` 包
- 旧版 `archive/` 目录（v4-v6 代码）归档
- 实体识别从纯启发式升级为「后端 `is_reference` 字段优先 + 启发式兜底」

### Fixed
- 图像型 PDF 提取失败问题（OCR 回退）
- 参考文献未作为实体的问题
- 参考文献小节换行错乱问题（自动合并 `[n]` 编号条目）
- 多种编码乱码问题
- 编码自动检测准确度问题

[Unreleased]: https://github.com/shikunpneg/fast_read_book/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/shikunpneg/fast_read_book/releases/tag/v1.0.0
