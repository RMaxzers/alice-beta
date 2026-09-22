from apps.api.config import settings
from apps.api.db import connect, migrate

if __name__ == "__main__":
    v = migrate(connect())
    settings().tables_db.parent.mkdir(parents=True, exist_ok=True)
    connect(settings().tables_db).close()
    print(f"ops db schema version {v}")
