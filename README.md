# osaka-travel-search-d

大阪旅遊搜尋引擎的 **D 部分**：Flask 搜尋網頁 + Precision@5 評估。
（A 爬蟲、B 索引、C 搜尋排序由其他組員負責。）

## 執行

需要 Python 3.10、Flask 3.1.3。以下指令用 `py`；如果電腦上的 `py` 不能用（例如 conda 環境），全部改成 `python` 即可，例如 `python app.py`。

`c_module/index_osaka.json`（B 的正式索引）不在 git 中，執行前要先放進 `c_module/`。

```bash
py -m pip install -r requirements.txt
py app.py          # 開啟 http://127.0.0.1:5000
py verify_d.py     # 自我檢查（27 項）
```

## 檔案

| 檔案 | 說明 |
|---|---|
| `app.py`、`templates/`、`static/` | 搜尋網頁（固定深色模式） |
| `config.py` | 接上 C 的搜尋程式，並轉成 D 使用的格式 |
| `c_module/` | C 的 `search_c_module.py` ＋ B 的 `index_osaka.json`（索引不納入版控） |
| `verify_d.py` | 自我檢查 |
| `evaluation/` | 10 組查詢、判讀表、P@5 計算、查詢耗時 |
| `search_temp.py`、`build_temp_index.py` | 暫用版（測試用，`config.py` 設 `USE_TEMP = True`） |

## 評估步驟

```bash
py evaluation/run_evaluation.py           # 1. 產生 judgments.csv
py evaluation/judging_split.py split      # 2. 產生附內文的判讀表 → evaluation/judging/判讀_D.csv
                                          # 3. 填 relevant（1/0）和 reason
py evaluation/judging_split.py merge      # 4. 合併回 judgments.csv
py evaluation/compute_p5.py               # 5. 計算 P@5
py evaluation/benchmark_query_time.py     # 6. 查詢耗時（加分）
```

P@5 = 前 5 名中相關的篇數 / 5；回傳不足 5 筆時，分母仍為 5。
