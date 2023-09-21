import azure.functions as func
import logging
import json
from search import bp as search_bp
from lookup import bp as lookup_bp
from suggest import bp as suggest_bp

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

app.register_functions(lookup_bp)
app.register_functions(search_bp)
app.register_functions(suggest_bp)


