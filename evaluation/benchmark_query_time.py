"""查詢耗時量測（加分項：query-time measurement，最多 2 分）

計時範圍：只計算 search() 本身，也就是查詢拆字、查倒排索引、
計算餘弦相似度與排序。不包含載入索引（只在開始前做一次）、產生摘要、網頁渲染。

做法：10 組評估查詢各先暖身 1 次，再各跑 REPEAT 次，用 time.perf_counter() 計時。
執行：py evaluation/benchmark_query_time.py
輸出：螢幕表格 + query_time_summary.csv
"""
import csv
import platform
import statistics
import sys
import time
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR.parent))

import config  # noqa: E402

REPEAT = 100
OUTPUT_PATH = EVAL_DIR / "query_time_summary.csv"


def main():
    index = config.load_index()
    with (EVAL_DIR / "queries.csv").open("r", encoding="utf-8-sig", newline="") as f:
        queries = list(csv.DictReader(f))

    rows, all_times = [], []
    for q in queries:
        config.search(q["query"], index, top_k=10)  # 暖身
        times = []
        for _ in range(REPEAT):
            start = time.perf_counter()
            config.search(q["query"], index, top_k=10)
            times.append((time.perf_counter() - start) * 1000)
        all_times.extend(times)
        rows.append({"query_id": q["query_id"], "query": q["query"],
                     "mean_ms": statistics.mean(times),
                     "median_ms": statistics.median(times),
                     "max_ms": max(times)})

    print(f"環境：Python {platform.python_version()}，{platform.platform()}")
    print(f"文件數 {len(index['documents'])}，每組查詢重複 {REPEAT} 次\n")
    print(f"{'ID':<5}{'查詢':<36}{'平均ms':>9}{'中位ms':>9}{'最大ms':>9}")
    for r in rows:
        print(f"{r['query_id']:<5}{r['query']:<36}{r['mean_ms']:>9.3f}"
              f"{r['median_ms']:>9.3f}{r['max_ms']:>9.3f}")
    print(f"\n全部 {len(all_times)} 次：平均 {statistics.mean(all_times):.3f} ms，"
          f"中位 {statistics.median(all_times):.3f} ms，最大 {max(all_times):.3f} ms")

    with OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})
    print(f"已儲存：{OUTPUT_PATH.name}")


if __name__ == "__main__":
    main()
