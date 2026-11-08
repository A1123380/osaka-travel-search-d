import json
import math
import re
from collections import Counter
from pathlib import Path

# 讀取 B 組正式索引
folder = Path(__file__).resolve().parent
index_path = folder / "index_osaka.json"

with index_path.open("r", encoding="utf-8") as file:
    data = json.load(file)

documents = data["documents"]
inverted_index = data["inverted_index"]
idf_scores = data["idf_scores"]
tfidf_scores = data["tfidf_scores"]
document_norms = data["document_norms"]


# C 組搜尋功能，提供 D 組直接呼叫
def search(query, top_k=10):

    # 英文小寫，只保留連續 a-z
    words = re.findall(r"[a-z]+", query.lower())

    if not words:
        return []

    # 計算查詢關鍵字 TF-IDF
    word_counts = Counter(words)
    query_tfidf = {}

    for word, count in word_counts.items():
        if word in idf_scores:
            tf = count / len(words)
            query_tfidf[word] = tf * idf_scores[word]

    if not query_tfidf:
        return []

    # 找出候選文章
    result_ids = set()

    for word in query_tfidf:
        result_ids.update(inverted_index.get(word, {}).keys())

    # 計算查詢向量長度
    query_norm = math.sqrt(
        sum(score ** 2 for score in query_tfidf.values())
    )

    if query_norm == 0:
        return []

    ranking_results = []

    # 計算餘弦相似度
    for doc_id in result_ids:

        doc_tfidf = tfidf_scores[doc_id]
        doc_norm = document_norms[doc_id]

        if doc_norm == 0:
            continue

        dot_product = sum(
            query_score * doc_tfidf.get(word, 0.0)
            for word, query_score in query_tfidf.items()
        )

        similarity = dot_product / (query_norm * doc_norm)

        if similarity > 0:
            page = documents[doc_id]

            ranking_results.append({
                "doc_id": doc_id,
                "title": page["title"],
                "url": page["url"],
                "similarity": similarity
            })

    # 依照相似度由高到低排序
    ranking_results.sort(
        key=lambda item: (-item["similarity"], int(item["doc_id"]))
    )

    return ranking_results[:top_k]


# 單獨執行時的測試功能
if __name__ == "__main__":

    print(f"成功讀取 B 組資料！目前共有 {len(documents)} 篇文章。")

    query = input("請輸入英文搜尋關鍵字：")

    results = search(query)

    print("\n===== 搜尋排名結果（前10筆） =====")

    if not results:
        print("找不到符合的文章。")

    else:
        for rank, item in enumerate(results, start=1):

            print(f"\n第 {rank} 名（文件 {item['doc_id']}）")
            print("文章標題：", item["title"])
            print("文章網址：", item["url"])
            print(f"相似度：{item['similarity']:.4f}")