import copy
import json
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "function"))
import embedding_engine as engine
from embedding_contract import process_values
import migrate
import configure_pipeline
import identity_auth
import function_app
import retrying_engine
import azure.functions as func


AUDIENCE = "api://11111111-2222-3333-4444-555555555555"
SERVICE_VECTOR_SEARCH = json.loads(
    (Path(__file__).parent / "fixtures" / "service-normalized-vector-search.json").read_text())


def sparse_vector_search():
    search = copy.deepcopy(SERVICE_VECTOR_SEARCH)
    search["algorithms"][0].pop("exhaustiveKnnParameters")
    search["profiles"][0].pop("compression")
    vectorizer = search["vectorizers"][0]
    vectorizer.pop("azureOpenAIParameters")
    parameters = vectorizer["customWebApiParameters"]
    for name in ("authIdentity", "httpHeaders", "httpMethod"):
        parameters.pop(name)
    parameters["timeout"] = "PT230S"
    return search


SCHEMA = {
    "name": "source",
    "fields": [
        {"name": "id", "type": "Edm.String", "key": True, "sortable": True, "filterable": True},
        {"name": "text", "type": "Edm.String"},
        {"name": "metadata", "type": "Edm.ComplexType",
         "fields": [{"name": "label", "type": "Edm.String"}]},
        {"name": "vector", "type": "Collection(Edm.Single)", "dimensions": 2,
         "vectorSearchProfile": "original"}],
    "vectorSearch": {"algorithms": [{"name": "hnsw", "kind": "hnsw"}],
                     "profiles": [{"name": "original", "algorithm": "hnsw"}]}}
DOCS = [{"id": "a'1", "text": "first", "metadata": {"label": "keep"}, "vector": [0.1, 0.2]},
        {"id": "z", "text": "second", "metadata": {"label": "all"}, "vector": [0.3, 0.4]}]


def response(status=200, data=None, headers=None):
    result = Mock(status_code=status, headers=headers or {}, content=b"json")
    result.json.return_value = data
    return result


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {
            "COHERE_ENDPOINT": "https://example.services.ai.azure.com/providers/cohere/v2/embed",
            "FAST_DEPLOYMENT": "Cohere-Embed-V5-Fast",
            "PRO_DEPLOYMENT": "Cohere-Embed-V5-Pro",
            "FAST_DIMENSIONS": "2", "PRO_DIMENSIONS": "2",
            "BASELINE_ENDPOINT": "https://example.openai.azure.com"}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        credential = Mock()
        credential.get_token.return_value.token = "identity-token"
        identity = patch.object(engine, "identity_credential", return_value=credential)
        identity.start()
        self.addCleanup(identity.stop)

    def test_cohere_request_and_roles(self):
        for model in ("fast", "pro"):
            for role in ("document", "query"):
                with self.subTest(model=model, role=role):
                    session = Mock()
                    session.post.return_value = response(data={"embeddings": {"float": [[0.1, 0.2]]}})
                    self.assertEqual(engine.EmbeddingEngine(session=session).embed(
                        model, role, "hello"), [0.1, 0.2])
                    payload = session.post.call_args.kwargs["json"]
                    self.assertEqual(payload, {
                        "model": os.environ[model.upper() + "_DEPLOYMENT"], "texts": ["hello"],
                        "input_type": "search_" + role, "embedding_types": ["float"],
                        "truncate": "NONE",
                        "output_dimension": 2})
                    self.assertEqual(session.post.call_args.kwargs["headers"],
                                     {"Content-Type": "application/json",
                                      "Authorization": "Bearer identity-token"})
                    self.assertEqual(session.post.call_args.args[0],
                                     "https://example.services.ai.azure.com/providers/cohere/v2/embed"
                                     "?api-version=2024-05-01-preview")

    def test_cohere_api_version_override_is_url_encoded(self):
        os.environ["COHERE_API_VERSION"] = "version with spaces&extra=value"
        session = Mock()
        session.post.return_value = response(data={"embeddings": {"float": [[1, 2]]}})
        engine.EmbeddingEngine(session=session).embed("fast", "query", "hello")
        self.assertEqual(session.post.call_args.args[0],
                         "https://example.services.ai.azure.com/providers/cohere/v2/embed"
                         "?api-version=version+with+spaces%26extra%3Dvalue")
        self.assertNotIn("api-key", session.post.call_args.kwargs["headers"])

    def test_cohere_base_endpoint_must_not_include_query(self):
        os.environ["COHERE_ENDPOINT"] += "?api-version=2024-05-01-preview"
        with self.assertRaises(engine.InputError):
            engine.EmbeddingEngine(session=Mock()).embed("fast", "query", "hello")

    def test_cohere_api_version_must_not_be_empty(self):
        os.environ["COHERE_API_VERSION"] = ""
        with self.assertRaises(engine.InputError):
            engine.EmbeddingEngine(session=Mock()).embed("fast", "query", "hello")

    def test_dimension_validated_by_response_not_guessed_list(self):
        session = Mock()
        session.post.return_value = response(data={"embeddings": {"float": [[1] * 7]}})
        self.assertEqual(len(engine.EmbeddingEngine(session=session).embed(
            "fast", "document", "hello", 7)), 7)
        with self.assertRaises(engine.ProviderError):
            engine.EmbeddingEngine(session=session).embed("fast", "document", "hello", 8)

    def test_optional_dimension_is_omitted(self):
        os.environ.pop("FAST_DIMENSIONS")
        session = Mock()
        session.post.return_value = response(data={"embeddings": {"float": [[1, 2, 3]]}})
        engine.EmbeddingEngine(session=session).embed("fast", "query", "hello")
        self.assertNotIn("output_dimension", session.post.call_args.kwargs["json"])

    def test_fast_and_pro_dimensions_are_independent(self):
        os.environ["FAST_DIMENSIONS"] = "1024"
        os.environ["PRO_DIMENSIONS"] = "2048"
        for model, dimensions in (("fast", 1024), ("pro", 2048)):
            for role in ("document", "query"):
                with self.subTest(model=model, role=role):
                    session = Mock()
                    session.post.return_value = response(data={
                        "embeddings": {"float": [[0.1] * dimensions]}})
                    vector = engine.EmbeddingEngine(session=session).embed(model, role, "hello")
                    self.assertEqual(len(vector), dimensions)
                    self.assertEqual(session.post.call_args.kwargs["json"]["output_dimension"],
                                     dimensions)

    def test_baseline_1536(self):
        session = Mock()
        session.post.return_value = response(data={"data": [{"embedding": [0.0] * 1536}]})
        engine.EmbeddingEngine(session=session).embed("baseline", "document", "hello")
        self.assertEqual(session.post.call_args.kwargs["json"]["dimensions"], 1536)
        self.assertIn("/openai/deployments/text-embedding-3-small/embeddings",
                      session.post.call_args.args[0])

    def test_finite_exact_nonempty_vectors(self):
        for value in ([], [True], ["1"], [float("nan")], [float("inf")], {}, None):
            with self.subTest(value=value), self.assertRaises(engine.ProviderError):
                engine.validate_vector(value)
        with self.assertRaises(engine.ProviderError):
            engine.validate_vector([1], 2)

    def test_no_arbitrary_url_route_or_role(self):
        with self.assertRaises(engine.InputError):
            engine.EmbeddingEngine(session=Mock()).embed("https://evil", "document", "hello")
        with self.assertRaises(engine.InputError):
            engine.EmbeddingEngine(session=Mock()).embed("fast", "https://evil", "hello")

    def test_provider_errors_never_fallback(self):
        for status in (400, 401, 403, 429, 500, 503):
            session = Mock()
            session.post.return_value = response(status, {})
            exception = engine.TransientProviderError if status in (429, 500, 503) else engine.ProviderError
            with self.subTest(status=status), self.assertRaises(exception):
                engine.EmbeddingEngine(session=session).embed("fast", "document", "hello")
            self.assertEqual(session.post.call_count, 1)

    def test_managed_identity_scope(self):
        credential, session = Mock(), Mock()
        credential.get_token.return_value.token = "identity-token"
        session.post.return_value = response(data={"embeddings": {"float": [[1, 2]]}})
        engine.EmbeddingEngine(credential, session).embed("fast", "document", "hello")
        credential.get_token.assert_called_once_with("https://cognitiveservices.azure.com/.default")

    def test_transport_timeout_is_transient_502(self):
        import requests
        session = Mock()
        session.post.side_effect = requests.Timeout("timeout")
        with self.assertRaises(engine.TransientProviderError) as caught:
            engine.EmbeddingEngine(session=session).embed("fast", "document", "hello")
        self.assertEqual(caught.exception.status, 502)


