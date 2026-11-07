"""In-place additive embedding migration for Azure AI Search.

Adds a new vector field/profile/vectorizer to an existing index, backfills vectors
from an existing text field, and verifies before/after behavior.
"""
import argparse
import copy
import json
import struct
import sys
import time
from pathlib import Path
from urllib.parse import quote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "function"))
from identity_auth import credential as identity_credential, function_audience
from embedding_engine import ProviderError, validate_vector

API_VERSION = "2025-09-01"
MAX_ATTEMPTS = 6
MAX_INDEX_BYTES = 16 * 1024 * 1024


def pause(attempt):
    time.sleep(min(2 ** attempt, 30))


def https_root(value, label):
    parsed = urlparse(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment):
        raise ValueError(f"{label} must be HTTPS without credentials/query/fragment")
    return value.rstrip("/")


def escape_odata(value):
    return value.replace("'", "''")


def float32_vector(vector, dimensions):
    validate_vector(vector, dimensions)
    try:
        return [struct.unpack("<f", struct.pack("<f", value))[0] for value in vector]
    except (OverflowError, struct.error) as exc:
        raise ProviderError("Vector value cannot be represented as Edm.Single") from exc


class Search:
    def __init__(self, endpoint, credential=None, session=None):
        self.endpoint = https_root(endpoint, "Search endpoint")
        self.credential = credential
        if session is None:
            import requests
            session = requests.Session()
        self.session = session

    def request(self, method, path, body=None):
        if self.credential is None:
            self.credential = identity_credential(cli=True)
        headers = {
            "Authorization": "Bearer " + self.credential.get_token("https://search.azure.com/.default").token,
            "Content-Type": "application/json"
        }
        for attempt in range(MAX_ATTEMPTS):
            response = self.session.request(
                method,
                f"{self.endpoint}/{path}?api-version={API_VERSION}",
                headers=headers,
                json=body,
                timeout=(10, 120))
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if attempt + 1 < MAX_ATTEMPTS:
                    pause(attempt)
                    continue
            if not 200 <= response.status_code < 300:
                raise RuntimeError(f"Search {method} {path}: HTTP {response.status_code}")
            return response.json() if response.content else {}
        raise RuntimeError("Search retry limit reached")

    @staticmethod
    def index(name):
        return "indexes/" + quote(name, safe="")


class Embedder:
    def __init__(self, model, dimensions, function_base, function_auth_resource_id, credential=None, session=None):
        self.model = model
        self.dimensions = dimensions
        self.function_base = https_root(function_base, "Function base")
        self.function_auth_resource_id = function_audience(function_auth_resource_id)
        self.credential = credential or identity_credential(cli=True)
        if session is None:
            import requests
            session = requests.Session()
        self.session = session

    def embed_batch(self, items):
        payload = {"values": [{"recordId": key, "data": {"text": text}} for key, text in items]}
        for attempt in range(MAX_ATTEMPTS):
            response = self.session.post(
                f"{self.function_base}/api/embed/{self.model}/document",
                headers={"Authorization": "Bearer " + self.credential.get_token(
                    self.function_auth_resource_id + "/.default").token},
                json=payload,
                timeout=(10, 240))
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if attempt + 1 < MAX_ATTEMPTS:
                    pause(attempt)
                    continue
            if not 200 <= response.status_code < 300:
                raise RuntimeError(f"Embedding function HTTP {response.status_code}")
            data = response.json()
            values = data.get("values")
            if not isinstance(values, list):
                raise RuntimeError("Embedding response is missing values")
            result = {}
            for value in values:
                key = value.get("recordId")
                errors = value.get("errors") or []
                vector = ((value.get("data") or {}).get("vector"))
                if not isinstance(key, str) or errors:
                    raise RuntimeError("Embedding response returned malformed records")
                result[key] = float32_vector(vector, self.dimensions)
            if len(result) != len(items):
                raise RuntimeError("Embedding response record count mismatch")
            return result
        raise RuntimeError("Embedding retry limit reached")


