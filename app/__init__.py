# app/__init__.py

import logging

# Use a module-level variable to check initialization
_initialized = False

def initialize():
    global _initialized
    if not _initialized:
        _initialized = True
        logging.info("App initialization logic goes here.")
