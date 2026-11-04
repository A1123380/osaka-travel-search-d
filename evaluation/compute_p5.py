"""計算 Precision@5

讀取填好的 judgments.csv，計算每組查詢的 P@5 與 10 組平均。
P@5 = 前 5 名中相關的篇數 / 5；回傳不足 5 筆時，缺少的名次視為不相關，分母仍為 5。

執行：py evaluation/compute_p5.py
輸出：螢幕表格 + p5_results.csv
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR.parent))

import config  # noqa: E402

QUERIES_PATH = EVAL_DIR / "queries.csv"
JUDGMENTS_PATH = EVAL_DIR / "judgments.csv"
RUN_INFO_PATH = EVAL_DIR / "run_info.json"
RESULTS_PATH = EVAL_DIR / "p5_results.csv"
CUTOFF = 5


def precision_at_k(labels_by_rank, k=CUTOFF):
    """labels_by_rank：{名次: 1 或 0}。缺少的名次視為不相關，分母固定為 k。"""
    return sum(labels_by_rank.get(r, 0) for r in range(1, k + 1)) / k


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def check_snapshot():
    """確認目前的索引和產生判讀表時是同一份，否則結果不可重現。回傳 run_info。"""
    if not RUN_INFO_PATH.exists():
        print("警告：找不到 run_info.json，無法確認索引版本。")
        return {}
    info = json.loads(RUN_INFO_PATH.read_text(encoding="utf-8"))
    h = hashlib.sha256(Path(config.INDEX_PATH).read_bytes()).hexdigest()
    if h != info.get("index_sha256"):
        print("警告：目前的索引檔和產生 judgments.csv 時不同！")
        print("      判讀結果可能對不上，請確認是否需要重跑 run_evaluation.py。\n")
    return info


def main():
    info = check_snapshot()
    queries = read_csv(QUERIES_PATH)
    judgments = read_csv(JUDGMENTS_PATH)

    problems = []
    # 檢查判讀表的列數和當初產生時一致（避免不小心刪掉一列，被當成不相關）
    for qid, expected in info.get("returned_per_query", {}).items():
        actual = sum(1 for row in judgments if row["query_id"] == qid)
        if actual != expected:
            problems.append(f"{qid}：判讀表有 {actual} 列，但當初產生了 {expected} 列")
    seen = set()
    for row in judgments:
        key = (row["query_id"], row["rank"])
        if key in seen:
            problems.append(f"{row['query_id']} 第 {row['rank']} 名：重複出現")
        seen.add(key)

    labels = {}  # (query_id, rank) -> 0/1
    for row in judgments:
        value = (row.get("relevant") or "").strip()
        where = f"{row['query_id']} 第 {row['rank']} 名"
        if value not in ("0", "1"):
            problems.append(f"{where}：relevant 必須是 1 或 0（目前是「{value}」）")
            continue
        if not (row.get("reason") or "").strip():
            problems.append(f"{where}：缺少判斷理由 reason")
        labels[(row["query_id"], int(row["rank"]))] = int(value)

    if problems:
        print(f"judgments.csv 還沒填完整，共 {len(problems)} 個問題（列出前 10 個）：")
        for p in problems[:10]:
            print("  -", p)
        sys.exit(1)

    out = []
    for q in queries:
        qid = q["query_id"]
        by_rank = {r: v for (q_id, r), v in labels.items() if q_id == qid}
        returned = sum(1 for r in by_rank if r <= CUTOFF)
        rel = sum(v for r, v in by_rank.items() if r <= CUTOFF)
        out.append({"query_id": qid, "query": q["query"], "returned_top5": returned,
                    "relevant_top5": rel, "precision_at_5": precision_at_k(by_rank)})

    mean = sum(r["precision_at_5"] for r in out) / len(out)

    print(f"{'ID':<5}{'查詢':<36}{'回傳':>4}{'相關':>4}{'P@5':>7}")
    for r in out:
        print(f"{r['query_id']:<5}{r['query']:<36}{r['returned_top5']:>5}"
              f"{r['relevant_top5']:>5}{r['precision_at_5']:>8.2f}")
    print(f"\n平均 Precision@5（{len(out)} 組）= {mean:.4f}")

    with RESULTS_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        writer.writeheader()
        for r in out:
            writer.writerow({**r, "precision_at_5": f"{r['precision_at_5']:.2f}"})
        writer.writerow({"query_id": "MEAN", "query": "", "returned_top5": "",
                         "relevant_top5": "", "precision_at_5": f"{mean:.4f}"})
    print(f"已儲存：{RESULTS_PATH.name}")


if __name__ == "__main__":
    main()
