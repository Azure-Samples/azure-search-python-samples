import logging

import azure.functions as func

from dlq import build_dead_letter_record, create_dead_letter_client, send_dead_letter_record
from indexing import SearchIngestionService
from shared_code.config import COSMOS_CONNECTION_NAME, create_search_client, load_settings


bp = func.Blueprint()


@bp.function_name(name="cosmosSearchSync")
@bp.cosmos_db_trigger(
    arg_name="documents",
    database_name="%COSMOS_DATABASE_NAME%",
    container_name="%COSMOS_CONTAINER_NAME%",
    connection=COSMOS_CONNECTION_NAME,
    lease_container_name="%COSMOS_LEASE_CONTAINER_NAME%",
    create_lease_container_if_not_exists=False,
)
def cosmos_search_sync(documents: func.DocumentList) -> None:
    if not documents:
        logging.info("No Cosmos DB changes received.")
        return

    settings = load_settings()
    search_client = create_search_client(settings)
    dead_letter_client = create_dead_letter_client(settings)
    ingestion_service = SearchIngestionService(search_client)

    logging.info("Processing %s Cosmos DB changes.", len(documents))

    # P0-3: one failing source document should not stall the rest of the batch.
    for raw_document in documents:
        source_document = dict(raw_document)
        source_id = source_document.get("id", "unknown")
        try:
            outcome = ingestion_service.sync_source_document(source_document)
            logging.info(
                "Indexed source document %s with outcome %s.",
                source_id,
                outcome,
            )
        except Exception as exc:  # noqa: BLE001
            logging.exception("Failed to process source document %s.", source_id)
            dead_letter_record = build_dead_letter_record(source_document, exc)
            send_dead_letter_record(dead_letter_client, dead_letter_record)
