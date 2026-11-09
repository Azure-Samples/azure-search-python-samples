"""Azure AI Search custom skill/vectorizer envelope, independent of Functions host."""
from embedding_engine import InputError, ProviderError, TransientProviderError


def process_values(body, model, role, embedding_engine):
    if not isinstance(body, dict) or not isinstance(body.get("values"), list) or not body["values"]:
        raise InputError("Request must contain a nonempty values array")
    results = []
    for record in body["values"]:
        if not isinstance(record, dict) or not isinstance(record.get("recordId"), str):
            raise InputError("Every record requires a string recordId")
        result = {"recordId": record["recordId"]}
        try:
            data = record.get("data")
            if not isinstance(data, dict):
                raise InputError("Record data must be an object")
            result["data"] = {"vector": embedding_engine.embed(model, role, data.get("text"))}
        except TransientProviderError:
            raise
        except (InputError, ProviderError) as exc:
            result["errors"] = [{"message": str(exc)}]
        results.append(result)
    return {"values": results}
