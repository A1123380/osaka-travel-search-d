# 審核工單：大阪旅遊搜尋引擎 D 部分（Flask 介面 + Precision@5 評估）

- 建立日期：2026-11-09
- 截止：11/11 課堂 Demo，11/12 23:59 交件
- 審核範圍：`D部分_搜尋介面與評估/` 資料夾（以下路徑皆相對於此資料夾）
- 審核方式：**唯讀**。請不要修改、刪除或重新產生任何檔案。需要執行時，請先複製整個資料夾到暫存位置再執行。

---

## 1. 背景

這是課程「資訊檢索與生成式人工智慧」的期中小組專題：用傳統 IR 實作的網頁搜尋引擎。作業規格寫明**不需要** LLM、embeddings 或 RAG。規格 PDF 在 `../課程規格/termProjectI_Web_Search_Engine_c544708bfc048e921b3001918a1dd754.pdf`。

| 部分 | 內容 | 本次是否審核 |
|---|---|---|
| A | 爬蟲，323 篇英文大阪旅遊網頁（`../A_爬蟲資料/osaka_pages_cleaned.json`） | 否 |
| B | 倒排索引與 TF-IDF（`c_module/index_osaka.json`，B 交付） | 只審 D 如何使用它 |
| C | 查詢與餘弦排序（`c_module/search_c_module.py`，C 交付，D 未修改） | 只審 D 的串接 |
| **D** | Flask 搜尋網頁、Precision@5 評估、查詢耗時量測 | **是** |

B 的公式（規格要求寫明）：
- 拆字：`re.findall(r"[a-z]+", text.lower())`，保留停用詞，不做詞幹化
- TF = 次數 / 該篇單字總數；IDF = log10(N / DF)，不平滑；權重 = TF × IDF
- 文件向量長度 = sqrt(Σ 權重²)；查詢沿用索引中的 IDF

---

## 2. 需要審核的檔案

| 檔案 | 重點 |
|---|---|
| `config.py` | 串接 C：`search()` 把 C 回傳的 dict 清單轉成 `[(doc_id, score)]`；`INDEX_PATH` 指向 C 讀取的同一份索引 |
| `app.py` | `timed_search`（L31）、`safe_url`（L40）、`make_snippet`（L49）、`home`（L80） |
| `templates/search.html` | 文字輸出、跳脫、連結屬性 |
| `static/style.css` | 固定深色模式（全組定案） |
| `evaluation/run_evaluation.py` | 產生 `judgments.csv`、記錄索引 SHA-256 到 `run_info.json` |
| `evaluation/judging_split.py` | 拆分給組員、合併回 `judgments.csv`（UTF-8 / cp950 讀取） |
| `evaluation/compute_p5.py` | `precision_at_k`（L27）、快照檢查、缺列與重複列檢查 |
| `evaluation/benchmark_query_time.py` | 查詢耗時量測（加分項） |
| `evaluation/queries.csv` | 10 組查詢、資訊需求、相關性規則（待全組確認後凍結） |
| `verify_d.py` | 27 項自我檢查 |
| `search_temp.py`、`build_temp_index.py` | 暫用版，`config.USE_TEMP = False` 時不使用，次要審核 |

---

## 3. 對照規格的需求清單（請逐項確認）

### 規格第 4 節：搜尋與介面
- [ ] 透過倒排索引找出候選文件，再以 TF-IDF 餘弦相似度排序
- [ ] 最多回傳 10 筆、分數 > 0、由高到低
- [ ] 空白查詢、詞彙外查詢不會出錯，並顯示清楚訊息
- [ ] Flask 搜尋框與結果頁；每筆顯示標題、網址、摘要、分數；頁面顯示索引篇數
- [ ] 摘要為純文字，約 50–100 個英文字；文章較短時顯示全文
- [ ] 結果連結只輸出 http/https 網址
- [ ] 在本機執行

### 規格第 6 節：評估
- [ ] 10 組查詢，各有資訊需求與相關性規則
- [ ] 評估檔包含：查詢、名次、文件編號或網址、相關性（1/0）、判斷理由
- [ ] P@5 = 前 5 名中相關的篇數 / 5；回傳不足 5 筆時，缺少的名次視為不相關，分母仍為 5
- [ ] 10 組取算術平均
- [ ] 在固定的索引快照上評估，結果可以重現

