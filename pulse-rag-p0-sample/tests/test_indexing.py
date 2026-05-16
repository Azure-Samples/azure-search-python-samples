from pathlib import Path
import sys
import unittest


API_PATH = Path(__file__).resolve().parents[1] / "api"
if str(API_PATH) not in sys.path:
    sys.path.insert(0, str(API_PATH))

from indexing import SearchIndexingError, SearchIngestionService  # noqa: E402


class FakeIndexingResult:
    def __init__(self, succeeded: bool, error_message: str | None = None):
        self.succeeded = succeeded
        self.error_message = error_message


class FakeSearchClient:
    def __init__(self, merge_results, stale_result_ids):
        self.merge_results = merge_results
        self.stale_result_ids = stale_result_ids
        self.calls: list[tuple[str, object]] = []

    def merge_or_upload_documents(self, documents):
        self.calls.append(("merge_or_upload", [doc["id"] for doc in documents]))
        return self.merge_results

    def search(self, **kwargs):
        self.calls.append(("search", kwargs["filter"]))
        return [{"id": result_id} for result_id in self.stale_result_ids]

    def delete_documents(self, documents):
        self.calls.append(("delete", [doc["id"] for doc in documents]))


def build_source_document(version: str = "v1") -> dict[str, object]:
    return {
        "id": "device-7",
        "deviceId": "device-7",
        "name": "Lobby display",
        "room": "Lobby",
        "status": "online",
        "description": "A signage display that reports building notices and events.",
        "version": version,
    }


class SearchIngestionServiceTests(unittest.TestCase):
    def test_deletes_stale_chunks_only_after_successful_upsert(self) -> None:
        client = FakeSearchClient(
            merge_results=[FakeIndexingResult(True)],
            stale_result_ids=["legacy-1"],
        )
        service = SearchIngestionService(client)

        outcome = service.sync_source_document(build_source_document())

        self.assertEqual(outcome["sourceId"], "device-7")
        self.assertEqual([call[0] for call in client.calls], ["merge_or_upload", "search", "delete"])

    def test_skips_delete_when_upsert_reports_failure(self) -> None:
        client = FakeSearchClient(
            merge_results=[FakeIndexingResult(False, "boom")],
            stale_result_ids=["legacy-1"],
        )
        service = SearchIngestionService(client)

        with self.assertRaises(SearchIndexingError):
            service.sync_source_document(build_source_document(version="v2"))

        self.assertEqual([call[0] for call in client.calls], ["merge_or_upload"])


if __name__ == "__main__":
    unittest.main()