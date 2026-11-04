"""暫代 C 的搜尋函式（D 測試用）

C 交出正式的 search.py 後，只要到 config.py 改 import 那一行即可。
這裡的約定介面（建議 C 沿用）：

    search(query: str, index: dict, top_k: int = 10) -> list[tuple[str, float]]
    回傳 [(doc_id, score), ...]，只含 score > 0，依分數由高到低排序

做法：查詢使用與 B 相同的拆字與 TF 公式，沿用索引裡的 IDF（不重算），
用倒排索引找出含查詢詞的候選文件，再算 TF-IDF 向量的餘弦相似度。
"""
import math
import re
from collections import Counter


def tokenize(text):
    """與 B 相同：轉小寫，以連續 a-z 為單字。"""
    return re.findall(r"[a-z]+", text.lower())


def search(query, index, top_k=10):
    tokens = tokenize(query or "")
    if not tokens:
        return []

    idf = index["idf_scores"]
    counts = Counter(tokens)
    n = len(tokens)

    # 查詢向量：TF = 次數 / 查詢單字總數，IDF 沿用索引；詞彙外的字略過
    q_weights = {
        t: (c / n) * idf[t]
        for t, c in counts.items()
        if t in idf and idf[t] > 0
    }
    q_norm = math.sqrt(sum(w * w for w in q_weights.values()))
    if q_norm == 0:  # 全是詞彙外的字，或只含出現在每一篇的字（IDF = 0）
        return []

    # 用倒排索引取得候選文件並累加內積
    dot = {}
    tfidf = index["tfidf_scores"]
    for term, qw in q_weights.items():
        for doc_id in index["inverted_index"][term]:
            dot[doc_id] = dot.get(doc_id, 0.0) + qw * tfidf[doc_id][term]

    norms = index["document_norms"]
    results = [
        (doc_id, score / (q_norm * norms[doc_id]))
        for doc_id, score in dot.items()
        if norms[doc_id] > 0
    ]
    results = [(d, s) for d, s in results if s > 0]
    results.sort(key=lambda x: (-x[1], int(x[0])))
    return results[:top_k]
