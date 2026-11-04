# osaka-travel-search-d

大阪旅遊搜尋引擎的 **D 部分**：Flask 搜尋網頁 + Precision@5 評估。
（A 爬蟲、B 索引、C 搜尋排序由其他組員負責，不在此 repo。）

## 執行

需要 Python 3.10、Flask 3.1.3，以及 A 的資料 `../1111/osaka_pages_cleaned.json`。

```bash
py -m pip install -r requirements.txt
py build_temp_index.py   # 建立暫用索引（B 正式版出來後不需要）
py app.py                # 開啟 http://127.0.0.1:5000
py verify_d.py           # 自我檢查
```

## 檔案

| 檔案 | 說明 |
|---|---|
| `app.py`、`templates/`、`static/` | 搜尋網頁 |
| `config.py` | 設定索引和搜尋函式來源 |
| `search_temp.py`、`build_temp_index.py` | 暫用，B、C 正式版出來後替換 |
| `verify_d.py` | 自我檢查 |
| `evaluation/` | 10 組查詢、判讀表、P@5 計算、查詢耗時 |

## 串接 B、C

只改 `config.py`：
- B 的索引 → 改 `INDEX_PATH`
- C 的 `search.py` → 改成 `from search import search, tokenize`

C 的函式格式：`search(query, index, top_k=10)` → `[(文件編號, 分數), ...]`，只回傳分數 > 0、最多 10 筆、由高到低。

## 評估步驟

```bash
py evaluation/run_evaluation.py      # 1. 產生 judgments.csv
                                     # 2. 讀內文，填 relevant（1/0）和 reason
py evaluation/compute_p5.py          # 3. 計算 P@5
py evaluation/benchmark_query_time.py  # 4. 查詢耗時（加分）
```

P@5 = 前 5 名中相關的篇數 / 5；回傳不足 5 筆時，分母仍為 5。
