"""判讀表：產生附內文的判讀表 → 填寫 → 合併回 judgments.csv

產生：py evaluation/judging_split.py split
      產生 evaluation/judging/判讀_D.csv（10 組查詢共 50 筆，由 D 判讀）
      每列附上相關性規則、該篇開頭（看出主題）與含查詢詞的句子；最後一欄是完整內文，不確定時再看

合併：py evaluation/judging_split.py merge
      讀取 evaluation/judging/判讀_*.csv，把 relevant、reason 填回 judgments.csv
      會檢查文件編號是否對得上，不會用空白蓋掉已經填好的值

填寫：只要填 relevant（1 = 相關，0 = 不相關）和 reason（一句理由），其他欄位不要改。
用 Excel 存檔時請選「CSV UTF-8（逗號分隔）」；存成一般 CSV 也能讀。
"""
import csv
import re
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR.parent))

import config  # noqa: E402

JUDGMENTS_PATH = EVAL_DIR / "judgments.csv"
QUERIES_PATH = EVAL_DIR / "queries.csv"
OUT_DIR = EVAL_DIR / "judging"

# 判讀者與負責的查詢（全部由 D 判讀）
ASSIGN = {
    "D": [f"Q{i:02d}" for i in range(1, 11)],
}
SPLIT_FIELDS = ["query_id", "rank", "relevant", "reason", "query", "title",
                "page_start", "key_sentences", "relevance_rule", "url", "doc_id", "text"]
LEAD_CHARS = 200      # 開頭摘錄長度
MAX_SENTENCES = 3     # 含查詢詞的句子最多幾句
SENTENCE_CHARS = 250  # 每句最長字數


def key_sentences(text, query):
    """挑出含最多查詢詞的句子（依原文順序），讓判讀時不必讀整篇。"""
    terms = {t for t in config.tokenize(query) if len(t) > 2}
    sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+", text) if x.strip()]
    scored = []
    for i, sent in enumerate(sentences):
        hits = terms & set(config.tokenize(sent))
        if hits:
            scored.append((len(hits), -i, sent))
    best = sorted(scored, reverse=True)[:MAX_SENTENCES]
    best.sort(key=lambda x: -x[1])
    return " ／ ".join(s[:SENTENCE_CHARS] for _, _, s in best) or "（內文沒有查詢詞）"


def read_csv(path):
    """先試 UTF-8，失敗再試 cp950（Excel 存成一般 CSV 時的編碼）。"""
    for enc in ("utf-8-sig", "cp950"):
        try:
            with Path(path).open("r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f)), enc
        except UnicodeDecodeError:
            continue
    raise ValueError(f"無法讀取 {path}，請用「CSV UTF-8」格式存檔")


def write_csv(path, fields, rows):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def split():
    judgments, _ = read_csv(JUDGMENTS_PATH)
    queries = {q["query_id"]: q for q in read_csv(QUERIES_PATH)[0]}
    docs = config.load_index()["documents"]
    OUT_DIR.mkdir(exist_ok=True)

    assigned = {qid for qids in ASSIGN.values() for qid in qids}
    missing = set(queries) - assigned
    if missing:
        print(f"注意：{sorted(missing)} 沒有分配給任何人")

    for person, qids in ASSIGN.items():
        rows = []
        for row in judgments:
            if row["query_id"] in qids:
                q = queries[row["query_id"]]
                text = docs[str(row["doc_id"])]["text"]
                rows.append({**row,
                             "relevance_rule": q["relevance_rule"],
                             "page_start": text[:LEAD_CHARS] + ("…" if len(text) > LEAD_CHARS else ""),
                             "key_sentences": key_sentences(text, row["query"]),
                             "text": text})
        path = OUT_DIR / f"判讀_{person}.csv"
        write_csv(path, SPLIT_FIELDS, rows)
        print(f"{path.name}：{'、'.join(qids)}，共 {len(rows)} 筆")


def merge():
    judgments, _ = read_csv(JUDGMENTS_PATH)
    by_key = {(r["query_id"], str(r["rank"])): r for r in judgments}
    filled, problems = 0, []

    for path in sorted(OUT_DIR.glob("判讀_*.csv")):
        person = path.stem.split("_", 1)[1]
        rows, enc = read_csv(path)
        for row in rows:
            key = (row.get("query_id", ""), str(row.get("rank", "")))
            target = by_key.get(key)
            if target is None:
                problems.append(f"{path.name}：找不到 {key[0]} 第 {key[1]} 名")
                continue
            if str(row.get("doc_id")) != str(target["doc_id"]):
                problems.append(f"{path.name}：{key[0]} 第 {key[1]} 名的文件編號不符，請勿修改 doc_id")
                continue
            rel = (row.get("relevant") or "").strip()
            reason = (row.get("reason") or "").strip()
            if rel not in ("", "0", "1"):
                problems.append(f"{path.name}：{key[0]} 第 {key[1]} 名 relevant 應為 1 或 0（目前是「{rel}」）")
                continue
            if rel:
                target["relevant"] = rel
                target["judge"] = target.get("judge") or person
                filled += 1
            if reason:
                target["reason"] = reason
        print(f"已讀取 {path.name}（{enc}）")

    fields = list(judgments[0].keys())
    write_csv(JUDGMENTS_PATH, fields, judgments)
    blank = sum(1 for r in judgments if not (r.get("relevant") or "").strip())
    print(f"\n合併完成：填入 {filled} 筆，尚未判讀 {blank} 筆")
    for p in problems:
        print("  -", p)
    if not blank and not problems:
        print("全部判讀完成，可以執行 py evaluation/compute_p5.py")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action == "split":
        split()
    elif action == "merge":
        merge()
    else:
        print(__doc__)
