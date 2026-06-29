"""Debug V4 extraction"""
import re, json
from collections import defaultdict, Counter
import jieba
import jieba.analyse

STOP_WORDS = set("""
的 了 在 是 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着
没有 看 好 自己 这 他 她 它 们 那 与 及 等 之 而 或 被 对 把 被 让
从 向 以 为 由 于 但 如 因为 所以 如果 虽然 然而 而且 不过 只是
可以 可能 应该 需要 能够 必须 基于 通过 利用 使用 采用 进行 包括
具有 分为 称为 作为 用于 其中 以及 所谓 例如 比如 此外 同时 之后
之前 当中 之间 方面 相关 主要 重要 基本 一般 通常 往往 越来越
大量 多个 不同 各种 这些 那些 每个 有的 一些 这个 那个 什么 怎么
如何 是否 不是 就是 而是 还是 或者 没有 可以 这个 问题 方法 技术
系统 数据 模型 信息 任务 过程 方式 结果 目标 特征 元素 类型 形式
结构 内容 关系 概念 能力 领域 研究 分析 实现 提出 定义 描述 表示
一个 两个 三个 多个 不同 同时 例如 可见 引入 存在 需要 给出 利用
基于 通过 使用 用于 包括 具有 分为 称为 作为 开发 支持 提供 计算
发现 得到 可能 处理 搜索 排序 检索 提取 构建 匹配 识别 预测 管理
模块 函数 配置 参数 相应 具体 自然 需要 目前 因此 此外 通常 左右
以下 如下 所示 给出 利用 而言 数据 信息 关系 应用 问题 理解 完成 进行
基于 定义 开发 提供 支持 处理 识别 搜索 计算 融合 排序 检测
描述 变化 操作 考虑 训练 标注 评估 选择 吸引 调整 指定 行为 研究
提高 关注 降低 类 型 特征 元素 集合 分类 包括 具有
""".split())

with open(r'e:\nlp\ltp\kg_book_full.txt', encoding='utf-8') as f:
    lines = f.readlines()

ch1 = ''.join(lines[405:1733])

# Don't strip English, just strip punctuation
import string
ch1_clean = ch1
# replace newlines with space
ch1_clean = ch1_clean.replace('\n', ' ')

kw = jieba.analyse.textrank(ch1_clean, topK=50, withWeight=True,
    allowPOS=('ns','n','vn','v','nr','nt','nz','l','eng'))

print("TextRank results:")
count = 0
for w, wt in kw:
    if w in STOP_WORDS or len(w) < 2 or len(w) > 10:
        continue
    if all(ord(c) < 128 for c in w):
        continue
    count += 1
    print(f"  {count}. {w}: {wt:.4f}")
    if count >= 20:
        break

# Also test TF-IDF
kw2 = jieba.analyse.extract_tags(ch1_clean, topK=50, withWeight=True,
    allowPOS=('ns','n','vn','v','nr','nt','nz','l','eng'))
print("\nTF-IDF results:")
count = 0
for w, wt in kw2:
    if w in STOP_WORDS or len(w) < 2 or len(w) > 10:
        continue
    if all(ord(c) < 128 for c in w):
        continue
    count += 1
    print(f"  {count}. {w}: {wt:.4f}")
    if count >= 20:
        break