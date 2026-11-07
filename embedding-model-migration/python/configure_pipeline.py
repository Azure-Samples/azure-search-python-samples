"""Opt-in full-document baseline/Fast/Pro blob skill + query vectorizer pipeline.

Does not deploy the Function or change Azure IAM. Run only after deploying the
Function and granting Search's managed identity access to the existing blob
container. All resource names must be new; no existing resources are overwritten.
Requires Entra EasyAuth on the Function with authentication required and HTTP 401
for anonymous requests. Search uses its system-assigned managed identity.
Choose --model baseline --dimensions 1536 for text-embedding-3-small, or choose
fast/pro and a dimension verified by both deployed role endpoints. Full content
is submitted without truncation; split oversized source documents beforehand.
"""
import argparse
import time
from urllib.parse import quote

from migrate import Embedder, Search, https_url
from identity_auth import credential, function_audience


def wait_for_indexer(client, name, seconds):
    deadline = time.monotonic() + seconds
    while True:
        status = client.request("GET", "indexers/" + quote(name, safe="") + "/status")
        result = status.get("lastResult") or {}
        if result.get("status") == "success":
            if result.get("itemsFailed", 0) or result.get("errors"):
                raise RuntimeError("Indexer reported document failures; inspect its status in Azure")
            print(f"Indexer succeeded: {result.get('itemsProcessed', 0)} documents processed")
            return
        if result.get("status") in ("transientFailure", "persistentFailure", "reset"):
            raise RuntimeError("Indexer did not complete successfully; inspect its status in Azure")
        if time.monotonic() >= deadline:
            raise TimeoutError("Indexer completion timeout; inspect its status before querying")
        time.sleep(min(5, max(deadline - time.monotonic(), 0)))


def resources(args):
    if not 1 <= args.degree_of_parallelism <= 10:
        raise ValueError("--degree-of-parallelism must be between 1 and 10")
    base = https_url(args.function_base, "Function base")
    audience = function_audience(args.function_auth_resource_id)
    vectorizer = {"name": "query-embedding", "kind": "customWebApi",
                  "customWebApiParameters": {
                      "uri": f"{base}/api/embed/{args.model}/query",
                      "httpMethod": "POST", "timeout": "PT1M", "authResourceId": audience}}
    index = {
        "name": args.index,
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True, "filterable": True, "sortable": True},
            {"name": "content", "type": "Edm.String", "searchable": True, "retrievable": True},
            {"name": "metadata_storage_name", "type": "Edm.String", "retrievable": True},
            {"name": "metadata_storage_path", "type": "Edm.String", "retrievable": True},
            {"name": "vector", "type": "Collection(Edm.Single)", "searchable": True,
             "retrievable": True, "stored": True, "dimensions": args.dimensions,
             "vectorSearchProfile": "embedding-profile"}],
        "vectorSearch": {
            "algorithms": [{"name": "cosine-hnsw", "kind": "hnsw",
                            "hnswParameters": {"metric": "cosine"}}],
            "profiles": [{"name": "embedding-profile", "algorithm": "cosine-hnsw",
                          "vectorizer": "query-embedding"}],
            "vectorizers": [vectorizer]}}
    datasource = {
        "name": args.datasource, "type": "azureblob",
        "credentials": {"connectionString": f"ResourceId={args.storage_resource_id};"},
        "container": {"name": args.container}}
    skillset = {
        "name": args.skillset,
        "skills": [{
            "@odata.type": "#Microsoft.Skills.Custom.WebApiSkill",
            "name": "document-embedding", "context": "/document",
            "uri": f"{base}/api/embed/{args.model}/document", "httpMethod": "POST",
            "authResourceId": audience, "timeout": "PT230S", "batchSize": 1,
            "degreeOfParallelism": args.degree_of_parallelism,
            "inputs": [{"name": "text", "source": "/document/content"}],
            "outputs": [{"name": "vector", "targetName": "vector"}]}]}
    indexer = {
        "name": args.indexer, "dataSourceName": args.datasource,
        "targetIndexName": args.index, "skillsetName": args.skillset,
        "parameters": {
            "maxFailedItems": 0, "maxFailedItemsPerBatch": 0,
            "configuration": {"dataToExtract": "contentAndMetadata"}},
        "fieldMappings": [
            {"sourceFieldName": "metadata_storage_path", "targetFieldName": "id",
             "mappingFunction": {"name": "base64Encode"}}],
        "outputFieldMappings": [{"sourceFieldName": "/document/vector",
                                  "targetFieldName": "vector"}]}
    return [("indexes", args.index, index), ("datasources", args.datasource, datasource),
            ("skillsets", args.skillset, skillset), ("indexers", args.indexer, indexer)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("search-endpoint", "function-base", "index", "datasource", "skillset",
                "indexer", "storage-resource-id", "container", "function-auth-resource-id"):
        parser.add_argument("--" + arg, required=True)
    parser.add_argument("--model", choices=("baseline", "fast", "pro"), required=True)
    parser.add_argument("--dimensions", type=int, required=True)
    parser.add_argument("--degree-of-parallelism", type=int, default=5,
                        help="Concurrent custom skill requests, 1..10 (default: 5); batch size stays 1")
    parser.add_argument("--managed-identity", action="store_true",
                        help="Use managed identity instead of the local Azure CLI identity")
    parser.add_argument("--probe-text", default="Verify this deployment's embedding dimensions.")
    parser.add_argument("--wait-seconds", type=int, default=0,
                        help="Optionally wait for and validate the indexer's initial run")
    args = parser.parse_args()
    if args.dimensions < 1 or args.wait_seconds < 0:
        parser.error("--dimensions must be positive and --wait-seconds must be nonnegative")
    if not 1 <= args.degree_of_parallelism <= 10:
        parser.error("--degree-of-parallelism must be between 1 and 10")
    if not args.storage_resource_id.startswith("/subscriptions/") or ";" in args.storage_resource_id:
        parser.error("--storage-resource-id must be an Azure storage account resource ID")
    # Both role paths must work with the real model before creating Search resources.
    audience = function_audience(args.function_auth_resource_id)
    for role in ("document", "query"):
        Embedder(args.model, args.dimensions, args.function_base, role=role,
                 function_auth_resource_id=audience,
                 managed_identity=args.managed_identity)(args.probe_text)
    client = Search(args.search_endpoint, credential=credential(args.managed_identity))
    definitions = resources(args)
    for collection, name, _ in definitions:
        path = collection + "/" + quote(name, safe="")
        if client.request("GET", path, allow_missing=True) is not None:
            raise ValueError(f"{collection}/{name} already exists; refusing to overwrite")
    for collection, name, body in definitions:
        client.request("PUT", collection + "/" + quote(name, safe=""), body, create=True)
        print(f"Created {collection}/{name}")
    if args.wait_seconds:
        wait_for_indexer(client, args.indexer, args.wait_seconds)
    else:
        print("Indexer creation triggers its initial run; inspect its status/errors before querying.")


if __name__ == "__main__":
    main()
