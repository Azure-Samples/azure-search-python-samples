"""Frozen-source, all-fields Azure AI Search backup/restore and embedding migration.

Run `python migrate.py --help`. Uses Azure CLI/managed identity, never API keys.
The source must remain frozen until backup completes. Non-retrievable fields
cannot be recovered through Search; this sample refuses incomplete backups.
"""
import argparse
import copy
import hashlib
import json
import re
import struct
from pathlib import Path
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "function"))
from identity_auth import credential as identity_credential, function_audience
from embedding_engine import (EmbeddingEngine, ProviderError, TransientProviderError,
                              validate_vector)

API_VERSION = "2025-09-01"
MAX_BYTES = 16 * 1024 * 1024
MAX_ATTEMPTS = 6


def encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value):
    return hashlib.sha256(value).hexdigest()


def file_digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def pause(attempt, retry_after=None):
    delay = min(2 ** attempt, 30)
    if retry_after:
        try:
            delay = max(float(retry_after), 0)
        except ValueError:
            try:
                delay = max((parsedate_to_datetime(retry_after)
                             - datetime.now(timezone.utc)).total_seconds(), 0)
            except (ValueError, TypeError):
                pass
    time.sleep(delay)


def https_url(value, label):
    parsed = urlparse(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment):
        raise ValueError(f"{label} must be HTTPS without credentials/query/fragment")
    return value.rstrip("/")


class Search:
    def __init__(self, endpoint, credential=None, session=None):
        self.endpoint = https_url(endpoint, "Search endpoint")
        self.credential = credential
        if session is None:
            import requests
            session = requests.Session()
        self.session = session

    def request(self, method, path, body=None, allow_missing=False, create=False):
        headers = {"Content-Type": "application/json"}
        if self.credential is None:
            self.credential = identity_credential()
        headers["Authorization"] = "Bearer " + self.credential.get_token(
            "https://search.azure.com/.default").token
        if create:
            headers["If-None-Match"] = "*"
        for attempt in range(MAX_ATTEMPTS):
            response = self.session.request(
                method, f"{self.endpoint}/{path}?api-version={API_VERSION}",
                data=encoded(body) if body is not None else None,
                headers=headers, timeout=(10, 120))
            if response.status_code == 404 and allow_missing:
                return None
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if attempt + 1 < MAX_ATTEMPTS:
                    pause(attempt, response.headers.get("Retry-After"))
                    continue
            if not 200 <= response.status_code < 300:
                # Provider bodies can contain credentials/configuration; do not dump them.
                raise RuntimeError(f"Search {method} {path}: HTTP {response.status_code}")
            return response.json() if response.content else {}
        raise RuntimeError("Search retry limit reached")

    def index(self, name):
        return "indexes/" + quote(name, safe="")


def schema_key(schema):
    keys = [field for field in schema["fields"] if field.get("key")]
    if len(keys) != 1:
        raise ValueError("Exactly one key is required")
    key = keys[0]
    if key["type"] != "Edm.String" or not key.get("sortable") or not key.get("filterable"):
        raise ValueError("Backup requires a sortable, filterable Edm.String key for keyset paging")
    return key["name"]


def guard_retrievable(fields, prefix=""):
    for field in fields:
        name = prefix + field["name"]
        if field.get("retrievable") is False:
            raise ValueError(f"Cannot back up non-retrievable field: {name}")
        if field.get("stored") is False:
            raise ValueError(f"Cannot back up unstored vector field: {name}")
        guard_retrievable(field.get("fields", []), name + "/")