def key_field(schema):
    keys = [field for field in schema["fields"] if field.get("key")]
    if len(keys) != 1:
        raise ValueError("Exactly one key field is required")
    key = keys[0]
    if (key.get("type") != "Edm.String" or key.get("sortable") is not True
            or key.get("filterable") is not True or key.get("normalizer")):
        raise ValueError("In-place migration requires a non-normalized, sortable, filterable Edm.String key")
    return key["name"]


def build_inplace_schema(schema, key_name, text_field, source_vector_field, new_vector_field, dimensions,
                         model, function_base, function_auth_resource_id, marker_field):
    if source_vector_field == new_vector_field:
        raise ValueError("--new-vector-field must differ from --source-vector-field")
    if marker_field in {key_name, text_field, source_vector_field, new_vector_field}:
        raise ValueError("--marker-field must not match key/text/source-vector/new-vector fields")

    updated = copy.deepcopy(schema)
    fields = updated.get("fields") or []
    source = next((field for field in fields if field.get("name") == source_vector_field), None)
    if source is None or source.get("type") != "Collection(Edm.Single)":
        raise ValueError("--source-vector-field must name a top-level Collection(Edm.Single) field")
    existing = next((field for field in fields if field.get("name") == new_vector_field), None)

    expected_uri = f"{https_root(function_base, 'Function base')}/api/embed/{model}/query"
    expected_audience = function_audience(function_auth_resource_id)
    changed = False

    if existing is None:
        new_field = copy.deepcopy(source)
        new_field["name"] = new_vector_field
        new_field["dimensions"] = dimensions
        new_field["retrievable"] = True
        new_field["stored"] = True
        profile_name = f"migration-{new_vector_field}-profile"
        vectorizer_name = f"migration-{new_vector_field}-vectorizer"
        new_field["vectorSearchProfile"] = profile_name
        fields.append(new_field)
        vector_search = updated.get("vectorSearch") or {}
        profiles = vector_search.get("profiles") or []
        original_profile = next((profile for profile in profiles
                                 if profile.get("name") == source.get("vectorSearchProfile")), None)
        if original_profile is None:
            raise ValueError("Source vector field has no valid vector search profile")
        profile = copy.deepcopy(original_profile)
        profile.pop("compression", None)
        profile.update(name=profile_name, vectorizer=vectorizer_name)
        if any(item.get("name") == profile_name for item in profiles):
            raise ValueError("Migration vector profile already exists")
        profiles.append(profile)
        vector_search["profiles"] = profiles
        vectorizers = vector_search.get("vectorizers") or []
        if any(item.get("name") == vectorizer_name for item in vectorizers):
            raise ValueError("Migration vectorizer already exists")
        vectorizers.append({
            "name": vectorizer_name,
            "kind": "customWebApi",
            "customWebApiParameters": {
                "uri": expected_uri,
                "httpMethod": "POST",
                "timeout": "PT1M",
                "authResourceId": expected_audience
            }
        })
        vector_search["vectorizers"] = vectorizers
        updated["vectorSearch"] = vector_search
        changed = True
    else:
        if existing.get("type") != "Collection(Edm.Single)":
            raise ValueError("--new-vector-field must be Collection(Edm.Single) when it already exists")
        if existing.get("dimensions") != dimensions:
            raise ValueError("--new-vector-field dimensions do not match --dimensions")
        if existing.get("retrievable") is False:
            raise ValueError("--new-vector-field must be retrievable")
        if existing.get("stored") is False:
            raise ValueError("--new-vector-field must be stored")

        vector_search = updated.get("vectorSearch") or {}
        profiles = vector_search.get("profiles") or []
        vectorizers = vector_search.get("vectorizers") or []
        profile_name = existing.get("vectorSearchProfile")
        profile = next((item for item in profiles if item.get("name") == profile_name), None)
        if not profile:
            raise ValueError("Existing --new-vector-field profile was not found")
        vectorizer_name = profile.get("vectorizer")
        vectorizer = next((item for item in vectorizers if item.get("name") == vectorizer_name), None)
        if not vectorizer:
            raise ValueError("Existing --new-vector-field vectorizer was not found")
        if vectorizer.get("kind") != "customWebApi":
            raise ValueError("Existing --new-vector-field vectorizer must be customWebApi")
        params = vectorizer.get("customWebApiParameters") or {}
        actual_uri = (params.get("uri") or "").rstrip("/")
        actual_audience = (params.get("authResourceId") or "").rstrip("/")
        if actual_uri.lower() != expected_uri.lower() or actual_audience != expected_audience:
            raise ValueError("Existing --new-vector-field vectorizer does not match --function-base/--model/--function-auth-resource-id")

    marker = next((field for field in fields if field.get("name") == marker_field), None)
    if marker is None:
        fields.append({
            "name": marker_field,
            "type": "Edm.String",
            "searchable": False,
            "retrievable": True,
            "filterable": True,
            "sortable": False,
            "facetable": False
        })
        changed = True
    elif marker.get("type") != "Edm.String" or marker.get("filterable") is not True:
        raise ValueError("--marker-field must resolve to a filterable Edm.String field")
    return updated, changed