class ContractTests(unittest.TestCase):
    def test_exact_skill_and_vectorizer_envelope(self):
        embedder = Mock()
        embedder.embed.return_value = [1, 2]
        body = {"values": [{"recordId": "123", "data": {"text": "hello"}}]}
        self.assertEqual(process_values(body, "fast", "query", embedder),
                         {"values": [{"recordId": "123", "data": {"vector": [1, 2]}}]})
        embedder.embed.assert_called_once_with("fast", "query", "hello")

    def test_record_errors_and_transient_propagation(self):
        embedder = Mock()
        embedder.embed.side_effect = engine.InputError("missing text")
        result = process_values({"values": [{"recordId": "r", "data": {}}]},
                                "fast", "document", embedder)
        self.assertIn("errors", result["values"][0])
        embedder.embed.side_effect = engine.TransientProviderError(429, "3")
        with self.assertRaises(engine.TransientProviderError):
            process_values({"values": [{"recordId": "r", "data": {"text": "x"}}]},
                           "fast", "document", embedder)

    def test_invalid_envelope(self):
        for body in ({}, {"values": []}, {"values": [None]}, {"values": [{"data": {}}]}):
            with self.subTest(body=body), self.assertRaises(engine.InputError):
                process_values(body, "fast", "query", Mock())


class FunctionRetryTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        self.now = 0
        self.sleeps = []
        self.engine = Mock()

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds

    def adapter(self, role="document"):
        return retrying_engine.RetryingEmbeddingEngine(
            self.engine, role, clock=lambda: self.now, sleep=self.sleep)

    def test_retry_after_then_success_does_not_repeat_other_records(self):
        self.engine.embed.side_effect = [engine.TransientProviderError(429, "2"), [1, 2], [3, 4]]
        result = process_values({"values": [
            {"recordId": "a", "data": {"text": "first"}},
            {"recordId": "b", "data": {"text": "second"}}]},
            "fast", "document", self.adapter())
        self.assertEqual(self.sleeps, [2])
        self.assertEqual([call.args[2] for call in self.engine.embed.call_args_list],
                         ["first", "first", "second"])
        self.assertEqual([item["data"]["vector"] for item in result["values"]], [[1, 2], [3, 4]])
        self.assertEqual(self.engine.embed.call_args_list[0].kwargs["timeout"], (10, 60))

    def test_exhausted_attempts_propagate_429(self):
        self.engine.embed.side_effect = engine.TransientProviderError(429, "1")
        with self.assertRaises(engine.TransientProviderError) as caught:
            self.adapter().embed("pro", "document", "hello")
        self.assertEqual(caught.exception.status, 429)
        self.assertEqual(self.engine.embed.call_count, 4)
        self.assertEqual(self.sleeps, [1, 1, 1])

    def test_401_and_5xx_are_not_retried_by_function_adapter(self):
        for error in (engine.ProviderError("HTTP 401"), engine.TransientProviderError(503)):
            self.engine.reset_mock()
            self.engine.embed.side_effect = error
            with self.subTest(error=error), self.assertRaises(type(error)):
                self.adapter().embed("pro", "document", "hello")
            self.assertEqual(self.engine.embed.call_count, 1)
            self.assertEqual(self.sleeps, [])

    def test_retry_after_exceeding_remaining_budget_returns_immediately(self):
        self.engine.embed.side_effect = engine.TransientProviderError(429, "21")
        with self.assertRaises(engine.TransientProviderError):
            self.adapter("query").embed("pro", "query", "hello")
        self.assertEqual(self.engine.embed.call_count, 1)
        self.assertEqual(self.sleeps, [])
        self.assertEqual(self.engine.embed.call_args.kwargs["timeout"], (10, 10))

    def test_request_budget_is_shared_across_records(self):
        def provider(*args, **kwargs):
            self.now += 19
            return [1, 2]
        self.engine.embed.side_effect = provider
        adapter = self.adapter("query")
        self.assertEqual(adapter.embed("fast", "query", "first"), [1, 2])
        self.engine.embed.side_effect = engine.TransientProviderError(429, "2")
        with self.assertRaises(engine.TransientProviderError):
            adapter.embed("fast", "query", "second")
        self.assertEqual(self.engine.embed.call_count, 2)
        self.assertEqual(self.sleeps, [])
        self.assertEqual(self.engine.embed.call_args.kwargs["timeout"], (0.5, 0.5))
        self.now = 21
        with self.assertRaises(engine.TransientProviderError):
            adapter.embed("fast", "query", "third")
        self.assertEqual(self.engine.embed.call_count, 2)

    def test_retry_after_http_date_and_invalid_header(self):
        from datetime import datetime, timezone
        with patch.object(retrying_engine, "datetime") as clock:
            clock.now.return_value = datetime(2026, 11, 6, 12, 0, 0, tzinfo=timezone.utc)
            self.assertEqual(retrying_engine.RetryingEmbeddingEngine.retry_delay(
                "Fri, 06 Nov 2026 12:00:05 GMT", 0), 5)
        for value in (None, "invalid", "nan", "inf"):
            self.assertEqual(retrying_engine.RetryingEmbeddingEngine.retry_delay(value, 2), 4)

    def test_configurable_retry_limits_cannot_expand_hard_budget(self):
        for name, value in (("EMBED_DOCUMENT_RETRY_BUDGET_SECONDS", "121"),
                            ("EMBED_QUERY_RETRY_BUDGET_SECONDS", "21"),
                            ("EMBED_MAX_429_ATTEMPTS", "5"),
                            ("EMBED_MAX_429_ATTEMPTS", "0")):
            with patch.dict(os.environ, {name: value}), self.assertRaises(RuntimeError):
                self.adapter("query" if "QUERY" in name else "document")
        with patch.dict(os.environ, {"EMBED_DOCUMENT_RETRY_BUDGET_SECONDS": "2",
                                    "EMBED_MAX_429_ATTEMPTS": "1"}):
            self.engine.embed.side_effect = engine.TransientProviderError(429, "1")
            with self.assertRaises(engine.TransientProviderError):
                self.adapter().embed("fast", "document", "hello")
            self.assertEqual(self.engine.embed.call_count, 1)

    def test_function_returns_429_and_retry_after_when_budget_cannot_fit(self):
        request = func.HttpRequest(
            method="POST", url="https://example/api/embed/pro/document",
            headers={"X-MS-CLIENT-PRINCIPAL-ID": "search-managed-identity"},
            body=b'{"values":[{"recordId":"r","data":{"text":"hello"}}]}',
            route_params={"model": "pro", "role": "document"})
        with (patch.dict(os.environ, {"REQUIRE_ENTRA_AUTH": "true",
                                     "EMBED_DOCUMENT_RETRY_BUDGET_SECONDS": "1"}),
              patch.object(function_app.engine, "embed",
                           side_effect=engine.TransientProviderError(429, "2")) as provider):
            result = function_app.embed(request)
        self.assertEqual(result.status_code, 429)
        self.assertEqual(result.headers["Retry-After"], "2")
        self.assertEqual(provider.call_count, 1)


