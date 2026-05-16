import azure.functions as func

from ingest import bp as ingest_bp
from query import bp as query_bp


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

app.register_functions(query_bp)
app.register_functions(ingest_bp)
