import os
import re
import json
import sqlite3
import time
from datetime import datetime
from transliterate import translit
from bs4 import BeautifulSoup
import requests
from urllib.parse import quote, urljoin
from app.utils import (
    DATABASE_PATH,
    get_db_connection,
    transliterate_text,
    clean_company_name,
    request_with_delay,
)  # Import from utils
import logging

RATE_LIMIT_DELAY = 1  # Delay between requests in seconds


# Initialize Database
def initialize_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS swift_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_reference TEXT,
        transaction_type TEXT,
        transaction_date TEXT,
        transaction_currency TEXT,
        transaction_amount TEXT,
        sender_account TEXT,
        sender_inn TEXT,
        sender_name TEXT,
        sender_address TEXT,
        sender_bank_code TEXT,
        receiver_account TEXT,
        receiver_inn TEXT,
        receiver_name TEXT,
        receiver_kpp TEXT,
        receiver_bank_code TEXT,
        receiver_bank_name TEXT,
        transaction_purpose TEXT,
        transaction_fees TEXT,
        company_info TEXT,
        receiver_info TEXT
    )
    """
    )
    conn.commit()
    conn.close()


def extract_transaction_reference(message):
    match = re.search(r":20:([^\n]+)", message)
    return match.group(1).strip() if match else None


def extract_transaction_type(message):
    match = re.search(r":23B:([^\n]+)", message)
    return match.group(1).strip() if match else None


def extract_transaction_date_and_currency(message):
    match = re.search(r":32A:(\d{6})([A-Z]{3})([\d,]+)", message)
    if match:
        raw_date, currency, amount = match.groups()
        try:
            formatted_date = datetime.strptime(raw_date, "%y%m%d").strftime("%Y-%m-%d")
            return formatted_date, currency, amount.replace(",", ".")
        except ValueError as e:
            print(f"Date parsing error: {e}")
            return None, None, None
    return None, None, None


def extract_sender_details(message):
    patterns = [
        r":50K:\s*/(\d+)\s*\n(?:INN(\d+)\s*\n)?([^\n]+)(?:\n([\s\S]+?)(?=:\d{2}[A-Z]:))?",
        r":50K:\s*/(\d+)\s*\n([^\n]+)(?:\n([\s\S]+?)(?=:\d{2}[A-Z]:))?",
        r":50K:(?:\s*/)?(\d+)\s*\n([^\n]+)(?:\n([\s\S]+?)(?=:\d{2}[A-Z]:))?",
    ]

    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            groups = match.groups()
            account = groups[0].strip() if groups[0] else None

            if len(groups) == 4:
                inn = groups[1].strip() if groups[1] else None
                name = clean_company_name(groups[2])
                address = (
                    transliterate_text(groups[3].strip().replace("\n", ", "))
                    if groups[3]
                    else None
                )
            else:
                inn = None
                name = clean_company_name(groups[1])
                address = (
                    transliterate_text(groups[2].strip().replace("\n", ", "))
                    if groups[2]
                    else None
                )

            if name:
                return account, inn, name, address

    return None, None, None, None


def extract_receiver_details(message):
    account_pattern = r":59:\s*/(\d+)"
    account_match = re.search(account_pattern, message)
    account = account_match.group(1).strip() if account_match else None

    details_pattern = r":59:\s*/\d+\s*\n(?:INN(\d+)(?:\.KPP(\d+))?\s*\n)?([^\n]+)"
    details_match = re.search(details_pattern, message)

    if details_match:
        inn = details_match.group(1).strip() if details_match.group(1) else None
        kpp = details_match.group(2).strip() if details_match.group(2) else None
        name = clean_company_name(details_match.group(3))
        return account, name, inn, kpp

    return account, None, None, None


def save_to_database(parsed_data):
    """Save parsed SWIFT data to the database."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check if a record with the same transaction_reference already exists
            cursor.execute(
                "SELECT 1 FROM swift_messages WHERE transaction_reference = ?",
                (parsed_data.get("transaction_reference"),),
            )
            if cursor.fetchone() is not None:
                print(
                    f"Transaction with reference {parsed_data.get('transaction_reference')} already exists in the database."
                )
                return  # Exit the function without saving duplicate

            # Proceed with insertion if no duplicate is found
            cursor.execute(
                """
                INSERT INTO swift_messages (
                    transaction_reference, transaction_type, transaction_date, transaction_currency,
                    transaction_amount, sender_account, sender_inn, sender_name, sender_address,
                    sender_bank_code, receiver_account, receiver_inn, receiver_name, receiver_kpp,
                    receiver_bank_code, receiver_bank_name, transaction_purpose, transaction_fees,
                    company_info, receiver_info
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    parsed_data.get("transaction_reference"),
                    parsed_data.get("transaction_type"),
                    parsed_data.get("transaction_date"),
                    parsed_data.get("transaction_currency"),
                    parsed_data.get("transaction_amount"),
                    parsed_data.get("sender_account"),
                    parsed_data.get("sender_inn"),
                    parsed_data.get("sender_name"),
                    parsed_data.get("sender_address"),
                    parsed_data.get("sender_bank_code"),
                    parsed_data.get("receiver_account"),
                    parsed_data.get("receiver_inn"),
                    parsed_data.get("receiver_name"),
                    parsed_data.get("receiver_kpp"),
                    parsed_data.get("receiver_bank_code"),
                    parsed_data.get("receiver_bank_name"),
                    parsed_data.get("transaction_purpose"),
                    parsed_data.get("transaction_fees"),
                    json.dumps(
                        parsed_data.get("company_info", {})
                    ),  # Ensure JSON serialization of company_info
                    json.dumps(
                        parsed_data.get("receiver_info", {})
                    ),  # Ensure JSON serialization of receiver_info
                ),
            )
            conn.commit()
            logging.info(f"Transaction {parsed_data.get('transaction_reference')} saved")
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        raise


def extract_mt103_data(message):
    message = message.replace("\r", "\n").replace("\n\n", "\n")

    transaction_date, currency, amount = extract_transaction_date_and_currency(message)
    sender_account, sender_inn, sender_name, sender_address = extract_sender_details(
        message
    )
    receiver_account, receiver_name, receiver_inn, receiver_kpp = (
        extract_receiver_details(message)
    )

    return {
        "transaction_reference": extract_transaction_reference(message),
        "transaction_type": extract_transaction_type(message),
        "transaction_date": transaction_date,
        "transaction_currency": currency,
        "transaction_amount": amount,
        "sender_account": sender_account,
        "sender_inn": sender_inn,
        "sender_name": sender_name,
        "sender_address": sender_address,
        "receiver_account": receiver_account,
        "receiver_name": receiver_name,
        "receiver_inn": receiver_inn,
        "receiver_kpp": receiver_kpp,
    }


initialize_db()
