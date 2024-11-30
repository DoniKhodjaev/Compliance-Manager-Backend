from flask import Blueprint, request, jsonify, abort

from app.services.swift_service import (
    extract_mt103_data,
    extract_transaction_reference,
    save_to_database,
)

from app.services.company_service import (
    search_orginfo,
    fetch_company_details_orginfo,
    get_company_details,
)

from app.utils import get_db_connection

import sqlite3


swift_blueprint = Blueprint("swift_blueprint", __name__)


@swift_blueprint.route("/parsed-swift-files", methods=["GET"])
def get_parsed_files():

    try:

        conn = get_db_connection()

        cursor = conn.cursor()

        cursor.execute("SELECT * FROM swift_messages")

        rows = cursor.fetchall()

        parsed_files = [dict(row) for row in rows]

        return jsonify(parsed_files)

    except sqlite3.Error as e:

        return jsonify({"error": str(e)}), 500

    finally:

        conn.close()


@swift_blueprint.route("/process-swift", methods=["POST"])
def process_swift():

    if not request.is_json:

        abort(400, description="Content-Type must be application/json")

    data = request.json

    message = data.get("message", "")

    try:

        if not message.strip():

            raise ValueError("The SWIFT message cannot be empty.")

        result = extract_mt103_data(message)

        if not result.get("transaction_reference"):

            raise ValueError("Failed to extract required information")

        # Save to database

        save_to_database(result)

        return jsonify(result)

    except ValueError as e:

        return jsonify({"error": str(e)}), 400

    except Exception as e:

        return jsonify({"error": str(e)}), 500


@swift_blueprint.route("/search-orginfo", methods=["GET"])
def api_search_orginfo():

    company_name = request.args.get("company_name")

    try:

        org_url = search_orginfo(company_name)

        if org_url:

            company_details = fetch_company_details_orginfo(org_url)

            return jsonify(company_details)

        return jsonify({"error": "No match found"}), 404

    except Exception as e:

        return jsonify({"error": str(e)}), 500


@swift_blueprint.route("/search-egrul", methods=["GET"])
def api_search_egrul():

    inn = request.args.get("inn")

    try:

        company_details = get_company_details(inn)

        if company_details:

            return jsonify(company_details)

        return jsonify({"error": "No match found"}), 404

    except Exception as e:

        return jsonify({"error": str(e)}), 500


@swift_blueprint.route("/search-swift", methods=["GET"])
def search_swift():

    reference = request.args.get("transaction_reference")

    if not reference:

        return jsonify({"error": "Invalid query"}), 400

    try:

        result = extract_transaction_reference(reference)

        return jsonify(result) if result else jsonify({"error": "Not found"}), 404

    except Exception as e:

        return jsonify({"error": str(e)}), 500


@swift_blueprint.route("/update-status/<string:id>", methods=["PATCH"])
def update_status(id):

    new_status = request.json.get("status")

    if not new_status:

        return jsonify({"error": "Missing status"}), 400

    try:

        conn = get_db_connection()

        cursor = conn.cursor()

        cursor.execute(
            "UPDATE swift_messages SET status = ? WHERE id = ?", (new_status, id)
        )

        conn.commit()

        if cursor.rowcount > 0:

            return jsonify({"message": "Status updated successfully"}), 200

        else:

            return jsonify({"error": "No message found with the given ID"}), 404

    except sqlite3.Error as e:

        return jsonify({"error": str(e)}), 500

    finally:

        conn.close()


@swift_blueprint.route("/delete-message/<string:id>", methods=["DELETE"])
def delete_message(id):

    try:

        conn = get_db_connection()

        cursor = conn.cursor()

        cursor.execute("DELETE FROM swift_messages WHERE id = ?", (id,))

        conn.commit()

        if cursor.rowcount > 0:

            return (
                jsonify(
                    {"message": f"Message with reference {id} deleted successfully"}
                ),
                200,
            )

        else:

            return jsonify({"error": f"No message found with reference {id}"}), 404

    except sqlite3.Error as e:

        return jsonify({"error": str(e)}), 500

    finally:

        conn.close()
