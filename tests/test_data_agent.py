from src.agents import data_agent


def test_sections_keep_heading_and_content(tmp_path, monkeypatch):
    document = tmp_path / "company.md"
    document.write_text(
        "## Name\n\nTestfirma\n\n## Mission\n\nSoftware entwickeln.",
        encoding="utf-8",
    )
    monkeypatch.setattr(data_agent, "ALLOWED_FILE", document)

    result = data_agent.read_project_document()

    assert result["status"] == "success"
    assert result["chunk_count"] == 2
    assert result["chunks"][0]["text"] == "## Name\n\nTestfirma"
    assert result["chunks"][1]["text"] == (
        "## Mission\n\nSoftware entwickeln."
    )


def test_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        data_agent, "ALLOWED_FILE", tmp_path / "missing.md"
    )

    result = data_agent.read_project_document()

    assert result["status"] == "error"
    assert result["chunks"] == []


def test_empty_file(tmp_path, monkeypatch):
    document = tmp_path / "empty.md"
    document.write_text("   \n\n", encoding="utf-8")
    monkeypatch.setattr(data_agent, "ALLOWED_FILE", document)

    result = data_agent.read_project_document()

    assert result["status"] == "error"
    assert result["chunks"] == []