class IdentityTests(unittest.TestCase):
    def test_function_audience_rejects_urls_secrets_and_missing_ids(self):
        self.assertEqual(identity_auth.function_audience(AUDIENCE), AUDIENCE)
        for value in (None, "", "https://example", "api://not-a-client-id",
                      AUDIENCE + "/.default", AUDIENCE + "?code=secret"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                identity_auth.function_audience(value)

    def test_credential_selection_has_no_environment_secret_fallback(self):
        with (patch.dict(os.environ, {}, clear=True),
                patch("azure.identity.AzureCliCredential") as cli,
                patch("azure.identity.DefaultAzureCredential") as default,
                patch("azure.identity.ManagedIdentityCredential") as managed):
            self.assertIs(identity_auth.credential(cli=True).credential, cli.return_value)
            self.assertIs(identity_auth.credential().credential, default.return_value)
            default.assert_called_once_with(exclude_environment_credential=True,
                                            exclude_workload_identity_credential=True)
            self.assertIs(identity_auth.credential(True).credential, managed.return_value)
            with patch.dict(os.environ, {"AZURE_CLIENT_ID": "assigned-id"}):
                identity_auth.credential(cli=True)
                managed.assert_called_with(client_id="assigned-id")
            with patch.dict(os.environ, {"IDENTITY_ENDPOINT": "http://platform-identity"}):
                identity_auth.credential()
                managed.assert_called_with()

    def test_token_cache_refreshes_five_minutes_before_expiry(self):
        from azure.core.credentials import AccessToken
        now = [1000]
        credential = Mock()
        first, refreshed = AccessToken("first", 2000), AccessToken("refreshed", 4000)
        credential.get_token.side_effect = [first, refreshed]
        cached = identity_auth.CachedTokenCredential(credential, clock=lambda: now[0])
        self.assertIs(cached.get_token("scope"), first)
        now[0] = 1699
        self.assertIs(cached.get_token("scope"), first)
        self.assertEqual(credential.get_token.call_count, 1)
        now[0] = 1700
        self.assertIs(cached.get_token("scope"), refreshed)
        self.assertEqual(credential.get_token.call_count, 2)

    def test_token_cache_isolates_scopes_and_token_options(self):
        from azure.core.credentials import AccessToken
        credential = Mock()
        credential.get_token.side_effect = [
            AccessToken("search", 4000), AccessToken("function", 4000),
            AccessToken("claims", 4000), AccessToken("tenant", 4000)]
        cached = identity_auth.CachedTokenCredential(credential, clock=lambda: 1000)
        search = cached.get_token("https://search.azure.com/.default")
        function = cached.get_token(AUDIENCE + "/.default")
        claims = cached.get_token(AUDIENCE + "/.default", claims="required-claims")
        tenant = cached.get_token(AUDIENCE + "/.default", tenant_id="specific-tenant")
        self.assertIs(cached.get_token("https://search.azure.com/.default"), search)
        self.assertIs(cached.get_token(AUDIENCE + "/.default"), function)
        self.assertIs(cached.get_token(AUDIENCE + "/.default", claims="required-claims"), claims)
        self.assertIs(cached.get_token(AUDIENCE + "/.default", tenant_id="specific-tenant"), tenant)
        self.assertEqual(credential.get_token.call_count, 4)

    def test_token_cache_never_falls_back_to_old_token_on_refresh_failure(self):
        from azure.core.credentials import AccessToken
        credential = Mock()
        credential.get_token.side_effect = [AccessToken("old", 2000),
                                           RuntimeError("refresh failed")]
        now = [1000]
        cached = identity_auth.CachedTokenCredential(credential, clock=lambda: now[0])
        cached.get_token("scope")
        now[0] = 1700
        with self.assertRaisesRegex(RuntimeError, "refresh failed"):
            cached.get_token("scope")
        self.assertEqual(credential.get_token.call_count, 2)

    def test_token_cache_close_clears_memory_and_closes_underlying_credential(self):
        from azure.core.credentials import AccessToken
        credential = Mock()
        credential.get_token.return_value = AccessToken("token", 4000)
        cached = identity_auth.CachedTokenCredential(credential, clock=lambda: 1000)
        cached.get_token("scope")
        cached.close()
        self.assertEqual(cached._tokens, {})
        credential.close.assert_called_once_with()

    def test_function_caller_uses_audience_token_and_preserves_contract(self):
        credential = Mock()
        credential.get_token.return_value.token = "identity-token"
        with patch("requests.Session") as factory:
            factory.return_value.post.return_value = response(data={
                "values": [{"recordId": "0", "data": {"vector": [1, 2]}}]})
            embedder = migrate.Embedder("pro", 2, "https://example.azurewebsites.net",
                                       function_auth_resource_id=AUDIENCE, credential=credential)
            self.assertEqual(embedder("hello"), [1, 2])
            credential.get_token.assert_called_once_with(AUDIENCE + "/.default")
            call = factory.return_value.post.call_args
            self.assertEqual(call.args[0], "https://example.azurewebsites.net/api/embed/pro/document")
            self.assertEqual(call.kwargs["headers"], {"Authorization": "Bearer identity-token"})
            self.assertEqual(call.kwargs["json"],
                             {"values": [{"recordId": "0", "data": {"text": "hello"}}]})

    def test_search_uses_entra_search_scope(self):
        credential, session = Mock(), Mock()
        credential.get_token.return_value.token = "identity-token"
        session.request.return_value = response(data={"ok": True})
        migrate.Search("https://example.search.windows.net", credential, session).request(
            "GET", "indexes/a")
        credential.get_token.assert_called_once_with("https://search.azure.com/.default")
        self.assertEqual(session.request.call_args.kwargs["headers"], {
            "Content-Type": "application/json", "Authorization": "Bearer identity-token"})

    def test_function_and_direct_callers_never_retry_401(self):
        credential = Mock()
        credential.get_token.return_value.token = "identity-token"
        with (patch("requests.Session") as factory, patch.object(migrate, "pause") as pause,
              patch.dict(os.environ, {
                  "COHERE_ENDPOINT": "https://example.services.ai.azure.com/providers/cohere/v2/embed",
                  "PRO_DEPLOYMENT": "migration-cohere-v5-pro"})):
            factory.return_value.post.return_value = response(401, {})
            for direct in (False, True):
                factory.return_value.post.reset_mock()
                embedder = migrate.Embedder("pro", 1024, "https://example.azurewebsites.net",
                                           direct=direct, function_auth_resource_id=AUDIENCE,
                                           credential=credential)
                with self.subTest(direct=direct), self.assertRaises(engine.ProviderError):
                    embedder("hello")
                self.assertEqual(factory.return_value.post.call_count, 1)
                pause.assert_not_called()

    def test_function_fails_closed_without_easyauth(self):
        request = func.HttpRequest(method="POST", url="https://example/api/embed/pro/query",
                                   body=b'{"values":[{"recordId":"r","data":{"text":"hello"}}]}',
                                   route_params={"model": "pro", "role": "query"})
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(function_app.embed(request).status_code, 503)
        with patch.dict(os.environ, {"REQUIRE_ENTRA_AUTH": "true"}, clear=True):
            self.assertEqual(function_app.embed(request).status_code, 401)
            request = func.HttpRequest(
                method="POST", url="https://example/api/embed/pro/query",
                headers={"X-MS-CLIENT-PRINCIPAL-ID": "search-managed-identity"},
                body=b'{"values":[{"recordId":"r","data":{"text":"hello"}}]}',
                route_params={"model": "pro", "role": "query"})
            with patch.object(function_app.engine, "embed", return_value=[1, 2]):
                result = function_app.embed(request)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(json.loads(result.get_body()), {
                "values": [{"recordId": "r", "data": {"vector": [1, 2]}}]})


class SchemaEquivalenceTests(unittest.TestCase):
    def setUp(self):
        self.expected = {"name": "new-index", "vectorSearch": sparse_vector_search()}
        self.actual = {"name": "new-index", "vectorSearch": copy.deepcopy(SERVICE_VECTOR_SEARCH),
                       "@odata.context": "https://offline.invalid/$metadata",
                       "@odata.etag": '"service-version"'}

    def test_exact_live_seven_differences_are_equivalent_without_mutating_inputs(self):
        before = copy.deepcopy(self.expected)
        self.assertEqual(migrate.canonical_schema(self.expected),
                         migrate.canonical_schema(self.actual))
        self.assertEqual(before, self.expected)

    def test_iso_duration_spelling_only_for_custom_api_timeout(self):
        parameters = self.actual["vectorSearch"]["vectorizers"][0]["customWebApiParameters"]
        for duration in ("PT230S", "PT3M50S", "PT0H3M50.0S", "P0DT230S"):
            parameters["timeout"] = duration
            with self.subTest(duration=duration):
                self.assertEqual(migrate.canonical_schema(self.expected),
                                 migrate.canonical_schema(self.actual))
        for duration in ("PT231S", "PT230Sx", "P1M", None):
            parameters["timeout"] = duration
            with self.subTest(duration=duration):
                self.assertNotEqual(migrate.canonical_schema(self.expected),
                                    migrate.canonical_schema(self.actual))
        self.expected["futureDuration"] = "PT230S"
        self.actual["futureDuration"] = "PT3M50S"
        parameters["timeout"] = "PT3M50S"
        self.assertNotEqual(migrate.canonical_schema(self.expected),
                            migrate.canonical_schema(self.actual))

    def test_nondefault_and_unknown_properties_are_not_discarded(self):
        for path, value in (
                (("futureUnknown",), None),
                (("vectorSearch", "profiles", 0, "compression"), "different-compression"),
                (("vectorSearch", "profiles", 0, "futureNull"), None),
                (("vectorSearch", "algorithms", 0, "hnswParameters", "metric"), "euclidean"),
                (("vectorSearch", "algorithms", 0, "exhaustiveKnnParameters"), {"metric": "cosine"}),
                (("vectorSearch", "vectorizers", 0, "azureOpenAIParameters"), {"deploymentId": "other"}),
                (("vectorSearch", "vectorizers", 0, "customWebApiParameters", "uri"), "https://different.invalid"),
                (("vectorSearch", "vectorizers", 0, "customWebApiParameters", "authResourceId"), "api://other"),
                (("vectorSearch", "vectorizers", 0, "customWebApiParameters", "authIdentity"), {"userAssignedIdentity": "other"}),
                (("vectorSearch", "vectorizers", 0, "customWebApiParameters", "httpHeaders"), {"x-custom": "other"}),
                (("vectorSearch", "vectorizers", 0, "customWebApiParameters", "httpMethod"), "GET"),
                (("vectorSearch", "vectorizers", 0, "customWebApiParameters", "httpMethod"), None),
                (("vectorSearch", "vectorizers", 0, "customWebApiParameters", "httpHeaders"), None),
                (("vectorSearch", "vectorizers", 0, "customWebApiParameters", "unknownNull"), None)):
            actual = copy.deepcopy(self.actual)
            node = actual
            for name in path[:-1]:
                node = node[name]
            node[path[-1]] = value
            with self.subTest(path=path, value=value):
                self.assertNotEqual(migrate.canonical_schema(self.expected),
                                    migrate.canonical_schema(actual))

    def test_defaults_do_not_apply_to_other_algorithm_or_vectorizer_kinds(self):
        for side in (self.expected, self.actual):
            side["vectorSearch"]["algorithms"][0]["kind"] = "exhaustiveKnn"
            side["vectorSearch"]["vectorizers"][0]["kind"] = "azureOpenAI"
        self.assertNotEqual(migrate.canonical_schema(self.expected),
                            migrate.canonical_schema(self.actual))


class FakeSearch:
    endpoint = "https://example.search.windows.net"

    def __init__(self):
        self.schemas = {"source": copy.deepcopy(SCHEMA)}
        self.rows = {"source": copy.deepcopy(DOCS)}
        self.filters = []

    def index(self, name):
        return "indexes/" + name

    def request(self, method, path, body=None, allow_missing=False, create=False):
        pieces = path.split("/")
        name = pieces[1]
        if path.endswith("/$count"):
            return len(self.rows[name])
        if path.endswith("/docs/search"):
            self.filters.append(body.get("filter"))
            if "filter" not in body:
                return {"value": [copy.deepcopy(DOCS[0])]}
            if body["filter"] == "id gt 'a''1'":
                return {"value": [copy.deepcopy(DOCS[1])]}
            return {"value": []}
        if path.endswith("/docs/index"):
            self.rows[name].extend({k: v for k, v in doc.items() if k != "@search.action"}
                                   for doc in body["value"])
            return {"value": [{"key": doc["id"], "status": True} for doc in body["value"]]}
        if len(pieces) == 4 and pieces[2] == "docs":
            from urllib.parse import unquote
            return next((copy.deepcopy(d) for d in self.rows[name]
                         if d["id"] == unquote(pieces[3])), None)
        if method == "PUT":
            self.schemas[name] = copy.deepcopy(body)
            self.rows[name] = []
            return body
        return copy.deepcopy(self.schemas.get(name))


class MigrationTests(unittest.TestCase):
    def setUp(self):
        # Scratch artifacts are confined to the owned project directory, never OS temp.
        self.directory = Path(__file__).parent / ("test-artifacts-" + uuid4().hex)
        self.addCleanup(lambda: shutil.rmtree(self.directory, ignore_errors=True))
        self.client = FakeSearch()

    def make_backup(self):
        migrate.backup(self.client, "source", self.directory, True)

    def test_backup_keyset_checksums_restore_all_fields(self):
        self.make_backup()
        _, manifest = migrate.read_backup(self.directory)
        self.assertEqual(manifest["count"], 2)
        self.assertIn("id gt 'a''1'", self.client.filters)
        migrate.restore(self.client, "copy", self.directory)
        self.assertEqual(self.client.rows["copy"], DOCS)

    def test_freeze_and_retrievable_guards(self):
        with self.assertRaises(ValueError):
            migrate.backup(self.client, "source", self.directory, False)
        fields = copy.deepcopy(SCHEMA["fields"])
        fields[2]["fields"][0]["retrievable"] = False
        with self.assertRaises(ValueError):
            migrate.guard_retrievable(fields)
        fields = copy.deepcopy(SCHEMA["fields"])
        fields[3]["stored"] = False
        with self.assertRaises(ValueError):
            migrate.guard_retrievable(fields)

    def test_tampering_detected_before_restore(self):
        self.make_backup()
        with (self.directory / "documents.jsonl").open("ab") as stream:
            stream.write(b"{}\n")
        with self.assertRaises(ValueError):
            migrate.restore(self.client, "copy", self.directory)
        self.assertNotIn("copy", self.client.schemas)

    def test_non_vector_fields_unchanged_query_role_configured(self):
        self.make_backup()
        embedder = Mock(side_effect=[[5, 6, 7], [8, 9, 10]])
        with patch.object(migrate, "Embedder", return_value=Mock(return_value=[1, 2, 3])) as query:
            migrate.restore(self.client, "fast-copy", self.directory, (
                embedder, "text", "vector", "fast", 3, "https://example.azurewebsites.net", AUDIENCE),
                migration_dir=self.directory / "migration")
            self.assertEqual(query.call_args.kwargs["role"], "query")
        for old, new in zip(DOCS, self.client.rows["fast-copy"]):
            self.assertEqual({k: v for k, v in old.items() if k != "vector"},
                             {k: v for k, v in new.items() if k != "vector"})
            self.assertEqual(len(new["vector"]), 3)
        vectorizer = self.client.schemas["fast-copy"]["vectorSearch"]["vectorizers"][-1]
        self.assertTrue(vectorizer["customWebApiParameters"]["uri"].endswith("/fast/query"))
        self.assertEqual(vectorizer["customWebApiParameters"]["authResourceId"], AUDIENCE)
        for path in self.directory.iterdir():
            if not path.is_file():
                continue
            contents = path.read_text().lower()
            self.assertNotIn("x-functions-key", contents)
            self.assertNotIn("authorization", contents)

    def test_function_query_probe_failure_prevents_destination_mutation(self):
        self.make_backup()
        embedder = Mock(return_value=[1, 2, 3])
        query = Mock(side_effect=engine.ProviderError("query route failed"))
        with patch.object(migrate, "Embedder", return_value=query), self.assertRaises(engine.ProviderError):
            migrate.restore(self.client, "failed-copy", self.directory, (
                embedder, "text", "vector", "fast", 3, "https://example.azurewebsites.net", AUDIENCE),
                migration_dir=self.directory / "migration")
        query.assert_called_once_with("first")
        self.assertNotIn("failed-copy", self.client.schemas)
        self.assertFalse((self.directory / "migration").exists())

    def test_migration_rejects_same_dimension_corrupted_destination_vector(self):
        self.make_backup()
        request = self.client.request

        def corrupt(method, path, *args, **kwargs):
            result = request(method, path, *args, **kwargs)
            if method == "GET" and "/docs/" in path and not path.endswith("/$count") and result:
                result["vector"] = [999, 999, 999]
            return result

        with (patch.object(self.client, "request", side_effect=corrupt),
              patch.object(migrate, "Embedder", return_value=Mock(return_value=[1, 2, 3])),
              self.assertRaisesRegex(RuntimeError, "field mismatch")):
            migrate.restore(self.client, "corrupt-copy", self.directory, (
                Mock(side_effect=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]),
                "text", "vector", "fast", 3, "https://example.azurewebsites.net", AUDIENCE),
                migration_dir=self.directory / "migration")
        schema, manifest = migrate.read_backup(self.directory / "migration")
        self.assertEqual(manifest["count"], 2)
        self.assertEqual(manifest["migration"]["vectorEncoding"], "IEEE754-binary32")
        self.assertEqual(schema["name"], "corrupt-copy")
        expected = list(migrate.documents(self.directory / "migration"))[0]["vector"]
        self.assertEqual(expected, migrate.float32_vector([0.1, 0.2, 0.3]))
        self.assertNotEqual(expected, DOCS[0]["vector"])

    def test_single_precision_round_trip_and_overflow(self):
        self.assertEqual(migrate.float32_vector([0.1, 0.2]),
                         migrate.float32_vector([0.100000001, 0.200000003]))
        with self.assertRaises(engine.ProviderError):
            migrate.float32_vector([1e100])

    def test_generated_backup_can_be_restored_without_model_calls(self):
        self.make_backup()
        output = self.directory / "migration"
        with patch.object(migrate, "Embedder", return_value=Mock(return_value=[1, 2, 3])):
            migrate.restore(self.client, "generated-copy", self.directory, (
                Mock(side_effect=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]),
                "text", "vector", "fast", 3, "https://example.azurewebsites.net", AUDIENCE),
                migration_dir=output)
        request = self.client.request

        def rounded_response(method, path, *args, **kwargs):
            result = request(method, path, *args, **kwargs)
            if method == "GET" and "/docs/" in path and not path.endswith("/$count") and result:
                result["vector"] = [round(value, 7) for value in result["vector"]]
            return result

        with patch.object(self.client, "request", side_effect=rounded_response):
            migrate.restore(self.client, "replayed-copy", output)
        self.assertEqual(self.client.rows["replayed-copy"], self.client.rows["generated-copy"])

    def test_odata_context_is_not_backed_up_or_restored(self):
        self.client.schemas["source"]["@odata.context"] = "https://example/$metadata#indexes/$entity"
        self.client.schemas["source"]["@odata.etag"] = '"source-version"'
        self.make_backup()
        schema, _ = migrate.read_backup(self.directory)
        self.assertNotIn("@odata.context", schema)
        self.assertNotIn("@odata.etag", schema)
        migrate.restore(self.client, "context-copy", self.directory)
        self.assertNotIn("@odata.context", self.client.schemas["context-copy"])

    def test_sparse_backup_replay_accepts_real_service_normalized_definitions(self):
        source = self.client.schemas["source"]
        source["vectorSearch"] = sparse_vector_search()
        source["fields"][-1]["vectorSearchProfile"] = "migration-fast-profile"
        self.make_backup()
        request = self.client.request

        def normalized_get(method, path, *args, **kwargs):
            result = request(method, path, *args, **kwargs)
            if method == "GET" and path == "indexes/normalized-copy" and result is not None:
                result["vectorSearch"] = copy.deepcopy(SERVICE_VECTOR_SEARCH)
            return result

        with patch.object(self.client, "request", side_effect=normalized_get):
            migrate.restore(self.client, "normalized-copy", self.directory)
        self.assertEqual(self.client.rows["normalized-copy"], DOCS)

    def test_migration_schema_change_is_rejected_before_upload(self):
        self.make_backup()
        request = self.client.request

        def changed_schema(method, path, *args, **kwargs):
            result = request(method, path, *args, **kwargs)
            if method == "GET" and path == "indexes/schema-corrupt" and result is not None:
                result["vectorSearch"]["vectorizers"][-1]["customWebApiParameters"][
                    "authResourceId"] = "api://different"
            return result

        with (patch.object(self.client, "request", side_effect=changed_schema),
              patch.object(migrate, "Embedder", return_value=Mock(return_value=[1, 2, 3])),
              self.assertRaisesRegex(RuntimeError, "Destination schema differs")):
            migrate.restore(self.client, "schema-corrupt", self.directory, (
                Mock(side_effect=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]),
                "text", "vector", "fast", 3, "https://example.azurewebsites.net", AUDIENCE),
                migration_dir=self.directory / "migration")
        self.assertEqual(self.client.rows["schema-corrupt"], [])

    def test_migration_and_generated_replay_accept_observed_service_defaults(self):
        self.make_backup()
        request = self.client.request
        observed = SERVICE_VECTOR_SEARCH["vectorizers"][0]

        def normalized_get(method, path, *args, **kwargs):
            result = request(method, path, *args, **kwargs)
            if method == "GET" and path in ("indexes/default-copy", "indexes/default-replay") and result:
                search = result["vectorSearch"]
                for algorithm in search["algorithms"]:
                    algorithm.setdefault("exhaustiveKnnParameters",
                                         SERVICE_VECTOR_SEARCH["algorithms"][0]["exhaustiveKnnParameters"])
                for profile in search["profiles"]:
                    profile.setdefault("compression", SERVICE_VECTOR_SEARCH["profiles"][0]["compression"])
                for vectorizer in search["vectorizers"]:
                    vectorizer.setdefault("azureOpenAIParameters", observed["azureOpenAIParameters"])
                    parameters = vectorizer["customWebApiParameters"]
                    for name in ("authIdentity", "httpHeaders", "httpMethod"):
                        parameters.setdefault(name, copy.deepcopy(observed["customWebApiParameters"][name]))
                    if parameters["timeout"] == "PT1M":
                        parameters["timeout"] = "PT60S"
            return result

        output = self.directory / "migration"
        with (patch.object(self.client, "request", side_effect=normalized_get),
              patch.object(migrate, "Embedder", return_value=Mock(return_value=[1, 2, 3]))):
            migrate.restore(self.client, "default-copy", self.directory, (
                Mock(side_effect=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]),
                "text", "vector", "fast", 3, "https://example.azurewebsites.net", AUDIENCE),
                migration_dir=output)
            migrate.restore(self.client, "default-replay", output)
        self.assertEqual(self.client.rows["default-copy"], self.client.rows["default-replay"])

    def test_existing_destination_refused(self):
        self.make_backup()
        with self.assertRaises(ValueError):
            migrate.restore(self.client, "source", self.directory)

    def test_key_requirements_and_schema_secrets(self):
        schema = copy.deepcopy(SCHEMA)
        schema["fields"][0]["sortable"] = False
        with self.assertRaises(ValueError):
            migrate.schema_key(schema)
        for value in ({"apiKey": "secret"}, {"httpHeaders": {"x-functions-key": "secret"}},
                      {"uri": "https://example/api?code=secret"},
                      {"uri": "https://example/api?api-key=secret"},
                      {"uri": "https://example/api?%63ode=secret"},
                      {"uri": "https://user:pass@example/api/embed"}):
            with self.assertRaises(ValueError):
                migrate.guard_no_secrets(value)
        schema = copy.deepcopy(SCHEMA)
        schema["encryptionKey"] = {"accessCredentials": {"applicationSecret": "cmk-secret"}}
        with self.assertRaises(ValueError):
            migrate.sanitize_schema(schema)

    def test_identity_schema_backup_restore_without_secret_artifacts(self):
        source = self.client.schemas["source"]
        source["vectorSearch"]["vectorizers"] = [{
            "name": "baseline-query", "kind": "customWebApi", "customWebApiParameters": {
                "uri": "https://example.azurewebsites.net/api/embed/baseline/query",
                "httpMethod": "POST", "authResourceId": AUDIENCE}}]
        source["vectorSearch"]["profiles"][0]["vectorizer"] = "baseline-query"
        self.make_backup()
        schema, manifest = migrate.read_backup(self.directory)
        self.assertEqual(manifest["credentialBindings"], [])
        self.assertEqual(schema["vectorSearch"]["vectorizers"][0][
            "customWebApiParameters"]["authResourceId"], AUDIENCE)
        migrate.restore(self.client, "copy", self.directory)
        actual = self.client.schemas["copy"]["vectorSearch"]["vectorizers"][0]
        self.assertEqual(actual["customWebApiParameters"]["authResourceId"], AUDIENCE)
        self.assertNotIn("httpHeaders", actual["customWebApiParameters"])
        expected_nonsecret, expected_bindings = migrate.sanitize_schema(source)
        actual_nonsecret, actual_bindings = migrate.sanitize_schema(self.client.schemas["copy"])
        actual_nonsecret["name"] = "source"
        self.assertEqual(actual_nonsecret, expected_nonsecret)
        self.assertEqual(actual_bindings, expected_bindings)
        self.assertEqual(self.client.rows["copy"], DOCS)
        contents = "".join(p.read_text() for p in self.directory.iterdir())
        self.assertNotIn("old-source-secret", contents)
        self.assertNotIn("new-restore-secret", contents)

    def test_redacted_credentials_and_only_recognized_slots(self):
        for secret in (None, "", "[REDACTED]", "real-key"):
            schema = copy.deepcopy(SCHEMA)
            schema["vectorSearch"]["vectorizers"] = [{
                "name": "v", "kind": "customWebApi", "customWebApiParameters": {
                    "uri": "https://example/api/embed/fast/query",
                    "httpHeaders": {"x-functions-key": secret}}}]
            with self.assertRaises(ValueError):
                migrate.sanitize_schema(schema)
            with self.assertRaises(ValueError):
                migrate.rehydrate_schema(SCHEMA, [
                    {"vectorizer": "v", "header": "Authorization", "environment": "OTHER_SECRET"}])
            schema["vectorSearch"]["vectorizers"][0]["customWebApiParameters"][
                "httpHeaders"]["Authorization"] = "Bearer arbitrary-secret"
            with self.assertRaises(ValueError):
                migrate.sanitize_schema(schema)

    def test_secret_source_schema_refused_before_any_backup_artifact(self):
        source = self.client.schemas["source"]
        source["vectorSearch"]["vectorizers"] = [{
            "name": "legacy", "kind": "customWebApi", "customWebApiParameters": {
                "uri": "https://example/api/embed/pro/query",
                "httpHeaders": {"x-functions-key": "must-not-persist"}}}]
        with self.assertRaises(ValueError):
            self.make_backup()
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_cmk_application_secret_refused_before_any_backup_artifact(self):
        source = self.client.schemas["source"]
        source["encryptionKey"] = {
            "accessCredentials": {"applicationSecret": "must-not-persist"}
        }
        with self.assertRaises(ValueError):
            self.make_backup()
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_upload_batches_count_and_bytes(self):
        self.assertEqual([len(x) for x in migrate.batches(
            {"id": str(i)} for i in range(1001))], [1000, 1])
        with patch.object(migrate, "MAX_BYTES", 100):
            with self.assertRaises(ValueError):
                list(migrate.batches([{"id": "x", "text": "x" * 100}]))
            batches = list(migrate.batches([{"id": "a"}, {"id": "b"}]))
            self.assertTrue(all(len(migrate.encoded({"value": b})) <= 100 for b in batches))

    def test_per_document_retry_and_permanent_failure(self):
        client = Mock()
        client.index.return_value = "indexes/dest"
        client.request.side_effect = [
            {"value": [{"key": "a", "status": True},
                       {"key": "b", "status": False, "statusCode": 503}]},
            {"value": [{"key": "b", "status": True}]}]
        with patch.object(migrate, "pause"):
            self.assertEqual(migrate.upload(client, "dest", [{"id": "a"}, {"id": "b"}], "id"), 2)
        self.assertEqual(len(client.request.call_args.args[2]["value"]), 1)
        client.request.side_effect = None
        client.request.return_value = {"value": [{"key": "a", "status": False, "statusCode": 400}]}
        with self.assertRaises(RuntimeError):
            migrate.upload(client, "dest", [{"id": "a"}], "id")

    def test_http_retry_only_429_and_5xx(self):
        for status in (400, 401, 403, 409, 429, 500, 503):
            with self.subTest(status=status):
                session = Mock()
                session.request.side_effect = [response(status, {}, {"Retry-After": "1"}),
                                               response(200, {"ok": True})]
                credential = Mock()
                credential.get_token.return_value.token = "identity-token"
                client = migrate.Search("https://example.search.windows.net",
                                        credential=credential, session=session)
                with patch.object(migrate, "pause") as wait:
                    if status in (429, 500, 503):
                        self.assertEqual(client.request("GET", "indexes/a"), {"ok": True})
                        wait.assert_called_once_with(0, "1")
                    else:
                        with self.assertRaises(RuntimeError):
                            client.request("GET", "indexes/a")
                        self.assertEqual(session.request.call_count, 1)

    def test_pipeline_custom_skill_and_vectorizer_roles(self):
        args = Mock(function_base="https://example.azurewebsites.net", index="idx",
                    datasource="source", skillset="skill", indexer="indexer",
                    storage_resource_id="/subscriptions/s/resourceGroups/g/providers/Microsoft.Storage/storageAccounts/a",
                    container="docs", model="pro", dimensions=7,
                    function_auth_resource_id=AUDIENCE, degree_of_parallelism=5)
        definitions = configure_pipeline.resources(args)
        skill = definitions[2][2]["skills"][0]
        self.assertTrue(skill["uri"].endswith("/pro/document"))
        self.assertEqual(skill["outputs"], [{"name": "vector", "targetName": "vector"}])
        self.assertEqual(skill["degreeOfParallelism"], 5)
        self.assertEqual(skill["batchSize"], 1)
        self.assertEqual(skill["timeout"], "PT230S")
        vectorizer = definitions[0][2]["vectorSearch"]["vectorizers"][0]
        self.assertTrue(vectorizer["customWebApiParameters"]["uri"].endswith("/pro/query"))
        self.assertEqual(vectorizer["customWebApiParameters"]["timeout"], "PT1M")
        for parameters in (skill, vectorizer["customWebApiParameters"]):
            self.assertEqual(parameters["authResourceId"], AUDIENCE)
            self.assertNotIn("authIdentity", parameters)
            self.assertNotIn("httpHeaders", parameters)
        datasource = definitions[1][2]
        self.assertEqual(datasource["credentials"]["connectionString"],
                         "ResourceId=" + args.storage_resource_id + ";")
        for parallelism in (1, 10):
            args.degree_of_parallelism = parallelism
            updated = configure_pipeline.resources(args)[2][2]["skills"][0]
            self.assertEqual(updated["degreeOfParallelism"], parallelism)
            self.assertEqual(updated["batchSize"], 1)
        for parallelism in (0, 11):
            args.degree_of_parallelism = parallelism
            with self.assertRaises(ValueError):
                configure_pipeline.resources(args)

    def test_pipeline_wait_reports_failure_not_silent_success(self):
        client = Mock()
        client.request.return_value = {"lastResult": {
            "status": "success", "itemsProcessed": 2, "itemsFailed": 1}}
        with self.assertRaises(RuntimeError):
            configure_pipeline.wait_for_indexer(client, "indexer", 1)
        client.request.return_value = {"lastResult": {"status": "persistentFailure"}}
        with self.assertRaises(RuntimeError):
            configure_pipeline.wait_for_indexer(client, "indexer", 1)
        client.request.return_value = {"lastResult": {
            "status": "success", "itemsProcessed": 2, "itemsFailed": 0}}
        configure_pipeline.wait_for_indexer(client, "indexer", 1)


if __name__ == "__main__":
    unittest.main()
