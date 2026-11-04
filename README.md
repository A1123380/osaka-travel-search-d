# osaka-travel-search-d

大阪旅遊資訊搜尋引擎（Information Retrieval and Generative AI, Term Project I）的 **D 部分**：Flask 搜尋介面、Precision@5 評估、查詢耗時量測（加分項）。

本 repo 只包含 D（奕宗）負責的程式。其他部分由組員負責，不在此 repo：
A 爬蟲（宏逸）、B 倒排索引與 TF-IDF（育翎）、C 查詢處理與排序（于玲）。

> **資料來源**：執行 `build_temp_index.py` 需要 A 的爬蟲資料 `osaka_pages_cleaned.json`（323 篇），
> 請放在本資料夾上一層的 `1111/` 目錄（即 `../1111/osaka_pages_cleaned.json`）。
> 產生的索引 `data/index_temp.json` 不納入版控，執行程式即可重新產生。

## 資料夾內容

```
D部分_搜尋介面與評估/
├── app.py                    Flask 搜尋介面（主程式）
├── config.py                 共用設定：索引路徑、搜尋函式來源（整合時只改這裡）
├── search_temp.py            【暫用】代替 C 的搜尋函式，C 交件後換掉
├── build_temp_index.py       【暫用】照 B 的規則用 323 篇建索引，B 交件後換掉
├── requirements.txt          套件版本
├── templates/search.html     搜尋頁與結果頁模板
├── static/style.css          版面樣式
├── data/index_temp.json      【暫用】索引（由 build_temp_index.py 產生）
└── evaluation/
    ├── queries.csv           10 組查詢、資訊需求、相關性規則（草案，待全組確認）
    ├── run_evaluation.py     跑 10 組查詢 → 產生 judgments.csv 與 run_info.json
    ├── judgments.csv         判讀表：relevant（1/0）、reason 待填
    ├── run_info.json         評估用的索引快照（SHA-256），確保可重現
    ├── compute_p5.py         計算每組 P@5 與平均 → p5_results.csv
    └── benchmark_query_time.py  查詢耗時量測 → query_time_summary.csv
```

## 安裝與執行

環境：Python 3.10.0、Flask 3.1.3

```bash
py -m pip install -r requirements.txt
py build_temp_index.py        # 只在還沒有 B 的正式索引時需要
py app.py                     # 開啟 http://127.0.0.1:5000
```

## 自我檢查

```bash
py verify_d.py
```

共 27 項自動檢查，涵蓋索引格式、搜尋回傳格式、排名正確性（和暴力法算出的餘弦相似度比對）、特殊查詢、網頁欄位、連結安全、摘要長度、P@5 公式。
B、C 交件並改完 `config.py` 後，一定要再跑一次。

## 介面功能（對應規格第 4 節）

| 規格要求 | 做法 |
|---|---|
| 搜尋框與結果頁 | 單一頁面 `/?q=查詢` |
| 標題、網址、摘要、分數 | 每筆都顯示，另附文件編號（方便評估對照） |
| 顯示索引篇數 | 頁首「已索引 323 篇網頁」 |
| 最多 10 筆、分數 > 0 | 由搜尋函式保證 |
| 空白查詢 / 查無結果 | 分別顯示：請輸入關鍵字、沒有英文單字、詞彙外、無相符文件 |
| 摘要 50–100 字 | 以查詢詞第一次出現的位置為中心取 60 個英文字，查詢詞以底色標示；文章較短時顯示全文 |
| 只輸出 http/https 連結 | `safe_url()` 檢查，其他網址只顯示文字、不做連結 |
| 安全顯示 | 所有內容經 Jinja 自動跳脫，不使用 `\|safe`；已測試 `<script>` 查詢會被跳脫 |
| 查詢耗時（加分） | 只計算 `search()`：拆字、查倒排索引、餘弦相似度、排序；不含載入索引、摘要與渲染 |

摘要不取文章開頭，是因為很多頁面開頭是導覽文字（例如 `PLAY FULL VIDEO Tickets Must see!...`）。

## 和 B、C 的串接

約定介面（建議 C 沿用）：

```python
search(query: str, index: dict, top_k: int = 10) -> list[tuple[str, float]]
# 回傳 [(doc_id, score), ...]，只含 score > 0，依分數由高到低
```

整合步驟，只要改 `config.py`：
1. **B 交出正式索引**：把 `INDEX_PATH` 改成 B 的索引檔。索引格式需與 B 的 `index_web_sample.json` 相同。
2. **C 交出 `search.py`**：放進本資料夾，把 `from search_temp import ...` 改成 `from search import search, tokenize`。
3. 重新執行 `py evaluation/run_evaluation.py`（判讀表還沒填之前可以隨時重跑）。

## 評估流程（對應規格第 6 節）

1. **凍結查詢**：全組確認 `evaluation/queries.csv` 的 10 組查詢之後就不再修改，也不要因為結果不好而換查詢。
2. **凍結索引**：B 和 C 的正式版確定後執行
   ```bash
   py evaluation/run_evaluation.py
   ```
   會產生 `judgments.csv`（50 列），並把索引的 SHA-256 記錄在 `run_info.json`。
3. **人工判讀**：讀每篇的**內文**（不能只看標題），依該查詢的相關性規則填寫：
   - `relevant`：1 = 相關，0 = 不相關
   - `reason`：一句判斷理由
   - `judge`：判讀人；`second_review`：有疑義時請另一位組員複核並簽名
4. **計算 P@5**
   ```bash
   py evaluation/compute_p5.py
   ```
   P@5 = 前 5 名中相關的篇數 / 5。回傳不足 5 筆時，缺少的名次視為不相關，分母仍為 5。結果存在 `p5_results.csv`，最後一列是 10 組平均。
   程式會檢查目前的索引是否和 `run_info.json` 記錄的相同，不同時會顯示警告。
5. **查詢耗時（加分）**
   ```bash
   py evaluation/benchmark_query_time.py
   ```
   10 組查詢各暖身 1 次，再各跑 100 次，回報平均、中位數、最大值。

保護機制：`judgments.csv` 已經有人填過 `relevant` 時，`run_evaluation.py` 會拒絕覆蓋。確定要重跑請加 `--overwrite`，舊檔會先備份成 `judgments.backup.csv`。

## 已驗證

- 用 323 篇暫用索引測試 3 組查詢，`search_temp.py` 的排名和分數，與不經倒排索引、直接算全部文件餘弦相似度的暴力法完全一致。
- 介面測試通過：首次進入、空白、只有空格、只有數字、詞彙外、`<script>` 注入、一般查詢。
- 用模擬判讀資料驗證 P@5：前 5 名有 3 篇相關得 0.60；只回傳 2 篇且都相關得 0.40，與規格範例一致。