def guard_no_secrets(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in ("apikey", "connectionstring", "httpheaders", "authorization",
                               "x-functions-key", "api-key") and child:
                raise ValueError(f"Schema contains {key}; refuse to persist credentials")
            if isinstance(child, str) and ("?code=" in child.lower() or "&code=" in child.lower()):
                raise ValueError("Schema contains a function key URL; refuse to persist credentials")
            guard_no_secrets(child)
    elif isinstance(value, list):
        for child in value:
            guard_no_secrets(child)


def sanitize_schema(schema):
    """Preserve identity-only schemas; refuse credential-bearing schemas."""
    sanitized = copy.deepcopy(schema)
    for name in list(sanitized):
        if name.startswith("@odata."):
            del sanitized[name]
    guard_no_secrets(sanitized)
    return sanitized, []


def canonical_schema(schema):
    """Normalize only observed Search defaults and custom API duration spelling."""
    result = copy.deepcopy(schema)
    for name in list(result):
        if name.startswith("@odata."):
            del result[name]
    search = result.get("vectorSearch") or {}
    for algorithm in search.get("algorithms") or []:
        if algorithm.get("kind") == "hnsw":
            algorithm.setdefault("exhaustiveKnnParameters", None)
    for profile in search.get("profiles") or []:
        profile.setdefault("compression", None)
    for vectorizer in search.get("vectorizers") or []:
        if vectorizer.get("kind") != "customWebApi":
            continue
        vectorizer.setdefault("azureOpenAIParameters", None)
        parameters = vectorizer.get("customWebApiParameters")
        if not isinstance(parameters, dict):
            continue
        parameters.setdefault("authIdentity", None)
        parameters.setdefault("httpHeaders", {})
        parameters.setdefault("httpMethod", "POST")
        duration = parameters.get("timeout")
        if not isinstance(duration, str):
            continue
        match = re.fullmatch(
            r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?",
            duration)
        if (match is None or not any(match.groups())
                or ("T" in duration and not any(match.groups()[1:]))):
            continue
        seconds = sum((Decimal(value or 0) * multiplier for value, multiplier in
                       zip(match.groups(), (86400, 3600, 60, 1))), Decimal(0))
        parameters["timeout"] = "PT" + format(seconds.normalize(), "f") + "S"
    return result


def rehydrate_schema(schema, bindings, require_credentials=True):
    if bindings:
        raise ValueError("Secret credential bindings are unsupported; use managed identities")
    result = copy.deepcopy(schema)
    guard_no_secrets(result)
    return result


def backup(client, source, directory, source_frozen):
    if not source_frozen:
        raise ValueError("Freeze ingestion, updates, deletes, indexers and schema changes; pass --source-frozen")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        raise ValueError("Backup directory must be empty")
    schema = client.request("GET", client.index(source))
    guard_retrievable(schema["fields"])
    schema, bindings = sanitize_schema(schema)
    key = schema_key(schema)
    schema.pop("@odata.etag", None)
    (directory / "schema.json").write_bytes(encoded(schema))
    before = client.request("GET", client.index(source) + "/docs/$count")
    count, previous = 0, None
    with (directory / "documents.jsonl").open("wb") as docs, (
            directory / "keys.jsonl").open("wb") as keys:
        while True:
            request = {"search": "*", "top": 1000, "orderby": key + " asc",
                       "select": "*", "count": True}
            if previous is not None:
                request["filter"] = key + " gt '" + previous.replace("'", "''") + "'"
            page = client.request("POST", client.index(source) + "/docs/search", request)
            rows = page.get("value")
            if not isinstance(rows, list):
                raise ValueError("Search returned no document array")
            if not rows:
                break
            for row in rows:
                document = {k: v for k, v in row.items() if not k.startswith("@search.")}
                current = document.get(key)
                if not isinstance(current, str) or not current:
                    raise ValueError("Invalid document key")
                if previous is not None and current <= previous:
                    raise ValueError("Non-increasing keys; keyset paging cannot safely continue")
                checksum = digest(encoded(document))
                docs.write(encoded({"key": current, "sha256": checksum, "document": document}) + b"\n")
                keys.write(encoded({"key": current, "sha256": checksum}) + b"\n")
                previous = current
                count += 1
    after = client.request("GET", client.index(source) + "/docs/$count")
    final_schema, final_bindings = sanitize_schema(client.request("GET", client.index(source)))
    if (before != after or count != before or final_schema != schema
            or final_bindings != bindings):
        raise ValueError("Source changed or backup is incomplete; backup NOT finalized")
    manifest = {"format": 1, "sourceEndpoint": client.endpoint, "sourceIndex": source,
                "sourceFrozenAcknowledged": True, "keyField": key, "count": count,
                "credentialBindings": bindings,
                "createdUtc": datetime.now(timezone.utc).isoformat(),
                "files": {name: file_digest(directory / name)
                          for name in ("schema.json", "documents.jsonl", "keys.jsonl")}}
    (directory / "manifest.json").write_bytes(encoded(manifest))
    print(f"Verified backup: {count} documents at {directory}")


def read_backup(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_bytes())
    if manifest.get("format") != 1 or manifest.get("sourceFrozenAcknowledged") is not True:
        raise ValueError("Unsupported or unfinalized backup")
    for name in ("schema.json", "documents.jsonl", "keys.jsonl"):
        if file_digest(directory / name) != manifest["files"].get(name):
            raise ValueError(f"Backup file checksum mismatch: {name}")
    schema = json.loads((directory / "schema.json").read_bytes())
    guard_no_secrets(schema)
    # Refuse legacy secret bindings before contacting Search.
    rehydrate_schema(schema, manifest.get("credentialBindings", []), require_credentials=False)
    guard_retrievable(schema["fields"])
    if schema_key(schema) != manifest["keyField"]:
        raise ValueError("Manifest key does not match schema")
    count, previous = 0, None
    with (directory / "documents.jsonl").open("rb") as docs, (
            directory / "keys.jsonl").open("rb") as keys:
        for line in docs:
            row = json.loads(line)
            key_row = json.loads(keys.readline())
            key = row["key"]
            if (not isinstance(key, str) or (previous is not None and key <= previous)
                    or row["document"].get(manifest["keyField"]) != key
                    or row["sha256"] != digest(encoded(row["document"]))
                    or key_row != {"key": key, "sha256": row["sha256"]}):
                raise ValueError("Document/key integrity check failed")
            previous = key
            count += 1
        if keys.readline() or count != manifest["count"]:
            raise ValueError("Backup document/key count mismatch")
    return schema, manifest


def documents(directory):
    with (Path(directory) / "documents.jsonl").open("rb") as stream:
        for line in stream:
            yield json.loads(line)["document"]


def batches(rows):
    batch = []
    empty_size = len(encoded({"value": []}))
    size = empty_size
    for document in rows:
        if "@search.action" in document:
            raise ValueError("Document contains reserved upload action")
        action = {"@search.action": "upload", **document}
        action_size = len(encoded(action))
        if empty_size + action_size > MAX_BYTES:
            raise ValueError("A single document exceeds Search's 16 MiB request limit")
        additional = action_size + (1 if batch else 0)
        if len(batch) == 1000 or size + additional > MAX_BYTES:
            yield batch
            batch = []
            size = empty_size
            additional = action_size
        batch.append(action)
        size += additional
    if batch:
        yield batch


def upload(client, target, rows, key):
    count = 0
    for batch in batches(rows):
        pending = batch
        for attempt in range(MAX_ATTEMPTS):
            result = client.request("POST", client.index(target) + "/docs/index", {"value": pending})
            statuses = result.get("value", [])
            by_key = {item["key"]: item for item in statuses}
            if len(statuses) != len(pending) or len(by_key) != len(pending):
                raise RuntimeError("Search returned incomplete/duplicate upload results")
            retry = []
            for doc in pending:
                status = by_key.get(doc[key])
                if status is None:
                    raise RuntimeError("Search did not return an upload result for every key")
                if status.get("status") is True:
                    count += 1
                elif status.get("statusCode") == 429 or 500 <= status.get("statusCode", 0) <= 599:
                    retry.append(doc)
                else:
                    raise RuntimeError(f"Upload failed for key {doc[key]!r}: "
                                       f"status {status.get('statusCode')}; {status.get('errorMessage')}")
            if not retry:
                break
            if attempt + 1 == MAX_ATTEMPTS:
                raise RuntimeError(f"Upload retry limit reached for {len(retry)} documents")
            pending = retry
            pause(attempt)
    return count


class Embedder:
    def __init__(self, model, dimensions, function_base=None, direct=False, role="document",
                 function_auth_resource_id=None, managed_identity=False, credential=None):
        self.model, self.dimensions = model, dimensions
        if role not in ("document", "query"):
            raise ValueError("Unsupported embedding role")
        self.role = role
        self.function_base = https_url(function_base, "Function base") if function_base else None
        self.engine = None
        self.credential = credential or identity_credential(managed_identity, cli=True)
        self.function_auth_resource_id = function_auth_resource_id
        if direct:
            self.engine = EmbeddingEngine(credential=self.credential)
        else:
            if not self.function_base:
                raise ValueError("--function-base is required unless --direct is used")
            self.function_auth_resource_id = function_audience(function_auth_resource_id)
            import requests
            self.session = requests.Session()

    def __call__(self, text):
        for attempt in range(MAX_ATTEMPTS):
            if self.engine:
                try:
                    return self.engine.embed(self.model, self.role, text, self.dimensions)
                except TransientProviderError as exc:
                    if attempt + 1 == MAX_ATTEMPTS:
                        raise
                    pause(attempt, exc.retry_after)
                    continue
            response = self.session.post(
                f"{self.function_base}/api/embed/{self.model}/{self.role}",
                headers={"Authorization": "Bearer " + self.credential.get_token(
                    self.function_auth_resource_id + "/.default").token},
                json={"values": [{"recordId": "0", "data": {"text": text}}]}, timeout=(10, 240))
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if attempt + 1 < MAX_ATTEMPTS:
                    pause(attempt, response.headers.get("Retry-After"))
                    continue
            if not 200 <= response.status_code < 300:
                raise ProviderError(f"Embedding function HTTP {response.status_code}")
            try:
                values = response.json()["values"]
                if len(values) != 1 or values[0]["recordId"] != "0" or values[0].get("errors"):
                    raise ProviderError("Embedding function returned record errors or mismatched records")
                return validate_vector(values[0]["data"]["vector"], self.dimensions)
            except (ValueError, KeyError, TypeError, IndexError) as exc:
                raise ProviderError("Malformed embedding function response") from exc
        raise ProviderError("Embedding retry limit reached")


def migration_schema(schema, target, field_name, model, dimensions, function_base,
                     function_auth_resource_id):
    schema = copy.deepcopy(schema)
    schema["name"] = target
    fields = [field for field in schema["fields"] if field["name"] == field_name]
    if len(fields) != 1 or fields[0]["type"] != "Collection(Edm.Single)":
        raise ValueError("--vector-field must name a top-level Collection(Edm.Single) field")
    field = fields[0]
    vector_search = schema.get("vectorSearch", {})
    profiles = vector_search.get("profiles", [])
    original = next((p for p in profiles if p["name"] == field.get("vectorSearchProfile")), None)
    if original is None:
        raise ValueError("Selected vector field has no valid vector search profile")
    name = "migration-" + model
    if any(p["name"] == name for p in profiles) or any(
            v["name"] == name for v in vector_search.get("vectorizers", [])):
        raise ValueError("Migration profile/vectorizer name already exists")
    profile = copy.deepcopy(original)
    # A previous compression may be incompatible with changed dimensions/model.
    profile.pop("compression", None)
    profile.update(name=name, vectorizer=name)
    profiles.append(profile)
    field.update(dimensions=dimensions, vectorSearchProfile=name)
    base = https_url(function_base, "Function base")
    audience = function_audience(function_auth_resource_id)
    vector_search.setdefault("vectorizers", []).append({
        "name": name, "kind": "customWebApi", "customWebApiParameters": {
            "uri": f"{base}/api/embed/{model}/query", "httpMethod": "POST",
            "timeout": "PT1M", "authResourceId": audience}})
    return schema


def float32_vector(vector, dimensions=None):
    validate_vector(vector, dimensions)
    try:
        return [struct.unpack("<f", struct.pack("<f", value))[0] for value in vector]
    except (OverflowError, struct.error) as exc:
        raise ProviderError("Vector value cannot be represented as Edm.Single") from exc


def migration_backup(directory, schema, source_directory, source_manifest, rows, details):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        raise ValueError("Migration output directory must be empty")
    schema, _ = sanitize_schema(schema)
    (directory / "schema.json").write_bytes(encoded(schema))
    count = 0
    key_field = source_manifest["keyField"]
    with (directory / "documents.jsonl").open("wb") as docs, (
            directory / "keys.jsonl").open("wb") as keys:
        for document in rows:
            checksum = digest(encoded(document))
            entry = {"key": document[key_field], "sha256": checksum}
            docs.write(encoded({**entry, "document": document}) + b"\n")
            keys.write(encoded(entry) + b"\n")
            count += 1
    if count != source_manifest["count"]:
        raise ValueError("Migration output count differs from source backup")
    manifest = {
        "format": 1, "sourceEndpoint": source_manifest["sourceEndpoint"],
        "sourceIndex": schema["name"], "sourceFrozenAcknowledged": True,
        "keyField": key_field, "count": count, "credentialBindings": [],
        "createdUtc": datetime.now(timezone.utc).isoformat(),
        "migration": {**details, "sourceBackup": str(Path(source_directory).resolve()),
                      "sourceManifestSha256": file_digest(Path(source_directory) / "manifest.json"),
                      "vectorEncoding": "IEEE754-binary32"},
        "files": {name: file_digest(directory / name)
                  for name in ("schema.json", "documents.jsonl", "keys.jsonl")}}
    (directory / "manifest.json").write_bytes(encoded(manifest))
    read_backup(directory)
    return manifest


def restore(client, target, directory, migration=None, migration_dir=None):
    schema, manifest = read_backup(directory)
    schema = rehydrate_schema(schema, manifest.get("credentialBindings", []))
    rows = documents(directory)
    schema["name"] = target
    if client.request("GET", client.index(target), allow_missing=True) is not None:
        raise ValueError("Destination index already exists; refusing to overwrite it")
    if migration:
        embedder, text_field, vector_field, model, dimensions, function_base, audience = migration
        function_audience(audience)
        if text_field == vector_field:
            raise ValueError("Text and vector fields must be different")
        for document in documents(directory):
            text = document.get(text_field)
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"Every document must contain nonempty string field {text_field!r}")
        first = next(documents(directory), None)
        if first is None:
            raise ValueError("Cannot verify requested model/dimensions with an empty backup")
        # Verify against the actual provider before creating anything; never guess dimensions.
        first_vector = float32_vector(embedder(first.get(text_field)), dimensions)
        # Both Function and direct document callers must prove the deployed query
        # route before any destination mutation.
        query = Embedder(model, dimensions, function_base, role="query",
                         function_auth_resource_id=audience,
                         credential=getattr(embedder, "credential", None))
        validate_vector(query(first.get(text_field)), dimensions)
        schema = migration_schema(schema, target, vector_field, model, dimensions,
                                  function_base, audience)

        def transformed():
            for index, row in enumerate(rows):
                result = copy.deepcopy(row)
                result[vector_field] = first_vector if index == 0 else float32_vector(
                    embedder(row.get(text_field)), dimensions)
                if {k: v for k, v in result.items() if k != vector_field} != {
                        k: v for k, v in row.items() if k != vector_field}:
                    raise AssertionError("Non-vector fields changed")
                yield result
        if migration_dir is None:
            source = Path(directory)
            migration_dir = source.with_name(
                source.name + "-migration-" + digest(target.encode("utf-8"))[:12])
        migration_dir = Path(migration_dir)
        if migration_dir.resolve() == Path(directory).resolve():
            raise ValueError("Migration output must differ from the source backup")
        # Finalize all generated documents locally before creating the destination.
        manifest = migration_backup(migration_dir, schema, directory, manifest, transformed(), {
            "model": model, "dimensions": dimensions, "textField": text_field,
            "vectorField": vector_field, "functionBase": function_base,
            "functionAuthResourceId": audience})
        directory = migration_dir
        output = documents(directory)
        print(f"Verified migration backup: {directory}")
    else:
        output = rows
    client.request("PUT", client.index(target), schema, create=True)
    actual_schema = client.request("GET", client.index(target))
    if canonical_schema(actual_schema) != canonical_schema(schema):
        raise RuntimeError("Destination schema differs from the requested backup/migration schema")
    count = upload(client, target, output, manifest["keyField"])
    if count != manifest["count"]:
        raise RuntimeError("Uploaded count does not match backup")
    # Search indexing is eventually consistent; verify actual keys/documents below.
    verify_destination(client, target, directory, manifest,
                       migration[2] if migration else None,
                       migration[4] if migration else None)
    print(f"Verified destination {target}: {count} documents; "
          + ("only selected vectors changed" if migration else "all fields identical"))


