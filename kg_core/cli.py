"""
kg-build 命令行入口
用法: kg-build book.txt --output kg_entity.json
"""
import argparse
import sys
from .builder import KnowledgeGraphBuilder


def main():
    parser = argparse.ArgumentParser(
        description="kg-build - 知识图谱构建工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  kg-build book.txt                          # 构建知识图谱
  kg-build book.txt --output data.json       # 指定输出路径
  kg-build book.txt --summary                # 生成 LLM 摘要
  kg-build book.txt --model qwen2.5:3b       # 指定模型
  kg-build book.txt --js kg_entity.js        # 输出 JS 文件
        """
    )
    parser.add_argument("book", help="书籍文本文件路径")
    parser.add_argument("--output", "-o", default="kg_entity.json", help="输出 JSON 路径 (默认: kg_entity.json)")
    parser.add_argument("--js", help="输出 JS 文件路径 (前端用)")
    parser.add_argument("--summary", action="store_true", help="生成 LLM 通俗理解摘要")
    parser.add_argument("--model", default="qwen2.5:3b", help="Ollama 模型名 (默认: qwen2.5:3b)")
    parser.add_argument("--existing", help="已有实体数据 JSON 路径 (增量更新)")
    parser.add_argument("--stats", action="store_true", help="仅显示统计信息")

    args = parser.parse_args()

    builder = KnowledgeGraphBuilder(args.book, model_name=args.model)

    if args.stats and args.existing:
        builder.load_book()
        builder.load_existing_data(args.existing)
        stats = builder.get_stats()
        print(f"实体: {stats['total_entities']}")
        print(f"关系: {stats['total_relations']}")
        print(f"有摘要: {stats['with_summary']}")
        print(f"有定义: {stats['with_definition']}")
        print(f"有段落: {stats['with_paragraph']}")
        return

    print(f"[kg-build] 开始构建知识图谱...")
    print(f"  书籍: {args.book}")
    print(f"  模型: {args.model}")
    print(f"  摘要: {'是' if args.summary else '否'}")

    data = builder.build(
        enable_summary=args.summary,
        existing_data_path=args.existing
    )

    builder.save_json(args.output)
    print(f"  JSON: {args.output}")

    if args.js:
        builder.save_js(args.js)
        print(f"  JS:   {args.js}")

    stats = builder.get_stats()
    print(f"\n构建完成!")
    print(f"  实体: {stats['total_entities']}")
    print(f"  关系: {stats['total_relations']}")
    print(f"  有摘要: {stats['with_summary']}")
    print(f"  有定义: {stats['with_definition']}")
    print(f"  有段落: {stats['with_paragraph']}")


if __name__ == "__main__":
    main()