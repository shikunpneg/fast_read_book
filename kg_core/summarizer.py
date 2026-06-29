"""
LLM 摘要生成器 - 通过 Ollama 为实体生成通俗理解
"""
import json
import os
import time
import logging
import requests


class SummaryGenerator:
    """通过 Ollama LLM 为知识图谱实体批量生成摘要

    用法:
        gen = SummaryGenerator(data_dict, model="qwen2.5:3b")
        gen.generate(heading_only=True)
    """

    def __init__(self, entities: dict, model: str = "qwen2.5:3b",
                 ollama_url: str = "http://localhost:11434/api/generate",
                 max_retries: int = 3, retry_delay: int = 10,
                 max_content_len: int = 800, save_interval: int = 20,
                 max_consecutive_failures: int = 10,
                 progress_file: str = None,
                 log_file: str = None):
        self.entities = entities
        self.model = model
        self.ollama_url = ollama_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_content_len = max_content_len
        self.save_interval = save_interval
        self.max_consecutive_failures = max_consecutive_failures
        self.progress_file = progress_file
        self.log_file = log_file

        self._setup_logging()

    def _setup_logging(self):
        self.log = logging.getLogger('kg_core.summarizer')
        if not self.log.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)-5s] %(message)s', datefmt='%H:%M:%S'))
            self.log.addHandler(handler)
            self.log.setLevel(logging.INFO)
            if self.log_file:
                os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
                fh = logging.FileHandler(self.log_file, encoding='utf-8', mode='w')
                fh.setFormatter(handler.formatter)
                self.log.addHandler(fh)

    def build_prompt(self, name, definition, paragraph):
        """构建摘要生成的 prompt"""
        content = ""
        if definition:
            content += f"定义：{definition}\n"
        if paragraph:
            para = paragraph[:self.max_content_len]
            if len(paragraph) > self.max_content_len:
                para += "..."
            content += f"原文：{para}\n"
        if not content.strip():
            return None
        return f"""你是一个知识图谱领域的专家。请根据以下关于「{name}」的内容，用1-2句简洁的中文概括其核心要点。

{content}
请直接输出摘要，不要包含"摘要："等前缀，不要换行。"""

    def check_health(self):
        """检查 Ollama 服务是否正常"""
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def call_ollama(self, prompt):
        """调用 Ollama API"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 150}
        }
        try:
            resp = requests.post(self.ollama_url, json=payload, timeout=180)
            resp.raise_for_status()
            return resp.json().get("response", "").strip()
        except requests.exceptions.Timeout:
            self.log.error("  Ollama 请求超时 (180s)")
            return None
        except requests.exceptions.ConnectionError:
            self.log.error("  Ollama 连接失败")
            return None
        except Exception as e:
            self.log.error(f"  Ollama 调用异常: {e}")
            return None

    def _load_progress(self):
        if self.progress_file and os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"completed": 0, "processed": {}, "failed": []}

    def _save_progress(self, completed, processed, failed):
        if not self.progress_file:
            return
        progress = {
            "completed": completed,
            "processed": processed,
            "failed": failed,
            "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

    def generate(self, heading_only: bool = True, output_path: str = None) -> dict:
        """批量生成摘要

        Args:
            heading_only: 仅处理标题实体
            output_path: 输出 JSON 路径（每次保存进度时写入）

        Returns:
            更新后的 entities 字典
        """
        self.log.info("=" * 50)
        self.log.info(f"批量摘要生成启动 (模型: {self.model}, 模式: {'仅标题' if heading_only else '全部'})")

        progress = self._load_progress()
        processed = progress.get("processed", {})
        failed = progress.get("failed", [])
        completed = progress.get("completed", 0)

        # 过滤需处理的实体
        to_process = []
        for name, entity in self.entities.items():
            if name in processed:
                continue
            if heading_only and not entity.get("is_heading", False):
                continue
            if entity.get("definition") or entity.get("paragraph"):
                to_process.append(name)

        total = len(to_process)
        self.log.info(f"待处理: {total} 个实体 (已完成: {completed})")

        if total == 0:
            self.log.info("所有实体已处理完毕!")
            if self.progress_file and os.path.exists(self.progress_file):
                os.remove(self.progress_file)
            return self.entities

        start_time = time.time()
        batch_count = 0
        consecutive_failures = 0

        for i, name in enumerate(to_process):
            entity = self.entities[name]
            definition = entity.get("definition", "")
            paragraph = entity.get("paragraph", "")

            self.log.info(f"[{i+1}/{total}] {name}")

            prompt = self.build_prompt(name, definition, paragraph)
            if not prompt:
                processed[name] = ""
                completed += 1
                continue

            summary = None
            for retry in range(self.max_retries):
                if retry > 0:
                    self.log.info(f"  重试 {retry}/{self.max_retries}...")
                    time.sleep(self.retry_delay)

                if not self.check_health():
                    self.log.warning("  Ollama 服务无响应，等待 30 秒...")
                    time.sleep(30)
                    if not self.check_health():
                        self.log.error("  Ollama 服务仍无响应，跳过")
                        break

                summary = self.call_ollama(prompt)
                if summary:
                    consecutive_failures = 0
                    break
                self.log.warning(f"  调用失败 (尝试 {retry+1}/{self.max_retries})")

            if summary:
                for prefix in ["摘要：", "摘要:", "总结：", "总结:", "核心要点：", "核心要点:"]:
                    if summary.startswith(prefix):
                        summary = summary[len(prefix):].strip()
                self.entities[name]["summary"] = summary
                processed[name] = summary
                self.log.info(f"  OK {summary[:60]}...")
            else:
                self.log.error(f"  最终失败，跳过")
                failed.append(name)
                consecutive_failures += 1

                if consecutive_failures >= self.max_consecutive_failures:
                    self.log.error(f"!!! 连续 {consecutive_failures} 个实体失败，终止")
                    self._save_progress(completed, processed, failed)
                    if output_path:
                        self._save_entities(output_path)
                    return self.entities

            completed += 1
            batch_count += 1

            if batch_count >= self.save_interval:
                self._save_progress(completed, processed, failed)
                if output_path:
                    self._save_entities(output_path)
                elapsed = time.time() - start_time
                remaining = (total - i - 1) * (elapsed / (i + 1))
                self.log.info(f"--- 进度已保存 ({completed}) ETA: {remaining/60:.1f}min ---")
                batch_count = 0

        self._save_progress(completed, processed, failed)
        if output_path:
            self._save_entities(output_path)

        elapsed = time.time() - start_time
        self.log.info(f"摘要生成完成! 成功: {len(processed)-len(failed)}, 失败: {len(failed)}, 耗时: {elapsed/60:.1f}min")

        if self.progress_file and os.path.exists(self.progress_file) and len(failed) == 0:
            os.remove(self.progress_file)

        return self.entities

    def _save_entities(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.entities, f, ensure_ascii=False, indent=2)