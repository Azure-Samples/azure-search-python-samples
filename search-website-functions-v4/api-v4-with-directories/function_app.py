import azure.functions as func
import logging
import json
from Search.search import bp as search_bp
from Lookup.lookup import bp as lookup_bp
from Suggest.suggest import bp as suggest_bp

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

app.register_functions(lookup_bp)
app.register_functions(search_bp)
app.register_functions(suggest_bp)


