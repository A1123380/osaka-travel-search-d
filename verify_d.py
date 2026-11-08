"""D 的一鍵自我檢查

執行：py verify_d.py
什麼時候跑：
  - 現在（用暫用索引與暫用搜尋）
  - B 交出正式索引、或 C 交出 search.py、改完 config.py 之後一定要再跑一次
  - Demo 前最後確認

檢查項目對照老師規格第 4、6 節與評分表；全部通過時結束代碼為 0。
"""
import math
import re
import sys
from collections import Counter
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
sys.path.insert(0, str(FOLDER))
sys.path.insert(0, str(FOLDER / "evaluation"))

import config  # noqa: E402

results = []


def check(name, ok, detail="", level="失敗"):
    results.append((name, bool(ok), detail, level))
    tag = "[通過]" if ok else f"[{level}]"
    print(f"{tag} {name}" + (f"：{detail}" if detail and not ok else ""))


def section(title):
    print(f"\n=== {title} ===")


# ---------------------------------------------------------------- 1. 索引
section("1. 索引檔（B 的輸出）")
try:
    index = config.load_index()
    loaded = True
except Exception as e:  # noqa: BLE001
    loaded = False
    check("索引可以讀取", False, f"{config.INDEX_PATH}：{e}")
    sys.exit(1)

check("索引可以讀取", loaded)
need = ["documents", "inverted_index", "df_scores", "idf_scores",
        "tfidf_scores", "document_norms"]
missing = [k for k in need if k not in index]
check("索引包含必要欄位", not missing, f"缺少 {missing}")
docs = index["documents"]
print(f"      文件數 {len(docs)}，詞彙數 {len(index['inverted_index'])}")
check("文件數在 200–1000 之間", 200 <= len(docs) <= 1000, f"目前 {len(docs)} 篇")
bad_doc = [d for d, p in docs.items()
           if not all(k in p for k in ("url", "title", "text", "fetch_time"))]
check("每篇文件都有 url/title/text/fetch_time", not bad_doc, f"有問題的文件 {bad_doc[:5]}")

# 參考檢查：索引的 TF-IDF 是否符合 B 宣告的公式（不符時只提醒，屬於 B 的範圍）
idf = index["idf_scores"]
mismatch = 0
for d, page in docs.items():
    toks = config.tokenize(page["text"])
    if not toks:
        continue
    c = Counter(toks)
    for t, w in index["tfidf_scores"][d].items():
        if abs((c.get(t, 0) / len(toks)) * idf.get(t, 0) - w) > 1e-9:
            mismatch += 1
            break
check("索引權重符合「TF=次數/總字數、IDF=log10(N/DF)」", mismatch == 0,
      f"{mismatch} 篇不一致；若 B 改了公式或拆字，請確認 C 的查詢也同步", level="提醒")

# ---------------------------------------------------------------- 2. 搜尋函式
section("2. 搜尋函式（C 的輸出，或暫用 search_temp）")
print(f"      目前使用：{config.SEARCH_SOURCE}")


def brute_force(query):
    """不用倒排索引，直接對全部文件算餘弦相似度，當作標準答案。"""
    toks = config.tokenize(query)
    if not toks:
        return {}
    c = Counter(toks)
    qv = {t: (k / len(toks)) * idf[t] for t, k in c.items() if idf.get(t, 0) > 0}
    qn = math.sqrt(sum(v * v for v in qv.values()))
    if qn == 0:
        return {}
    out = {}
    for d, weights in index["tfidf_scores"].items():
        dn = index["document_norms"][d]
        s = sum(qv[t] * weights.get(t, 0) for t in qv)
        if s > 0 and dn > 0:
            out[str(d)] = s / (qn * dn)
    return out


import csv  # noqa: E402

with (FOLDER / "evaluation" / "queries.csv").open(encoding="utf-8-sig", newline="") as f:
    test_queries = [row["query"] for row in csv.DictReader(f)]
test_queries += ["osaka", "castle", "kōshōji"]

format_errors, rank_errors = [], []
for q in test_queries:
    res = config.search(q, index, top_k=10)
    if not isinstance(res, list) or len(res) > 10:
        format_errors.append(f"{q}：不是 list 或超過 10 筆")
        continue
    if any(not (isinstance(x, (tuple, list)) and len(x) == 2) for x in res):
        format_errors.append(f"{q}：元素不是 (doc_id, score)")
        continue
    scores = [s for _, s in res]
    if any(s <= 0 for s in scores):
        format_errors.append(f"{q}：含有分數 <= 0 的結果")
    if scores != sorted(scores, reverse=True):
        format_errors.append(f"{q}：沒有依分數由高到低排序")
    if any(str(d) not in docs for d, _ in res):
        format_errors.append(f"{q}：回傳的文件編號不在索引中")

    truth = brute_force(q)
    expect = sorted(truth.values(), reverse=True)[:10]
    if len(scores) != len(expect) or any(abs(a - b) > 1e-9 for a, b in zip(scores, expect)):
        rank_errors.append(f"{q}：前 10 名分數與標準答案不同")
    elif any(abs(truth.get(str(d), -1) - s) > 1e-9 for d, s in res):
        rank_errors.append(f"{q}：某篇文件的分數算錯")

