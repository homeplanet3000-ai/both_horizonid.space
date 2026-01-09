import pytest

from database import db


@pytest.fixture()
def temp_db(tmp_path, monkeypatch) -> str:
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", str(db_path))
    return str(db_path)