### 評分表「Web interface：safe text rendering」
- [ ] 模板沒有使用 `|safe`、`Markup` 或其他關閉跳脫的寫法
- [ ] 查詢字串、標題、內文、網址都經過 Jinja 自動跳脫

### 加分：查詢耗時
- [ ] 計時範圍清楚：只包含 `search()`，不含載入索引、產生摘要與頁面渲染

---

## 4. 請特別檢查的風險點

1. **串接正確性（`config.py`）**
   C 的 `search(query, top_k)` 不接收 index 參數，而是在 import 時從 `c_module/` 讀取自己的索引。D 用 `INDEX_PATH = Path(_c.index_path)` 確保兩邊讀同一份檔案。請確認不會出現 D 顯示的文件和 C 排序的文件來自不同索引的情況。

2. **`verify_d.py` 的檢查是否真的獨立**
   排名檢查用 `brute_force()`（L78）：直接對索引中**所有文件**的 `tfidf_scores` 算餘弦相似度，不經倒排索引，當作標準答案。另有一項檢查從原文重算權重，驗證 B 的公式。請判斷這兩項是否足以抓出 C 的排序錯誤，有沒有漏洞，例如同分時的排序。

3. **摘要（`make_snippet`）**
   取查詢詞第一次出現位置前 15 個字開始的 60 個字。請檢查邊界情況：文章不到 60 字、命中字在開頭或結尾、沒有命中、只用 IDF > 0 的查詢詞標示。另請確認每一段都由 Jinja 跳脫後才輸出。

4. **評估流程的資料完整性**
   - `judging_split.py merge`：組員可能用 Excel 存成 cp950、改動欄位順序、刪除某列、修改 doc_id，或在 relevant 填入 1/0 以外的值
   - `compute_p5.py`：比對 `run_info.json` 的 `returned_per_query` 檢查缺列，並檢查重複的 (query_id, rank)
   - `run_evaluation.py`：判讀表已有標記時拒絕覆蓋，加 `--overwrite` 才會先備份再覆寫
   - 請確認沒有任何路徑會讓 P@5 被默默算錯

5. **安全性**
   - `app.run(host="127.0.0.1", debug=False)`
   - 查詢長度限制為 200 字元
   - 搜尋程式拋出例外時顯示友善訊息，不回傳 500（`home` 內的 try/except）
   - 外部連結使用 `target="_blank" rel="noopener noreferrer"`

6. **版控與隱私**
   - `.gitignore` 必須排除含 A 爬蟲全文的檔案：`data/`、`c_module/index_osaka.json`、`evaluation/judging/`
   - 請用 `git ls-files` 確認沒有誤加入這些檔案，也沒有組員姓名、帳號、密碼或本機絕對路徑

---

## 5. 已知且接受的行為（請不要列為錯誤）

| 現象 | 原因 |
|---|---|
| `Kōshōji` 被拆成 k、sh、ji，結果出現 K11、Katsuo-ji 等不相關頁面 | B 的拆字規則只取 a–z（全組約定），作為「效果不好的查詢」分析案例 |
| `<b>test</b> castle` 的結果中 `b` 被當成查詢詞，標示到 B1F、1-B | 同上，單一字母也會成為詞 |
| `sumiyoshi taisha shrine` 前幾名是其他神社 | 資料中沒有住吉大社的專頁（sumiyoshi 的 DF = 3），作為分析案例 |
| `kaiyukan aquarium` 只回傳 7 筆 | 只有 7 篇分數 > 0，符合規格 |
| 部分結果是網站的搜尋頁（例如 Osaka Metro NiNE 的 Search Articles） | A 的資料品質問題，不在 D 範圍 |
| C 的介面和原本約定不同 | 刻意在 D 的 `config.py` 轉換，C 的程式碼不修改 |
| C 和 D 各自載入一次索引（約 5.5 MB JSON） | 為了不改 C 的程式碼，記憶體用量可以接受 |
| `queries.csv` 尚未經全組確認 | 流程上的待辦事項，不是程式問題 |
| 使用 Flask 開發伺服器 | 規格只要求在本機 Demo |

