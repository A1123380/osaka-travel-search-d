"""D｜Flask 搜尋介面

執行：py app.py  然後打開 http://127.0.0.1:5000

功能：
  - 搜尋框與結果頁，顯示索引篇數
  - 每筆結果顯示：標題、網址、摘要、分數（最多 10 筆，只顯示分數 > 0）
  - 空白查詢、詞彙外查詢、查無結果時顯示清楚訊息
  - 摘要：以查詢詞第一次出現的位置為中心，取約 60 個英文字
  - 只對 http/https 網址輸出連結；所有文字都經 Jinja 自動跳脫（不使用 |safe）
  - 顯示查詢耗時（計時範圍見 timed_search 的說明）
"""
import time
from urllib.parse import urlparse

from flask import Flask, render_template, request

from config import load_index, search, tokenize

SNIPPET_WORDS = 60      # 規格要求約 50–100 個英文字
SNIPPET_LEAD = 15       # 命中字前面保留幾個字
TOP_K = 10
MAX_QUERY_CHARS = 200

app = Flask(__name__)
INDEX = load_index()
DOCUMENTS = INDEX["documents"]
NUM_DOCS = len(DOCUMENTS)


def timed_search(query):
    """計時範圍：只包含 search()，也就是查詢拆字、查倒排索引、計算餘弦相似度與排序。
    不包含載入索引（啟動時只做一次）、產生摘要與網頁渲染。"""
    start = time.perf_counter()
    results = search(query, INDEX, top_k=TOP_K)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return results, elapsed_ms


def safe_url(url):
    """只接受 http/https 網址，其他一律不輸出成連結。"""
    try:
        scheme = urlparse(url).scheme.lower()
    except (ValueError, AttributeError):
        return None
    return url if scheme in ("http", "https") else None


def make_snippet(text, query_terms):
    """回傳 [(文字片段, 是否為查詢詞), ...]，由模板逐段輸出（自動跳脫）。"""
    words = text.split()
    if not words:
        return []

    hit_at = next(
        (i for i, w in enumerate(words) if set(tokenize(w)) & query_terms),
        None,
    )
    start = 0 if hit_at is None else max(0, hit_at - SNIPPET_LEAD)
    end = min(len(words), start + SNIPPET_WORDS)
    start = max(0, end - SNIPPET_WORDS)

    segments = []
    if start > 0:
        segments.append(("… ", False))
    for i in range(start, end):
        word = words[i]
        is_hit = bool(set(tokenize(word)) & query_terms)
        text_part = word if i == end - 1 else word + " "
        if segments and segments[-1][1] == is_hit and segments[-1][0] != "… ":
            segments[-1] = (segments[-1][0] + text_part, is_hit)
        else:
            segments.append((text_part, is_hit))
    if end < len(words):
        segments.append((" …", False))
    return segments


@app.route("/")
def home():
    raw_query = request.args.get("q")
    context = {"num_docs": NUM_DOCS, "query": "", "results": None,
               "message": None, "elapsed_ms": None}

    if raw_query is None:  # 第一次進入頁面，還沒搜尋
        return render_template("search.html", **context)

    query = raw_query.strip()[:MAX_QUERY_CHARS]
    context["query"] = query

    if not query:
        context["message"] = "請輸入查詢關鍵字。"
        return render_template("search.html", **context)

    tokens = tokenize(query)
    if not tokens:
        context["message"] = "查詢中沒有可搜尋的英文單字（本系統只索引英文字母 a–z）。"
        return render_template("search.html", **context)

    results, elapsed_ms = timed_search(query)
    context["elapsed_ms"] = elapsed_ms

    if not results:
        in_vocab = [t for t in set(tokens) if t in INDEX["idf_scores"]]
        if not in_vocab:
            context["message"] = f"查無結果：查詢詞「{query}」不在索引詞彙中，請換個關鍵字。"
        else:
            context["message"] = f"查無結果：沒有文件與「{query}」相符。"
        context["results"] = []
        return render_template("search.html", **context)

    query_terms = {t for t in tokens if INDEX["idf_scores"].get(t, 0) > 0}
    items = []
    for rank, (doc_id, score) in enumerate(results, start=1):
        doc = DOCUMENTS[str(doc_id)]
        items.append({
            "rank": rank,
            "doc_id": doc_id,
            "title": doc.get("title") or "(無標題)",
            "url": doc.get("url", ""),
            "href": safe_url(doc.get("url", "")),
            "score": score,
            "snippet": make_snippet(doc.get("text", ""), query_terms),
        })
    context["results"] = items
    return render_template("search.html", **context)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
