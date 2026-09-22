import json
from pathlib import Path


SAMPLE_ROOT = Path(__file__).resolve().parents[1]


def test_sample_data_is_public_and_fictional() -> None:
    documents = json.loads(
        (SAMPLE_ROOT / "data" / "release-brief.json").read_text(
            encoding="utf-8"
        )
    )

    assert len(documents) >= 2
    assert all(document["title"].startswith("Contoso") for document in documents)
    ignored = (SAMPLE_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in ignored
