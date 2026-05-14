from __future__ import annotations

from app.core.database import SystemSessionLocal
from app.services.prd_v1 import SeedService


def main() -> None:
    db = SystemSessionLocal()
    try:
        result = SeedService(db).init_defaults()
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
