"""D 的共用設定：介面（app.py）與評估程式都從這裡取得索引和搜尋函式。

整合時只要改這個檔：
  1. B 的正式索引出來後 → 把 INDEX_PATH 改成 B 的索引檔路徑
  2. C 的 search.py 出來後 → 把下面的 import 改成 `from search import search, tokenize`
     （並把 C 的 search.py 放進本資料夾，或加入 sys.path）
"""
import json
import sys
from pathlib import Path

# Windows 終端機預設 cp950，標題中的 ō、・ 等字元印出時改成 ? 而不是讓程式中斷
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

from search_temp import search, tokenize  # noqa: F401  ← C 交件後改這行

FOLDER = Path(__file__).resolve().parent
INDEX_PATH = FOLDER / "data" / "index_temp.json"  # ← B 交件後改這行


def load_index(path=INDEX_PATH):
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)
