"""D 的共用設定：介面（app.py）與評估程式都從這裡取得索引和搜尋函式。

目前使用正式版：
  - 索引：B 的 index_osaka.json
  - 搜尋：C 的 search_c_module.py
兩者都放在 c_module/（C 的程式會從自己的資料夾讀索引，D 也讀同一份）。

C 的函式是 search(query, top_k)，回傳 [{"doc_id", "title", "url", "similarity"}, ...]，
這裡轉成 D 使用的格式 [(doc_id, score), ...]。C 的程式碼本身沒有修改。

要改回暫用版（測試用）：把 USE_TEMP 改成 True，並先執行 py build_temp_index.py。
"""
import json
import re
import sys
from pathlib import Path

# Windows 終端機預設 cp950，標題中的 ō、・ 等字元印出時改成 ? 而不是讓程式中斷
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

FOLDER = Path(__file__).resolve().parent
USE_TEMP = False

if USE_TEMP:
    from search_temp import search, tokenize  # noqa: F401
    INDEX_PATH = FOLDER / "data" / "index_temp.json"
    SEARCH_SOURCE = "暫用 search_temp.search"
else:
    sys.path.insert(0, str(FOLDER / "c_module"))
    import search_c_module as _c  # noqa: E402

    INDEX_PATH = Path(_c.index_path)  # 和 C 讀同一份索引
    SEARCH_SOURCE = "C 正式版 search_c_module.search"

    def tokenize(text):
        """與 B、C 相同：轉小寫，以連續 a-z 為單字（D 用來標示摘要中的查詢詞）。"""
        return re.findall(r"[a-z]+", text.lower())

    def search(query, index=None, top_k=10):
        """呼叫 C 的搜尋，轉成 [(doc_id, score), ...]。index 參數保留給相容用，C 會用自己載入的索引。"""
        return [(r["doc_id"], r["similarity"]) for r in _c.search(query or "", top_k=top_k)]


def load_index(path=INDEX_PATH):
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)
