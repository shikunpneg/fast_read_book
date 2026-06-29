"""
批量生成实体摘要 - 通过 Ollama (qwen2.5:3b) 为每个实体生成中文摘要
支持断点续传，每 50 个实体自动保存进度
"""
import json
import os
import sys
import time
import logging
import requests
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:3b"
INPUT_FILE = "e:/nlp/ltp/kg_entity_v7.json"
OUTPUT_FILE = "e:/nlp/ltp/kg_entity_v7.json"
PROGRESS_FILE = "e:/nlp/ltp/summary_progress.json"
LOG_FILE = "e:/nlp/ltp/logs/generate_summaries.log"
MAX_RETRIES = 3
RETRY_DELAY = 10  # seconds, 每次重试前的等待时间
SAVE_INTERVAL = 20  # save every N entities (heading-only mode, smaller batch)
MAX_CONTENT_LEN = 800  # max chars sent to Ollama (to avoid token overflow)
HEADING_ONLY = True  # 只生成标题实体的摘要

# ── 日志 ──────────────────────────────────────────────
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)-5s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8', mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger('generate_summaries')


def build_prompt(name, definition, paragraph):
    """构建摘要生成的 prompt"""
    content = ""
    if definition:
        content += f"定义：{definition}\n"
    if paragraph:
        # 截断过长内容
        para = paragraph[:MAX_CONTENT_LEN]
        if len(paragraph) > MAX_CONTENT_LEN:
            para += "..."
        content += f"原文：{para}\n"

    if not content.strip():
        return None

    prompt = f"""你是一个知识图谱领域的专家。请根据以下关于「{name}」的内容，用1-2句简洁的中文概括其核心要点。

{content}
请直接输出摘要，不要包含"摘要："等前缀，不要换行。"""
    return prompt


def check_ollama_health():
    """检查 Ollama 服务是否正常响应"""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def call_ollama(prompt):
    """调用 Ollama API 生成摘要，增加超时和重试"""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 150,  # 限制生成长度
        }
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=180)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()
    except requests.exceptions.Timeout:
        log.error("  Ollama 请求超时 (180s)")
        return None
    except requests.exceptions.ConnectionError:
        log.error("  Ollama 连接失败，请确认 Ollama 服务已启动")
        return None
    except Exception as e:
        log.error(f"  Ollama 调用异常: {e}")
        return None


def load_progress():
    """加载进度文件，支持断点续传"""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                progress = json.load(f)
            log.info(f"找到进度文件: 已完成 {progress.get('completed', 0)} 个实体")
            return progress
        except Exception as e:
            log.warning(f"进度文件损坏，从头开始: {e}")
    return {"completed": 0, "processed": {}, "failed": []}


