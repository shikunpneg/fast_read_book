"""简单测试 Ollama 连接"""
import urllib.request, json, time

t0 = time.time()
data = json.dumps({"model": "qwen2.5:3b", "prompt": "你好", "stream": False}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:11434/api/generate",
    data=data,
    headers={"Content-Type": "application/json"},
)
resp = urllib.request.urlopen(req, timeout=180)
r = json.loads(resp.read())
elapsed = time.time() - t0
resp_text = r["response"][:50]
print(f"耗时: {elapsed:.1f}s")
print(f"响应: {resp_text}")