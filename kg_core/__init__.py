"""
kg_core - 知识图谱交互书核心引擎
提供电子书解析、实体提取、关系构建、摘要生成等功能
"""
from .builder import KnowledgeGraphBuilder
from .summarizer import SummaryGenerator
from .text_cleaner import clean_text, split_chapters

__version__ = "1.0.1"
__all__ = ["KnowledgeGraphBuilder", "SummaryGenerator", "clean_text", "split_chapters"]