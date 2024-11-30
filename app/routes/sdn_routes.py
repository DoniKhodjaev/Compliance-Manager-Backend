import os
import json
from flask import Blueprint, jsonify, request
from app.services.sdn_service import SDNService
from urllib.parse import unquote

# Initialize Blueprint for SDN Routes
sdn_blueprint = Blueprint("sdn", __name__)

@sdn_blueprint.route("/health", methods=["GET"])
def health_check():
    """Check if the SDN service is healthy."""
    return jsonify({"status": "ok"})

@sdn_blueprint.route("/list", methods=["GET"])
def get_sdn_list():
    """Get the full SDN list."""
    try:
        if SDNService.is_cache_valid():
            with open(SDNService.CACHE_FILE_PATH, "r") as cache_file:
                sdn_entries = json.load(cache_file)
        else:
            sdn_entries = SDNService.parse_xml_to_json()
        return jsonify(sdn_entries)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@sdn_blueprint.route("/search", methods=["GET"])
def search_sdn():
    """Search the SDN list with given criteria."""
    try:
        query = unquote(request.args.get('query', '')).strip()
        if not query:
            return jsonify({"average_match_score": 0.0, "results": []})

        result = SDNService.search_sdn(query)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@sdn_blueprint.route("/update", methods=["POST"])
def update_sdn_list():
    """Update the SDN list from the source."""
    try:
        download_result = SDNService.download_sdn_file()
        if download_result["status"] == "error":
            return jsonify(download_result), 500
        
        sdn_entries = SDNService.parse_xml_to_json()
        return jsonify({
            "status": "success",
            "message": "SDN list updated successfully",
            "entries_count": len(sdn_entries)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
