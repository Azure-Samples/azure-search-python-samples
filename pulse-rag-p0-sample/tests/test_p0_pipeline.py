from datetime import UTC, datetime
from pathlib import Path
import sys
import unittest


SHARED_CODE_PATH = Path(__file__).resolve().parents[1] / "api" / "shared_code"
if str(SHARED_CODE_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_CODE_PATH))

from p0_pipeline import (  # noqa: E402
    build_merge_or_upload_actions,
    build_search_documents,
    build_stale_chunk_filter,
    split_text,
    stable_chunk_id,
)


class P0PipelineTests(unittest.TestCase):
    def test_stable_chunk_id_uses_source_id_etag_and_index(self) -> None:
        self.assertEqual(
            stable_chunk_id("device-42", '"etag-7"', 3),
            "device-42_etag-7_0003",
        )

    def test_split_text_preserves_overlap(self) -> None:
        text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        chunks = split_text(text, chunk_size=10, chunk_overlap=4)

        self.assertEqual(chunks[0], "ABCDEFGHIJ")
        self.assertEqual(chunks[1], "GHIJKLMNOP")
        self.assertEqual(chunks[2], "MNOPQRSTUV")

    def test_build_search_documents_generates_deterministic_chunk_metadata(self) -> None:
        source_document = {
            "id": "device-123",
            "deviceId": "device-123",
            "deviceName": "Touch Panel",
            "location": "Room 101",
            "description": "A" * 80,
            "capabilities": ["display", "touch"],
            "_etag": '"etag-1"',
            "deviceVersion": "42",
        }

        documents = build_search_documents(
            source_document,
            ingestion_run_id="run-1",
            chunk_size=60,
            chunk_overlap=10,
            ingestion_time=datetime(2026, 5, 16, 8, 0, tzinfo=UTC),
        )

        self.assertGreater(len(documents), 1)
        self.assertEqual(documents[0].id, "device-123_etag-1_0000")
        self.assertEqual(documents[0].source_partition_key, "device-123")
        self.assertEqual(documents[0].device_version, "42")
        self.assertEqual(documents[0].ingestion_run_id, "run-1")

        actions = build_merge_or_upload_actions(documents)
        self.assertTrue(all(action["@search.action"] == "mergeOrUpload" for action in actions))

    def test_build_stale_chunk_filter_escapes_single_quotes(self) -> None:
        stale_filter = build_stale_chunk_filter("device'oops", "run'7")
        self.assertEqual(
            stale_filter,
            "sourceId eq 'device''oops' and ingestionRunId ne 'run''7'",
        )


if __name__ == "__main__":
    unittest.main()