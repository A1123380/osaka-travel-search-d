"""產生相關性判讀表 judgments.csv

用凍結的索引跑 queries.csv 的 10 組查詢，把每組前 5 筆結果寫進 judgments.csv。
relevant（1/0）和 reason 兩欄留空，請組員讀完「內文」後填寫。
同時把這次使用的索引檔 SHA-256 記錄在 run_info.json，方便日後確認結果可重現。

執行：py evaluation/run_evaluation.py
若 judgments.csv 已經有人填過 relevant，程式會拒絕覆蓋；確定要重跑請加 --overwrite。
"""
import csv
import datetime
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
CUTOFF = 5
FIELDS = ["query_id", "query", "rank", "doc_id", "url", "title", "score",
          "relevant", "reason", "judge", "second_review"]


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def relative_path(path):
    """記錄相對於專案資料夾的路徑，換電腦也看得懂（不含使用者名稱）。"""
    project_root = config.FOLDER.parent
    try:
        return Path(path).resolve().relative_to(project_root).as_posix()
    except ValueError:
        return Path(path).name


def read_queries():
    with QUERIES_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def already_labeled():
    if not JUDGMENTS_PATH.exists():
        return False
    with JUDGMENTS_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return any((row.get("relevant") or "").strip() for row in csv.DictReader(f))


def main():
    if already_labeled():
        if "--overwrite" not in sys.argv:
            print("judgments.csv 已經有判讀結果，為避免覆蓋，程式停止。")
            print("確定要重跑請加 --overwrite（舊檔會先備份成 judgments.backup.csv）。")
            sys.exit(1)
        JUDGMENTS_PATH.replace(EVAL_DIR / "judgments.backup.csv")

    index = config.load_index()
    queries = read_queries()
    rows = []
    for q in queries:
        results = config.search(q["query"], index, top_k=CUTOFF)
        print(f"\n{q['query_id']} {q['query']}（{len(results)} 筆）")
        if len(results) < CUTOFF:
            print(f"  注意：只回傳 {len(results)} 筆，缺少的名次在 P@5 視為不相關")
        for rank, (doc_id, score) in enumerate(results, start=1):
            doc = index["documents"][str(doc_id)]
            print(f"  {rank}. [{doc_id}] {score:.4f} {doc['title'][:70]}")
            rows.append({
                "query_id": q["query_id"], "query": q["query"], "rank": rank,
                "doc_id": doc_id, "url": doc["url"], "title": doc["title"],
                "score": f"{score:.6f}", "relevant": "", "reason": "",
                "judge": "", "second_review": "",
            })

    # utf-8-sig：用 Excel 開啟中文不會變亂碼
    with JUDGMENTS_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    run_info = {
        "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "index_path": relative_path(config.INDEX_PATH),
        "index_sha256": sha256(config.INDEX_PATH),
        "num_documents": len(index["documents"]),
        "search_module": config.search.__module__,
        "queries_sha256": sha256(QUERIES_PATH),
        "cutoff": CUTOFF,
    }
    with RUN_INFO_PATH.open("w", encoding="utf-8") as f:
        json.dump(run_info, f, ensure_ascii=False, indent=2)

    print(f"\n已產生 {JUDGMENTS_PATH.name}（{len(rows)} 列），請填 relevant（1/0）與 reason。")
    print(f"索引快照資訊已存到 {RUN_INFO_PATH.name}")


if __name__ == "__main__":
    main()