def verify_destination(client, target, directory, manifest, changed_vector=None, dimensions=None):
    key = manifest["keyField"]
    schema = json.loads((Path(directory) / "schema.json").read_bytes())
    vector_fields = [field["name"] for field in schema["fields"]
                     if field["type"] == "Collection(Edm.Single)"]
    for expected in documents(directory):
        actual = None
        for attempt in range(MAX_ATTEMPTS):
            actual = client.request("GET", client.index(target) + "/docs/"
                                    + quote(expected[key], safe=""), allow_missing=True)
            if actual is not None:
                break
            pause(attempt)
        if actual is None:
            raise RuntimeError(f"Destination is missing key {expected[key]!r}")
        actual = {k: v for k, v in actual.items() if not k.startswith("@odata.")}
        if changed_vector:
            validate_vector(actual.get(changed_vector), dimensions)
        for name in vector_fields:
            for document in (actual, expected):
                if document.get(name) is not None:
                    document[name] = float32_vector(document[name]) if document[name] else []
        if actual != expected:
            raise RuntimeError(f"Destination field mismatch at key {expected[key]!r}")
    for attempt in range(MAX_ATTEMPTS):
        count = client.request("GET", client.index(target) + "/docs/$count")
        if count == manifest["count"]:
            return
        pause(attempt)
    raise RuntimeError("Destination count mismatch")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--search-endpoint", required=True)
    parser.add_argument("--managed-identity", action="store_true",
                        help="Use managed identity; AZURE_CLIENT_ID selects a user-assigned identity")
    sub = parser.add_subparsers(dest="command", required=True)
    save = sub.add_parser("backup")
    save.add_argument("--source", required=True)
    save.add_argument("--backup-dir", required=True)
    save.add_argument("--source-frozen", action="store_true")
    load = sub.add_parser("restore")
    load.add_argument("--target", required=True)
    load.add_argument("--backup-dir", required=True)
    migrate = sub.add_parser("reembed")
    migrate.add_argument("--target", required=True)
    migrate.add_argument("--backup-dir", required=True)
    migrate.add_argument("--text-field", required=True)
    migrate.add_argument("--vector-field", required=True)
    migrate.add_argument("--model", choices=("baseline", "fast", "pro"), required=True)
    migrate.add_argument("--dimensions", type=int, required=True,
                         help="Must match actual provider response; no assumed dimension list")
    migrate.add_argument("--function-base", required=True,
                         help="https://<function-app>.azurewebsites.net (no /api suffix)")
    migrate.add_argument("--function-auth-resource-id", required=True,
                         help="Entra EasyAuth audience: api://<application-client-id>")
    migrate.add_argument("--direct", action="store_true",
                         help="Use shared Cohere client for documents; query vectorizer still uses Function")
    migrate.add_argument("--migration-dir",
                         help="Empty local directory retaining a checksummed generated-document backup; "
                              "defaults to a sibling of --backup-dir")
    args = parser.parse_args()
    credential = identity_credential(args.managed_identity)
    client = Search(args.search_endpoint, credential=credential)
    if args.command == "backup":
        backup(client, args.source, args.backup_dir, args.source_frozen)
    elif args.command == "restore":
        restore(client, args.target, args.backup_dir)
    else:
        if args.dimensions < 1:
            parser.error("--dimensions must be positive")
        embedder = Embedder(args.model, args.dimensions, args.function_base, args.direct,
                            function_auth_resource_id=args.function_auth_resource_id,
                            managed_identity=args.managed_identity)
        restore(client, args.target, args.backup_dir, (
            embedder, args.text_field, args.vector_field, args.model,
            args.dimensions, args.function_base, args.function_auth_resource_id),
            migration_dir=args.migration_dir)


if __name__ == "__main__":
    main()
