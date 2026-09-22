from __future__ import annotations

import pytest

from apps.api.db import connect, migrate
from packages.schemas.models import Privacy, Verification
from scripts.make_samples import pdf
from services.ingestion.extract import ExtractionError, detect_kind, extract_pdf
from services.ingestion.pipeline import IngestError, Ingestor, safe_filename
from services.rag.facts import FactIn, add_fact, facts_for


@pytest.fixture
def ing(tmp_path):
    con = connect(tmp_path / "o.db")
    migrate(con)
    return Ingestor(con, tmp_path / "data", tmp_path / "t.db", qdrant=None, embed=None, embed_model="m", embed_dim=8,
                    max_bytes=1024, max_pages=5), con


def test_type_validation():
    with pytest.raises(ExtractionError):
        detect_kind("fake.pdf", b"MZ\x90\x00 not a pdf")
    with pytest.raises(ExtractionError, match="no soportado"):
        detect_kind("libro.epub", b"PK")
    with pytest.raises(ExtractionError):
        detect_kind("x.exe", b"MZ")
    with pytest.raises(ExtractionError):
        detect_kind("x.txt", b"abc\x00def")
    assert detect_kind("a.MD", b"# hola") == "markdown"


def test_pdf_without_text_requires_ocr(tmp_path):
    p = tmp_path / "empty.pdf"
    pdf(p, [[""]])
    with pytest.raises(ExtractionError, match="OCR"):
        extract_pdf(p.read_bytes(), 10)


def test_size_limit_dedupe_versioning_and_paths(ing):
    i, con = ing
    with pytest.raises(IngestError, match="límite"):
        i.register("big.txt", b"x" * 2000, Privacy.PRIVATE, "admin")
    a, new = i.register("../../etc/notas.txt", b"hola", Privacy.PRIVATE, "admin")
    assert new and a["original_name"] == "notas.txt" and ".." not in a["stored_path"]
    b, new2 = i.register("otra.txt", b"hola", Privacy.PRIVATE, "admin")
    assert not new2 and b["document_id"] == a["document_id"]           # identical copy
    c, _ = i.register("notas.txt", b"hola v2", Privacy.PRIVATE, "admin")
    assert c["version"] == 2 and c["supersedes"] == a["document_id"]   # new version
    assert safe_filename("C:\\x\\..\\a<b>.md") == "a_b_.md"


def test_verified_conflict_is_surfaced_not_resolved(tmp_path):
    con = connect(tmp_path / "f.db")
    migrate(con)
    base = dict(subject_key="servicio-demo.puerto", privacy=Privacy.INTERNAL, verification=Verification.VERIFIED, verified_by="usuario")
    add_fact(con, FactIn(statement="El servicio demo usa el puerto 8443", source_id="inv-v1", **base), "admin")
    add_fact(con, FactIn(statement="El servicio demo usa el puerto 9443", source_id="inv-v2", **base), "admin")
    r = facts_for(con, "Servicio-Demo.Puerto")
    assert len(r["conflict"]) == 2 and {f["source_id"] for f in r["conflict"]} == {"inv-v1", "inv-v2"}


def test_llm_cannot_grant_verified(tmp_path):
    con = connect(tmp_path / "f.db")
    migrate(con)
    f = FactIn(subject_key="kk", statement="algo", verification=Verification.VERIFIED, source_id="s", verified_by="x")
    with pytest.raises(ValueError):
        add_fact(con, f, "admin", via_llm=True)
    with pytest.raises(ValueError):
        add_fact(con, FactIn(subject_key="kk", statement="algo", verification=Verification.VERIFIED, source_id="s"), "admin")
