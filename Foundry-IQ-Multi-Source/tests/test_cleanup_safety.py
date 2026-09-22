import json
from types import SimpleNamespace

import pytest
from azure.core import MatchConditions
from foundry_iq_multi_source.config import Settings
from foundry_iq_multi_source.sample import MultiSourceSample


class FakeIndexClient:
    def __init__(self) -> None:
        self.deleted: list[tuple[str, str, MatchConditions]] = []
        self.resources = {
            ("index", "sample-owned-index"): SimpleNamespace(
                name="sample-owned-index",
                e_tag='"owned-etag"',
            )
        }

    def get_index(self, name: str):
        return self.resources[("index", name)]

    def get_knowledge_source(self, name: str):
        return self.resources[("knowledge_source", name)]

    def get_knowledge_base(self, name: str):
        return self.resources[("knowledge_base", name)]

    def delete_index(self, resource, *, match_condition) -> None:
        self.deleted.append(("index", resource.name, match_condition))

    def delete_knowledge_source(self, resource, *, match_condition) -> None:
        self.deleted.append(
            ("knowledge_source", resource.name, match_condition)
        )

    def delete_knowledge_base(self, resource, *, match_condition) -> None:
        self.deleted.append(
            ("knowledge_base", resource.name, match_condition)
        )


def settings() -> Settings:
    return Settings(
        search_endpoint="https://example.search.windows.net",
        azure_openai_endpoint="https://example.openai.azure.com",
        azure_openai_deployment="gpt-5-mini",
        azure_openai_model="gpt-5-mini",
    )


def sample_with_fake_client(
    config: Settings,
    client: FakeIndexClient,
) -> MultiSourceSample:
    sample = object.__new__(MultiSourceSample)
    sample.settings = config
    sample.credential = object()
    sample._created_resources = []
    sample.index_client = client
    return sample


def test_cleanup_without_manifest_deletes_nothing(
    monkeypatch,
    tmp_path,
) -> None:
    manifest_path = tmp_path / "resources.json"
    monkeypatch.setattr(
        Settings,
        "manifest_path",
        property(lambda self: manifest_path),
    )
    client = FakeIndexClient()

    sample_with_fake_client(settings(), client).cleanup()

    assert client.deleted == []


def test_cleanup_deletes_only_manifest_owned_resources(
    monkeypatch,
    tmp_path,
) -> None:
    manifest_path = tmp_path / "resources.json"
    monkeypatch.setattr(
        Settings,
        "manifest_path",
        property(lambda self: manifest_path),
    )
    config = settings()
    manifest_path.write_text(
        json.dumps(
            {
                "search_endpoint": config.search_endpoint,
                "resources": [
                    {
                        "kind": "index",
                        "name": "sample-owned-index",
                        "e_tag": "\"owned-etag\"",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    client = FakeIndexClient()

    sample_with_fake_client(config, client).cleanup()

    assert client.deleted == [
        (
            "index",
            "sample-owned-index",
            MatchConditions.IfNotModified,
        )
    ]
    assert not manifest_path.exists()


def test_cleanup_refuses_replacement_with_different_etag(
    monkeypatch,
    tmp_path,
) -> None:
    manifest_path = tmp_path / "resources.json"
    monkeypatch.setattr(
        Settings,
        "manifest_path",
        property(lambda self: manifest_path),
    )
    config = settings()
    manifest_path.write_text(
        json.dumps(
            {
                "search_endpoint": config.search_endpoint,
                "resources": [
                    {
                        "kind": "index",
                        "name": "sample-owned-index",
                        "e_tag": "\"original-etag\"",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    client = FakeIndexClient()

    with pytest.raises(RuntimeError, match="refused to delete"):
        sample_with_fake_client(config, client).cleanup()

    assert client.deleted == []
    assert manifest_path.exists()