def save_progress(completed, processed, failed):
    """保存进度"""
    progress = {
        "completed": completed,
        "processed": processed,
        "failed": failed,
        "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def main():
    log.info("=" * 50)
    log.info("批量摘要生成启动")
    log.info(f"模型: {MODEL}")
    log.info(f"模式: {'仅标题实体' if HEADING_ONLY else '全部实体'}")
    log.info(f"输入: {INPUT_FILE}")
    log.info("=" * 50)

    # 加载实体数据
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        entities = json.load(f)
    log.info(f"加载实体数据: {len(entities)} 个实体")

    # 加载进度
    progress = load_progress()
    processed = progress.get("processed", {})
    failed = progress.get("failed", [])
    completed = progress.get("completed", 0)

    # 过滤需要处理的实体
    to_process = []
    for name, entity in entities.items():
        if name in processed:
            continue
        # 如果 HEADING_ONLY 模式，只处理标题实体
        if HEADING_ONLY and not entity.get("is_heading", False):
            continue
        definition = entity.get("definition", "")
        paragraph = entity.get("paragraph", "")
        if definition or paragraph:
            to_process.append(name)

    total = len(to_process)
    log.info(f"待处理: {total} 个实体 (已完成: {completed})")

    if total == 0:
        log.info("所有实体已处理完毕!")
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
        return

    # 批量处理
    start_time = time.time()
    batch_count = 0
    consecutive_failures = 0
    MAX_CONSECUTIVE_FAILURES = 10  # 连续失败超过此数则暂停

    for i, name in enumerate(to_process):
        entity = entities[name]
        definition = entity.get("definition", "")
        paragraph = entity.get("paragraph", "")

        log.info(f"[{i+1}/{total}] {name}")

        prompt = build_prompt(name, definition, paragraph)
        if not prompt:
            log.info(f"  跳过: 无有效内容")
            processed[name] = ""
            completed += 1
            continue

        # 重试机制（含 Ollama 健康检查）
        summary = None
        for retry in range(MAX_RETRIES):
            if retry > 0:
                log.info(f"  重试 {retry}/{MAX_RETRIES}...")
                time.sleep(RETRY_DELAY)

            # 重试前检查 Ollama 是否健康
            if not check_ollama_health():
                log.warning("  Ollama 服务无响应，等待 30 秒后重试...")
                time.sleep(30)
                if not check_ollama_health():
                    log.error("  Ollama 服务仍然无响应，跳过此实体")
                    break

            summary = call_ollama(prompt)
            if summary:
                consecutive_failures = 0  # 重置连续失败计数
                break
            log.warning(f"  调用失败 (尝试 {retry+1}/{MAX_RETRIES})")

        if summary:
            # 清理输出
            summary = summary.strip()
            for prefix in ["摘要：", "摘要:", "总结：", "总结:", "核心要点：", "核心要点:"]:
                if summary.startswith(prefix):
                    summary = summary[len(prefix):].strip()
            entities[name]["summary"] = summary
            processed[name] = summary
            log.info(f"  ✓ {summary[:60]}...")
        else:
            log.error(f"  ✗ 最终失败 (3 次重试均失败)，跳过此实体")
            failed.append(name)
            consecutive_failures += 1

            # 连续失败过多，提醒用户
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                log.error("=" * 50)
                log.error(f"!!! 连续 {consecutive_failures} 个实体失败，Ollama 可能已卡住")
                log.error("!!! 建议: 在终端执行 ollama stop qwen2.5:3b 后重新运行脚本")
                log.error("!!! 当前进度已保存，重启后会自动续传")
                log.error("=" * 50)
                save_progress(completed, processed, failed)
                with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(entities, f, ensure_ascii=False, indent=2)
                return  # 终止脚本，等用户手动处理

        completed += 1
        batch_count += 1

        # 进度保存
        if batch_count >= SAVE_INTERVAL:
            save_progress(completed, processed, failed)
            log.info(f"--- 进度已保存 ({completed}/{total + completed - len(to_process)}) ---")

            # 保存实体数据
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(entities, f, ensure_ascii=False, indent=2)
            log.info("--- 实体数据已保存 ---")

            # ETA
            elapsed = time.time() - start_time
            remaining = (total - i - 1) * (elapsed / (i + 1))
            log.info(f"--- ETA: {remaining/60:.1f} 分钟 ---")

            batch_count = 0

    # 最终保存
    save_progress(completed, processed, failed)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(entities, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start_time
    log.info("=" * 50)
    log.info(f"摘要生成完成!")
    log.info(f"成功: {len(processed) - len(failed)} 个")
    log.info(f"失败: {len(failed)} 个")
    log.info(f"总耗时: {elapsed/60:.1f} 分钟")
    log.info(f"输出: {OUTPUT_FILE}")

    # 清理进度文件
    if os.path.exists(PROGRESS_FILE) and len(failed) == 0:
        os.remove(PROGRESS_FILE)
        log.info("进度文件已清理")

    if failed:
        log.warning(f"失败实体列表: {failed}")


if __name__ == "__main__":
    main()