def count_pending(client, index, marker_field, marker_value):
    filter_expr = f"{marker_field} ne '{escape_odata(marker_value)}'"
    page = client.request("POST", Search.index(index) + "/docs/search",
                          {"search": "*", "count": True, "top": 0, "filter": filter_expr})
    return page.get("@odata.count")


def split_index_batches(actions):
    batches = []
    current = []
    for action in actions:
        candidate = current + [action]
        size = len(json.dumps({"value": candidate}, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        if size <= MAX_INDEX_BYTES:
            current = candidate
            continue
        if not current:
            raise RuntimeError("A single update action exceeds Search's 16 MiB indexing request limit")
        batches.append(current)
        current = [action]
        single_size = len(json.dumps({"value": current}, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        if single_size > MAX_INDEX_BYTES:
            raise RuntimeError("A single update action exceeds Search's 16 MiB indexing request limit")
    if current:
        batches.append(current)
    return batches


def upload_updates(client, index, key_name, actions):
    for batch in split_index_batches(actions):
        response = client.request("POST", Search.index(index) + "/docs/index", {"value": batch})
        statuses = response.get("value") or []
        if len(statuses) != len(batch):
            raise RuntimeError("Search returned incomplete indexing statuses")
        by_key = {item.get("key"): item for item in statuses}
        for action in batch:
            key_value = action.get(key_name)
            status = by_key.get(key_value)
            if status is None or status.get("status") is not True:
                code = status.get("statusCode") if status else "missing"
                message = status.get("errorMessage") if status else "missing status"
                raise RuntimeError(f"Index update failed for key {action}: status {code}; {message}")


def backfill(client, index, key, text_field, vector_field, embedder,
             marker_field, marker_value, batch_size=4):
    pending = count_pending(client, index, marker_field, marker_value)
    processed = 0
    last = None
    while True:
        filters = [f"{marker_field} ne '{escape_odata(marker_value)}'"]
        if last is not None:
            filters.append(f"{key} gt '{escape_odata(last)}'")
        request = {"search": "*", "orderby": key + " asc", "top": 500,
                   "select": f"{key},{text_field}",
                   "filter": " and ".join(filters)}
        page = client.request("POST", Search.index(index) + "/docs/search", request).get("value") or []
        if not page:
            break
        last = page[-1][key]
        rows = []
        for row in page:
            text = row.get(text_field)
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"Every document must contain nonempty string field {text_field!r}")
            rows.append((row[key], text))
        vectors = {}
        for offset in range(0, len(rows), batch_size):
            vectors.update(embedder.embed_batch(rows[offset: offset + batch_size]))
        actions = []
        for doc_key, _ in rows:
            actions.append({
                "@search.action": "merge",
                key: doc_key,
                vector_field: vectors[doc_key],
                marker_field: marker_value
            })
        upload_updates(client, index, key, actions)
        processed += len(rows)
        print(f"Backfilled {processed}/{pending} pending documents into '{vector_field}'.")


def verify(client, index, key, vector_field, dimensions):
    count = client.request("GET", Search.index(index) + "/docs/$count")
    seen, last = 0, None
    while True:
        request = {"search": "*", "orderby": key + " asc", "top": 500,
                   "select": key}
        if last is not None:
            request["filter"] = f"{key} gt '{escape_odata(last)}'"
        page = client.request("POST", Search.index(index) + "/docs/search", request).get("value") or []
        if not page:
            break
        last = page[-1][key]
        for row in page:
            document = client.request("GET", Search.index(index) + "/docs/" + quote(row[key], safe=""))
            validate_vector(document.get(vector_field), dimensions)
        seen += len(page)
    if seen != count:
        raise RuntimeError("Destination verification did not read all documents")


def sample_keys(client, index, key, field):
    rows = client.request("POST", Search.index(index) + "/docs/search",
                          {"search": "*", "top": 3, "select": f"{key},{field}"}).get("value") or []
    return [row.get(key) for row in rows]


def query_probe(client, index, key, vector_field, text):
    payload = {"top": 3, "select": key, "vectorQueries": [
        {"kind": "text", "text": text, "fields": vector_field, "k": 3}
    ]}
    rows = client.request("POST", Search.index(index) + "/docs/search", payload).get("value") or []
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--search-endpoint", required=True)
    parser.add_argument("--index", required=True)
    parser.add_argument("--text-field", required=True)
    parser.add_argument("--source-vector-field", required=True)
    parser.add_argument("--new-vector-field", required=True)
    parser.add_argument("--model", choices=("fast", "pro"), required=True)
    parser.add_argument("--dimensions", type=int, required=True)
    parser.add_argument("--function-base", required=True)
    parser.add_argument("--function-auth-resource-id", required=True)
    parser.add_argument("--managed-identity", action="store_true")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--query-probe-text", default="How do I recover my account?")
    parser.add_argument("--marker-field", required=True,
                        help="Filterable Edm.String marker field used to track pending backfill records")
    parser.add_argument("--marker-value", help="Marker value; defaults to <new-vector-field>:<model>:<dimensions>")
    parser.add_argument("--source-writes-frozen", action="store_true",
                        help="Required acknowledgement that source index writes/deletes are paused during backfill")
    args = parser.parse_args()

    if args.dimensions < 1:
        parser.error("--dimensions must be positive")
    if args.batch_size < 1 or args.batch_size > 16:
        parser.error("--batch-size must be in [1, 16]")
    if not args.source_writes_frozen:
        parser.error("--source-writes-frozen is required to prevent concurrent-write backfill corruption")

    marker_value = args.marker_value or f"{args.new_vector_field}:{args.model}:{args.dimensions}"
    credential = identity_credential(args.managed_identity, cli=True)
    client = Search(args.search_endpoint, credential=credential)
    embedder = Embedder(args.model, args.dimensions, args.function_base,
                        args.function_auth_resource_id, credential=credential)

    schema = client.request("GET", Search.index(args.index))
    key = key_field(schema)
    updated, changed = build_inplace_schema(
        schema, key, args.text_field, args.source_vector_field, args.new_vector_field, args.dimensions,
        args.model, args.function_base, args.function_auth_resource_id, args.marker_field)

    before_count = client.request("GET", Search.index(args.index) + "/docs/$count")
    print(f"Before: index={args.index}, count={before_count}, sampleKeys={sample_keys(client, args.index, key, args.text_field)}")

    if changed:
        client.request("PUT", Search.index(args.index), updated)
    pending_before = count_pending(client, args.index, args.marker_field, marker_value)
    print(f"Backfill target set: pendingBackfill={pending_before} for field '{args.new_vector_field}'.")

    backfill(client, args.index, key, args.text_field, args.new_vector_field, embedder,
             marker_field=args.marker_field, marker_value=marker_value, batch_size=args.batch_size)
    verify(client, args.index, key, args.new_vector_field, args.dimensions)
    pending_after = count_pending(client, args.index, args.marker_field, marker_value)
    after_count = client.request("GET", Search.index(args.index) + "/docs/$count")
    print(f"After: index={args.index}, count={after_count}, pendingBackfill={pending_after}, sampleKeysWithNewField={sample_keys(client, args.index, key, args.new_vector_field)}")
    hits = query_probe(client, args.index, key, args.new_vector_field, args.query_probe_text)
    print(f"After query probe: returned={hits} results using field '{args.new_vector_field}'.")


if __name__ == "__main__":
    main()