---

## 6. 執行與驗證（請在複製的資料夾中進行）

環境：Windows、Python 3.10、Flask 3.1.3。索引檔 `c_module/index_osaka.json` 不在 git 中，但本機資料夾裡有。

```bash
py -m pip install -r requirements.txt
py verify_d.py                              # 預期：共 27 項，通過 27
py app.py                                   # http://127.0.0.1:5000
py evaluation/benchmark_query_time.py       # 預期平均約 0.3–0.5 ms
```

評估流程：`judgments.csv` 目前尚未填寫，`compute_p5.py` 預期會報「還沒填完整」並以代碼 1 結束，這是正確行為。要測試合併與計算，請在副本中填寫 `evaluation/judging/判讀_*.csv` 後執行：

```bash
py evaluation/judging_split.py merge
py evaluation/compute_p5.py
```

### 已完成的人工測試（2026-11-09，使用者在瀏覽器實測）

| # | 測試 | 結果 |
|---|---|---|
| 1 | 首頁、深色模式、顯示 323 篇 | 通過 |
| 2–4 | `osaka castle`：10 筆，欄位齊全，標示查詢詞，顯示耗時 | 通過 |
| 5 | 標題連結到原網址並在新分頁開啟 | 已以程式檢查 HTML 屬性 |
| 6–7 | `takoyaki dotonbori`、`kaiyukan aquarium` | 通過 |
| 8 | 大寫 `CASTLE` 與小寫結果相同 | 通過 |
| 9–12 | 空白、只有空格、`2026`、`zzqxv` 顯示提示訊息 | 通過 |
| 13 | `<b>test</b>` 照原樣顯示，沒有變成粗體 | 通過 |
| 14–15 | `Kōshōji`、`sumiyoshi taisha shrine` | 符合第 5 節的預期 |
| 16 | 視窗縮窄後的版面 | 尚待確認 |
| 17 | 終端機只有 200/304 紀錄；`/favicon.ico` 的 404 已處理，Chrome DevTools 的 404 是瀏覽器自動請求，無害 | 通過 |

---

## 7. 不在本次範圍

- A 的爬蟲程式與資料品質、B 的索引程式、C 模組的內部寫法（除了串接介面）
- Word 書面報告與 Canva 簡報
- 10 組查詢的人工相關性判讀內容

---

## 審核紀錄

### 第 1 次（2026-11-09，Codex）
結論：修正後可以交件。處理結果如下：

| 嚴重度 | 發現 | 處理 |
|---|---|---|
| 高 | 50 筆判讀尚未填寫，沒有 P@5 結果 | 流程待辦，等組員判讀（非程式問題） |
| 中 | `compute_p5.py` 沒檢查名次是否為 1..N，改名次會默默算錯 | ✅ 已修正（commit a27567c）：檢查每組名次與文件編號，和 `run_info.json` 的 `expected_rows` 比對 |
| 中 | 索引雜湊不符只警告；沒有檢查 `queries_sha256` | ✅ 已修正（commit a27567c）：兩者不符都停止 |
| 低 | B 的 README 串接介面描述過時 | 不修改（屬於 B 的檔案），已記錄 |
| 建議 | 有些電腦的 `py` 不能用 | ✅ README 補充 `python` 的寫法（commit a27567c） |

修正後在副本中驗證 9 種情況：改名次、改文件編號、刪列、重複名次、名次非數字、未知查詢編號、索引變動、查詢檔變動都會停止；正常填寫可以正確計算。

---

## 8. 請用以下格式回報

每個發現一筆，依嚴重程度排序：

```
[嚴重度] 高 / 中 / 低 / 建議
[位置]   檔案:行號
[問題]   一句話說明
[重現]   具體輸入或步驟 → 實際結果 vs 預期結果
[建議]   修正方式（只寫說明，不要直接改檔案）
```

最後請附上：
1. 第 3 節的清單，每一項標註「符合 / 不符合 / 無法確認」
2. 有沒有任何情況會讓 Demo 當場失敗（程式當掉、出現錯誤頁、結果空白）
3. 整體結論：可以交件 / 修正後可以交件 / 有重大問題
