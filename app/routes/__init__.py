# app/routes/__init__.py

import logging

# Use a module-level variable to track if routes have been loaded
_routes_loaded = False

def initialize_routes():
    global _routes_loaded
    if not _routes_loaded:
        _routes_loaded = True
        logging.info("Routes have been successfully loaded.")
