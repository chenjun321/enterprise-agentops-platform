import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.database import check_database


if __name__ == "__main__":
    check_database()
    print("database reachable")

