import json
import unittest

from migrate_inplace import MAX_INDEX_BYTES, build_inplace_schema, key_field, split_index_batches


def minimal_schema():
    return {
        "name": "products-v1",
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True,
             "sortable": True, "filterable": True, "retrievable": True},
            {"name": "content", "type": "Edm.String", "searchable": True, "retrievable": True},
            {"name": "vector", "type": "Collection(Edm.Single)", "searchable": True,
             "retrievable": True, "dimensions": 1024, "vectorSearchProfile": "profile-v1"},
        ],
        "vectorSearch": {
            "algorithms": [{"name": "hnsw-default", "kind": "hnsw"}],
            "profiles": [{"name": "profile-v1", "algorithm": "hnsw-default", "vectorizer": "vectorizer-v1"}],
            "vectorizers": [{
                "name": "vectorizer-v1",
                "kind": "customWebApi",
                "customWebApiParameters": {
                    "uri": "https://old-func.azurewebsites.net/api/embed/fast/query",
                    "httpMethod": "POST",
                    "authResourceId": "api://11111111-1111-1111-1111-111111111111"
                }
            }]
        }
    }


class InPlaceSchemaTests(unittest.TestCase):
    def test_rejects_normalized_key(self):
        schema = minimal_schema()
        schema["fields"][0]["normalizer"] = "lowercase"
        with self.assertRaisesRegex(ValueError, "non-normalized"):
            key_field(schema)

    def test_adds_new_vector_field_and_vectorizer(self):
        updated, changed = build_inplace_schema(
            minimal_schema(), "id", "content", "vector", "vector_v2", 1024, "fast",
            "https://unit-func.azurewebsites.net", "api://00000000-0000-0000-0000-000000000000", "migrationMarker")
        self.assertTrue(changed)
        fields = {field["name"]: field for field in updated["fields"]}
        self.assertIn("vector_v2", fields)
        self.assertEqual(1024, fields["vector_v2"]["dimensions"])
        self.assertTrue(fields["vector_v2"]["retrievable"])
        self.assertTrue(fields["vector_v2"]["stored"])
        names = [item["name"] for item in updated["vectorSearch"]["vectorizers"]]
        self.assertIn("migration-vector_v2-vectorizer", names)

    def test_accepts_existing_new_vector_field(self):
        schema = minimal_schema()
        schema["fields"].append({
            "name": "vector_v2",
            "type": "Collection(Edm.Single)",
            "searchable": True,
            "retrievable": True,
            "stored": True,
            "dimensions": 1024,
            "vectorSearchProfile": "migration-vector_v2-profile"
        })
        schema["vectorSearch"]["profiles"].append({
            "name": "migration-vector_v2-profile",
            "algorithm": "hnsw-default",
            "vectorizer": "migration-vector_v2-vectorizer"
        })
        schema["vectorSearch"]["vectorizers"].append({
            "name": "migration-vector_v2-vectorizer",
            "kind": "customWebApi",
            "customWebApiParameters": {
                "uri": "https://unit-func.azurewebsites.net/api/embed/fast/query",
                "httpMethod": "POST",
                "authResourceId": "api://00000000-0000-0000-0000-000000000000"
            }
        })
        schema["fields"].append({
            "name": "migrationMarker",
            "type": "Edm.String",
            "filterable": True,
            "retrievable": True
        })
        updated, changed = build_inplace_schema(
            schema, "id", "content", "vector", "vector_v2", 1024, "fast",
            "https://unit-func.azurewebsites.net", "api://00000000-0000-0000-0000-000000000000", "migrationMarker")
        self.assertFalse(changed)
        self.assertEqual("vector_v2", next(field["name"] for field in updated["fields"] if field["name"] == "vector_v2"))

    def test_adds_marker_field(self):
        updated, changed = build_inplace_schema(
            minimal_schema(), "id", "content", "vector", "vector_v2", 1024, "fast",
            "https://unit-func.azurewebsites.net", "api://00000000-0000-0000-0000-000000000000",
            marker_field="migrationVectorVersion")
        self.assertTrue(changed)
        fields = {field["name"]: field for field in updated["fields"]}
        self.assertEqual("Edm.String", fields["migrationVectorVersion"]["type"])
        self.assertTrue(fields["migrationVectorVersion"]["filterable"])

    def test_rejects_equal_source_and_destination(self):
        with self.assertRaisesRegex(ValueError, "must differ"):
            build_inplace_schema(
                minimal_schema(), "id", "content", "vector", "vector", 1024, "fast",
                "https://unit-func.azurewebsites.net", "api://00000000-0000-0000-0000-000000000000", "migrationMarker")

    def test_rejects_marker_alias(self):
        with self.assertRaisesRegex(ValueError, "must not match"):
            build_inplace_schema(
                minimal_schema(), "id", "content", "vector", "vector_v2", 1024, "fast",
                "https://unit-func.azurewebsites.net", "api://00000000-0000-0000-0000-000000000000", "id")

    def test_rejects_existing_vectorizer_mismatch(self):
        schema = minimal_schema()
        schema["fields"].append({
            "name": "vector_v2",
            "type": "Collection(Edm.Single)",
            "searchable": True,
            "retrievable": True,
            "stored": True,
            "dimensions": 1024,
            "vectorSearchProfile": "profile-v1"
        })
        schema["fields"].append({
            "name": "migrationMarker",
            "type": "Edm.String",
            "filterable": True
        })
        with self.assertRaisesRegex(ValueError, "does not match"):
            build_inplace_schema(
                schema, "id", "content", "vector", "vector_v2", 1024, "fast",
                "https://unit-func.azurewebsites.net", "api://00000000-0000-0000-0000-000000000000", "migrationMarker")

    def test_splits_index_batches(self):
        big_vector = [0.1234567] * 3072
        actions = [
            {"@search.action": "merge", "id": f"doc-{i}", "vector_v2": big_vector, "migrationMarker": "m1"}
            for i in range(250)
        ]
        batches = split_index_batches(actions)
        self.assertGreaterEqual(len(batches), 1)
        for batch in batches:
            size = len(json.dumps({"value": batch}, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            self.assertLessEqual(size, MAX_INDEX_BYTES)
        self.assertEqual(sum(len(batch) for batch in batches), len(actions))


if __name__ == "__main__":
    unittest.main()
