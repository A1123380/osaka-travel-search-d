"""暫用索引建立程式（D 測試用，不是正式交件的 indexer）

用途：B 的正式索引還沒出來前，先用 A 的 323 篇資料建立一份索引，
讓 D 的介面和評估流程可以先跑起來。

計算規則完全照 B 的 search_b_web.py：
  - 拆字：轉小寫，以連續 a-z 為單字，保留停用詞、不做詞幹處理
  - TF  = 單字出現次數 / 該篇單字總數
  - IDF = log10(文件總數 / DF)
  - TF-IDF = TF × IDF，文件向量長度 = sqrt(Σ TF-IDF²)
輸出格式也與 B 的 index_web_sample.json 相同（文件編號為字串 "1"、"2"…）。

B 交出正式索引後，請改用 B 的索引檔（見 README.md），本檔即可不用。

執行：py build_temp_index.py
"""
import json
import math
import re
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
INPUT_PATH = FOLDER.parent / "1111" / "osaka_pages_cleaned.json"
OUTPUT_PATH = FOLDER / "data" / "index_temp.json"


def tokenize(text):
    return re.findall(r"[a-z]+", text.lower())


def main():
    with INPUT_PATH.open("r", encoding="utf-8-sig") as f:
        pages = json.load(f)

    inverted_index = {}
    doc_tokens = {}
    for doc_id, page in enumerate(pages, start=1):
        words = tokenize(page["text"])
        if not words:
            raise ValueError(f"文件 {doc_id} 沒有可用的英文單字。")
        doc_tokens[doc_id] = words
        for word in words:
            postings = inverted_index.setdefault(word, {})
            postings[doc_id] = postings.get(doc_id, 0) + 1

    total = len(pages)
    df_scores = {w: len(p) for w, p in inverted_index.items()}
    idf_scores = {w: math.log10(total / df) for w, df in df_scores.items()}

    tfidf_scores = {}
    document_norms = {}
    for doc_id, words in doc_tokens.items():
        n = len(words)
        weights = {
            w: (inverted_index[w][doc_id] / n) * idf_scores[w]
            for w in set(words)
        }
        tfidf_scores[doc_id] = weights
        document_norms[doc_id] = math.sqrt(sum(v * v for v in weights.values()))

    output = {
        "documents": {doc_id: page for doc_id, page in enumerate(pages, start=1)},
        "inverted_index": inverted_index,
        "df_scores": df_scores,
        "idf_scores": idf_scores,
        "tfidf_scores": tfidf_scores,
        "document_norms": document_norms,
        "settings": {
            "indexed_fields": ["text"],
            "tokenization": "轉小寫，以連續 a-z 為單字",
            "stopwords": "保留所有停用詞",
            "stemming": "不做詞幹處理",
            "tf": "單字出現次數 / 文件單字總數",
            "idf": "log10(文件總數 / DF)",
            "note": "D 暫用索引（build_temp_index.py），正式版以 B 為準",
        },
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)

    print(f"文件數：{total}，詞彙數：{len(inverted_index)}")
    print(f"已儲存：{OUTPUT_PATH}")


if __name__ == "__main__":
    main()
