from __future__ import annotations

import pytest

from services.structured_data.sql import QueryPlan, SqlError, build_sql, execute, import_table, read_table

CSV = b"id,equipo,estado soporte,licencias\n1,EQ-1,Vigente,2\n2,EQ-2,Fuera de soporte,3\n3,EQ-3,fuera de soporte,1\n"


@pytest.fixture
def db(tmp_path):
    p = tmp_path / "t.db"
    h, b = read_table("csv", CSV)
    import_table(p, "inv", h, b)
    import_table(p, "secret_table", ["x"], [["top-secret"]])
    return p, h


def run(db, plan):
    p, cols = db
    sql, params = build_sql(plan, cols)
    return execute(p, sql, params, {"inv"})


def test_count_and_group(db):
    assert run(db, QueryPlan(table="inv", operation="count", filters=[{"column": "estado_soporte", "op": "=", "value": "Fuera de soporte"}]))[0]["n"] == 2
    assert run(db, QueryPlan(table="inv", operation="sum", column="licencias"))[0]["value"] == 6
    g = run(db, QueryPlan(table="inv", operation="group_count", column="estado_soporte"))
    assert sum(r["n"] for r in g) == 3


def test_unknown_column_and_injection_in_values(db):
    with pytest.raises(SqlError):
        run(db, QueryPlan(table="inv", operation="count", filters=[{"column": "x; DROP TABLE inv", "op": "=", "value": 1}]))
    # values are bound parameters: injection text is just a string
    assert run(db, QueryPlan(table="inv", operation="count", filters=[{"column": "equipo", "op": "=", "value": "' OR 1=1 --"}]))[0]["n"] == 0


@pytest.mark.parametrize("sql", [
    "DELETE FROM inv", "DROP TABLE inv", "INSERT INTO inv VALUES (9,'x','y',1)", "ATTACH DATABASE 'x.db' AS x",
    "PRAGMA table_info(inv)", "SELECT * FROM secret_table", "SELECT load_extension('evil')", "SELECT 1; DELETE FROM inv",
    "SELECT * FROM sqlite_master",
])
def test_authorizer_blocks_everything_but_allowed_reads(db, sql):
    with pytest.raises(SqlError):
        execute(db[0], sql, [], {"inv"})


def test_plan_rejects_extra_fields_and_big_limits():
    with pytest.raises(ValueError):
        QueryPlan(table="inv", operation="count", raw_sql="DELETE")
    with pytest.raises(ValueError):
        QueryPlan(table="inv", operation="list", limit=10_000)
