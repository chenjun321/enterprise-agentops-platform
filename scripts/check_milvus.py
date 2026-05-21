import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    try:
        from pymilvus import MilvusClient
    except ModuleNotFoundError as exc:
        raise SystemExit("pymilvus is not installed. Run: python -m pip install -r requirements.txt") from exc

    uri = os.getenv("MILVUS_URI", "http://127.0.0.1:19530")
    token = os.getenv("MILVUS_TOKEN") or None
    kwargs = {"uri": uri}
    if token:
        kwargs["token"] = token
    client = MilvusClient(**kwargs)
    print({"ok": True, "uri": uri, "collections": client.list_collections()})


if __name__ == "__main__":
    main()
