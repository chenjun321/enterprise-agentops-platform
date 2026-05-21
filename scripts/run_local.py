import os
import sys
from pathlib import Path

import uvicorn


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    os.environ.setdefault("APP_ENV", "local")
    os.environ.setdefault("DATABASE_URL", "sqlite:///./data/app.db")
    os.environ.setdefault("AUTO_INIT_LOCAL_DB", "true")
    os.environ.setdefault("VECTOR_STORE", "milvus_lite")
    os.environ.setdefault("MILVUS_LITE_URI", "./data/milvus_lite.db")
    os.environ.setdefault("ENABLE_API_DOCS", "true")
    (ROOT / "data").mkdir(exist_ok=True)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