check("回傳格式：list[(doc_id, score)]、最多 10 筆、分數 > 0、由高到低",
      not format_errors, "; ".join(format_errors[:3]))
check(f"排名與暴力法餘弦相似度一致（{len(test_queries)} 組查詢）",
      not rank_errors, "; ".join(rank_errors[:3]))
for q in ["", "   ", "2026", "zzqxv"]:
    try:
        r = config.search(q, index, top_k=10)
        check(f"特殊查詢「{q}」不會出錯且回傳空結果", r == [], f"回傳 {r[:2]}")
    except Exception as e:  # noqa: BLE001
        check(f"特殊查詢「{q}」不會出錯且回傳空結果", False, repr(e))

# ---------------------------------------------------------------- 3. 網頁
section("3. Flask 網頁（D）")
import app as web  # noqa: E402

client = web.app.test_client()


def page(q=None):
    url = "/" if q is None else "/?q=" + q
    r = client.get(url)
    return r.status_code, r.get_data(as_text=True)


code, html = page()
check("首頁可以開啟", code == 200, f"HTTP {code}")
check("首頁顯示索引篇數", f"<strong>{len(docs)}</strong>" in html)

for q, label in [("", "空白"), ("%20%20", "只有空格"), ("2026", "只有數字"),
                 ("zzqxv", "詞彙外")]:
    code, html = page(q)
    check(f"{label}查詢顯示提示訊息", code == 200 and 'class="message"' in html,
          f"HTTP {code}")

code, html = page("%3Cscript%3Ealert(1)%3C/script%3E%20castle")
check("輸入 <script> 會被跳脫，不會執行",
      "<script>alert" not in html and "&lt;script&gt;" in html)

snippet_errors, link_errors, field_errors = [], [], []
for q in test_queries[:10]:
    code, html = page(q)
    items = re.findall(r"<li>(.*?)</li>", html, re.S)
    if len(items) > 10:
        field_errors.append(f"{q}：超過 10 筆")
    for it in items:
        for cls in ("title", "url", "snippet", "score"):
            if f'class="{cls}' not in it:
                field_errors.append(f"{q}：缺少 {cls}")
        for href in re.findall(r'href="([^"]*)"', it):
            if not re.match(r"https?://", href):
                link_errors.append(href)
        m = re.search(r'<p class="snippet">(.*?)</p>', it, re.S)
        if m:
            words = [w for w in re.sub(r"<.*?>", "", m.group(1)).split() if w != "…"]
            doc_id = re.search(r"文件編號 (\d+)", it).group(1)
            full_len = len(docs[doc_id]["text"].split())
            if not (50 <= len(words) <= 100 or len(words) == full_len):
                snippet_errors.append(f"{q} 文件 {doc_id}：{len(words)} 字")

check("每筆結果都有標題、網址、摘要、分數，且最多 10 筆",
      not field_errors, "; ".join(field_errors[:3]))
check("所有結果連結都是 http/https", not link_errors, str(link_errors[:3]))
check("摘要長度 50–100 字（文章較短時為全文）", not snippet_errors,
      "; ".join(snippet_errors[:3]))
check("javascript: 網址不會變成連結", web.safe_url("javascript:alert(1)") is None)
check("頁面顯示查詢耗時", "搜尋耗時" in page("castle")[1])

# ---------------------------------------------------------------- 4. 評估
section("4. 評估計算（D）")
from compute_p5 import precision_at_k  # noqa: E402

check("P@5：前 5 名有 3 篇相關 = 0.60",
      precision_at_k({1: 1, 2: 0, 3: 1, 4: 0, 5: 1}) == 0.6)
check("P@5：只回傳 2 筆且都相關 = 0.40（分母仍為 5）",
      precision_at_k({1: 1, 2: 1}) == 0.4)
check("P@5：沒有結果 = 0", precision_at_k({}) == 0)
check("queries.csv 正好 10 組且不重複",
      len(test_queries) - 3 == 10 and len(set(test_queries[:10])) == 10,
      f"目前 {len(test_queries) - 3} 組")

# ---------------------------------------------------------------- 結果
failed = [r for r in results if not r[1] and r[3] == "失敗"]
warned = [r for r in results if not r[1] and r[3] != "失敗"]
print(f"\n共 {len(results)} 項：通過 {len(results) - len(failed) - len(warned)}，"
      f"失敗 {len(failed)}，提醒 {len(warned)}")
if config.USE_TEMP:
    print("注意：目前仍在使用暫用索引或暫用搜尋，B、C 交件並改 config.py 後請再跑一次。")
sys.exit(1 if failed else 0)
