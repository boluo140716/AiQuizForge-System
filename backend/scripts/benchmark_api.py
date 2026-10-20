"""API 基准测试：测量常用读接口的延迟与吞吐。

用法（宿主机，服务已启动）：
    python backend/scripts/benchmark_api.py --requests 100 --concurrency 8

结果同时写入 reports/perf/ 下的 CSV 与 Markdown。
"""
import argparse
import csv
import json
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import requests

ENDPOINTS = [
    ("笔记列表", "/api/v1/notes/?page=1&page_size=10"),
    ("笔记本列表", "/api/v1/notebooks/"),
    ("测验列表", "/api/v1/quizzes/"),
    ("错题列表", "/api/v1/wrong-questions/list/"),
    ("掌握度", "/api/v1/learning/mastery/"),
    ("学习曲线", "/api/v1/learning/curve/"),
    ("今日复习", "/api/v1/learning/review/due/"),
]

_local = threading.local()


def _session():
    if not hasattr(_local, "session"):
        _local.session = requests.Session()
    return _local.session


def login(base_url, username, password):
    resp = requests.post(
        f"{base_url}/api/v1/auth/login/",
        json={"username": username, "password": password},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access"]


def percentile(values, p):
    if not values:
        return 0.0
    values = sorted(values)
    k = (len(values) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def one_request(url, headers):
    start = time.perf_counter()
    try:
        resp = _session().get(url, headers=headers, timeout=30)
        status = resp.status_code
    except requests.RequestException:
        status = 0
    return status, (time.perf_counter() - start) * 1000


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--username", default="demo")
    parser.add_argument("--password", default="demo12345")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--out-dir", default="reports/perf")
    args = parser.parse_args()

    token = login(args.base_url, args.username, args.password)
    headers = {"Authorization": f"Bearer {token}"}

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = out_dir / f"benchmark_{stamp}.csv"
    md_path = out_dir / f"benchmark_{stamp}.md"

    rows, summary = [], []

    for name, path in ENDPOINTS:
        url = f"{args.base_url}{path}"
        for _ in range(3):  # 预热，排除首次连接与缓存冷启动
            one_request(url, headers)

        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            results = list(
                pool.map(lambda _: one_request(url, headers), range(args.requests))
            )
        elapsed = time.perf_counter() - started

        latencies = [ms for status, ms in results if status == 200]
        errors = sum(1 for status, _ in results if status != 200)
        summary.append({
            "endpoint": name,
            "path": path,
            "requests": args.requests,
            "errors": errors,
            "mean_ms": round(statistics.mean(latencies), 2) if latencies else 0.0,
            "p50_ms": round(percentile(latencies, 50), 2),
            "p95_ms": round(percentile(latencies, 95), 2),
            "p99_ms": round(percentile(latencies, 99), 2),
            "rps": round(args.requests / elapsed, 2) if elapsed else 0.0,
        })
        rows.extend((name, status, round(ms, 2)) for status, ms in results)

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["endpoint", "status", "latency_ms"])
        writer.writerows(rows)

    lines = [
        "# API 基准测试",
        "",
        f"- 时间：{stamp}",
        f"- 地址：{args.base_url}",
        f"- 每接口请求数：{args.requests}，并发：{args.concurrency}",
        "",
        "| 接口 | 请求数 | 错误 | 平均(ms) | P50(ms) | P95(ms) | P99(ms) | RPS |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for s in summary:
        lines.append(
            f"| {s['endpoint']} | {s['requests']} | {s['errors']} | {s['mean_ms']} | "
            f"{s['p50_ms']} | {s['p95_ms']} | {s['p99_ms']} | {s['rps']} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nCSV: {csv_path}\nMD:  {md_path}")


if __name__ == "__main__":
    main()
