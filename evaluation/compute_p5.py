"""計算 Precision@5

讀取填好的 judgments.csv，計算每組查詢的 P@5 與 10 組平均。
P@5 = 前 5 名中相關的篇數 / 5；回傳不足 5 筆時，缺少的名次視為不相關，分母仍為 5。

計算前會做三道檢查，任何一項不符就停止（避免默默算出錯的結果）：
  1. 索引快照：目前索引的 SHA-256 必須和 run_info.json 記錄的相同
  2. 查詢檔：queries.csv 的 SHA-256 必須和 run_info.json 記錄的相同
  3. 判讀表結構：每組查詢的名次必須剛好是 1..N，且每個名次的文件編號和產生時相同

執行：py evaluation/compute_p5.py（或 python evaluation/compute_p5.py）
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
    """先試 UTF-8，失敗再試 cp950（Excel 存成一般 CSV 時的編碼）。"""
    for enc in ("utf-8-sig", "cp950"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    raise ValueError(f"無法讀取 {path}，請用「CSV UTF-8」格式存檔")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stop(title, problems):
    print(f"{title}，共 {len(problems)} 個問題（列出前 10 個）：")
    for p in problems[:10]:
        print("  -", p)
    sys.exit(1)


def check_snapshot():
    """檢查 1、2：索引與查詢檔必須和產生判讀表時相同。回傳 run_info。"""
    if not RUN_INFO_PATH.exists():
        stop("找不到 run_info.json", ["請先執行 run_evaluation.py 產生判讀表"])
    info = json.loads(RUN_INFO_PATH.read_text(encoding="utf-8"))
    problems = []
    if sha256(config.INDEX_PATH) != info.get("index_sha256"):
        problems.append("目前的索引檔和產生 judgments.csv 時不同")
    if sha256(QUERIES_PATH) != info.get("queries_sha256"):
        problems.append("queries.csv 在產生 judgments.csv 之後被修改過")
    if "expected_rows" not in info:
        problems.append("run_info.json 是舊版格式，缺少 expected_rows")
    if problems:
        problems.append("判讀結果和目前的索引／查詢對不上，請重新執行 run_evaluation.py 並重新判讀")
        stop("評估快照不一致，無法計算", problems)
    return info


def check_structure(queries, judgments, expected_rows):
    """檢查 3：每組查詢的 (名次, 文件編號) 必須和產生時完全相同。"""
    problems = []
    qids = {q["query_id"] for q in queries}
    for row in judgments:
        if row.get("query_id") not in qids:
            problems.append(f"出現不在 queries.csv 的查詢編號「{row.get('query_id')}」")

    for qid in sorted(qids):
        expected = [str(d) for d in expected_rows.get(qid, [])]
        actual = {}
        for row in judgments:
            if row.get("query_id") != qid:
                continue
            rank_text = str(row.get("rank", "")).strip()
            if not rank_text.isdigit():
                problems.append(f"{qid}：名次「{rank_text}」不是正整數")
                continue
            rank = int(rank_text)
            if rank in actual:
                problems.append(f"{qid} 第 {rank} 名：重複出現")
            actual[rank] = str(row.get("doc_id", "")).strip()

        expected_ranks = set(range(1, len(expected) + 1))
        if set(actual) != expected_ranks:
            missing = sorted(expected_ranks - set(actual))
            extra = sorted(set(actual) - expected_ranks)
            detail = []
            if missing:
                detail.append(f"缺少第 {missing} 名")
            if extra:
                detail.append(f"多出第 {extra} 名")
            problems.append(f"{qid}：名次應為 1–{len(expected)}，" + "、".join(detail))
        for rank, doc_id in actual.items():
            if 1 <= rank <= len(expected) and doc_id != expected[rank - 1]:
                problems.append(f"{qid} 第 {rank} 名：文件編號應為 {expected[rank - 1]}，"
                                f"判讀表是 {doc_id}")
    return problems


def main():
    info = check_snapshot()
    queries = read_csv(QUERIES_PATH)
    judgments = read_csv(JUDGMENTS_PATH)

    problems = check_structure(queries, judgments, info["expected_rows"])
    if problems:
        stop("judgments.csv 的結構和產生時不符（名次或文件編號被改動）", problems)

    labels, unfilled = {}, []
    for row in judgments:
        value = (row.get("relevant") or "").strip()
        where = f"{row['query_id']} 第 {row['rank']} 名"
        if value not in ("0", "1"):
            unfilled.append(f"{where}：relevant 必須是 1 或 0（目前是「{value}」）")
            continue
        if not (row.get("reason") or "").strip():
            unfilled.append(f"{where}：缺少判斷理由 reason")
        labels[(row["query_id"], int(row["rank"]))] = int(value)
    if unfilled:
        stop("judgments.csv 還沒填完整", unfilled)

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
