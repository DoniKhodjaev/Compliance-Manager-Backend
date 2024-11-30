import re
import time
from transliterate import translit
import sqlite3
from marshmallow import Schema, fields


DATABASE_PATH = "./data/swift_messages.db"


ENTITY_LABELS = [
    # Russian (Cyrillic and Latin)
    "ООО",
    "OOO",
    "Общество с ограниченной ответственностью",
    "Obshchestvo s ogranichennoy otvetstvennostyu",
    "ЗАО",
    "ZAO",
    "Закрытое акционерное общество",
    "Zakrytoe aktsionernoe obshchestvo",
    "МЕЖДУНАРОДНАЯ КОМПАНИЯ ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО",
    "ОАО",
    "OAO",
    "Открытое акционерное общество",
    "Otkrytoe aktsionernoe obshchestvo",
    "MKPAO",
    "АО",
    "AO",
    "Акционерное общество",
    "Aktsionernoe obshchestvo",
    "AKTsIONERNAJa KOMPANIJa",
    "ПАО",
    "PAO",
    "Публичное акционерное общество",
    "Publichnoe aktsionernoe obshchestvo",
    "ИП",
    "IP",
    "Индивидуальный предприниматель",
    "Individual’nyy predprinimatel'",
    "MEZhDUNARODNAYa KOMPANIYa PUBLIChNOE AKTsIONERNOE OBShchESTVO",
    "ГУП",
    "GUP",
    "Государственное унитарное предприятие",
    "Gosudarstvennoe unitarnoe predpriyatie",
    "ЧП",
    "ChP",
    "Частное предприятие",
    "Chastnoe predpriyatie",
    "OBSchESTVO S OGRANIChENNOJ OTVETSTVENNOST'Ju",
    # English
    "LLC",
    "Limited Liability Company",
    "Inc",
    "Incorporated",
    "Corp",
    "Corporation",
    "Ltd",
    "Limited",
    "Plc",
    "Public Limited Company",
    "LLP",
    "Limited Liability Partnership",
    "Sole Prop.",
    "Sole Proprietorship",
    "NGO",
    "Non-Governmental Organization",
    "NPO",
    "Non-Profit Organization",
    "Co.",
    "Company",
    "SA",
    "Société Anonyme",
    "GmbH",
    "Gesellschaft mit beschränkter Haftung",
    "AG",
    "Aktiengesellschaft",
    # Uzbek (Cyrillic and Latin)
    "МЧЖ",
    "MChJ",
    "Масъулияти чекланган жамият",
    "Masʼuliyati cheklangan jamiyat",
    "MAS`ULIYATI CHEKLANGAN JAMIYAT",
    "АЖ",
    "AJ",
    "Акциядорлик жамияти",
    "Aktsiyadorlik jamiyati",
    "ЙТТ",
    "YTT",
    "Якка тартибдаги тадбиркор",
    "Yakka tartibdagi tadbirkor",
    "ДУК",
    "DUK",
    "Давлат унитар корхонаси",
    "Davlat unitar korxonasi",
    "ХК",
    "XK",
    "Хусусий корхона",
    "Xususiy korxona",
    "ФМШЖ",
    "FMShJ",
    "Фуқароларнинг масъулияти чекланган жамияти",
    "Fuqarolarning masʼuliyati cheklangan jamiyati",
    "КФХ",
    "KFX",
    "Крестьянское фермерское хозяйство",
    "Dehqon fermer xoʻjaligi",
    "ТШЖ",
    "TShJ",
    "Тадбиркорлик шерикчилиги жамияти",
    "Tadbirkorlik sherikchiligi jamiyati",
    "КХ",
    "KH",
    "Хусусий корхона",
    "Xususiy korxona",
]


ENTITY_ABBREVIATIONS = {
    # Russian (Cyrillic and Latin)
    "Общество с ограниченной ответственностью": "ООО",
    "Obshchestvo s ogranichennoy otvetstvennostyu": "OOO",
    "МЕЖДУНАРОДНАЯ КОМПАНИЯ ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО": "MKPAO",
    "Закрытое акционерное общество": "ЗАО",
    "Zakrytoe aktsionernoe obshchestvo": "ZAO",
    "Открытое акционерное общество": "ОАО",
    "Otkrytoe aktsionernoe obshchestvo": "OAO",
    "Акционерное общество": "АО",
    "Aktsionernoe obshchestvo": "AO",
    "AKTsIONERNAJa KOMPANIJa": "АО",
    "Публичное акционерное общество": "ПАО",
    "Publichnoe aktsionernoe obshchestvo": "PAO",
    "Индивидуальный предприниматель": "ИП",
    "Individual’nyy predprinimatel'": "IP",
    "Некоммерческая организация": "НКО",
    "Nekommercheskaya organizatsiya": "NKO",
    "Государственное унитарное предприятие": "ГУП",
    "Gosudarstvennoe unitarnoe predpriyatie": "GUP",
    "Частное предприятие": "ЧП",
    "Chastnoe predpriyatie": "ChP",
    "OBSchESTVO S OGRANIChENNOJ OTVETSTVENNOST'Ju": "ООО",
    # English
    "Limited Liability Company": "LLC",
    "Incorporated": "Inc",
    "Corporation": "Corp",
    "Limited": "Ltd",
    "Public Limited Company": "Plc",
    "Limited Liability Partnership": "LLP",
    "Sole Proprietorship": "Sole Prop.",
    "Non-Governmental Organization": "NGO",
    "Non-Profit Organization": "NPO",
    "Company": "Co.",
    "Société Anonyme": "SA",
    "Gesellschaft mit beschränkter Haftung": "GmbH",
    "Aktiengesellschaft": "AG",
    # Uzbek (Cyrillic and Latin)
    "Масъулияти чекланган жамият": "МЧЖ",
    "Masʼuliyati cheklangan jamiyat": "MChJ",
    "MAS`ULIYATI CHEKLANGAN JAMIYAT": "MChJ",
    "Акциядорлик жамияти": "АЖ",
    "Aktsiyadorlik jamiyati": "AJ",
    "Якка тартибдаги тадбиркор": "ЙТТ",
    "Yakka tartibdagi tadbirkor": "YTT",
    "Давлат унитар корхонаси": "ДУК",
    "Davlat unitar korxonasi": "DUK",
    "Хусусий корхона": "ХК",
    "Xususiy korxona": "XK",
    "Фуқароларнинг масъулияти чекланган жамияти": "ФМШЖ",
    "Fuqarolarning masʼuliyati cheklangan jamiyati": "FMShJ",
    "Крестьянское фермерское хозяйство": "КФХ",
    "Dehqon fermer xoʻjaligi": "KFX",
    "Тадбиркорлик шерикчилиги жамияти": "ТШЖ",
    "Tadbirkorlik sherikchiligi jamiyati": "TShJ",
}


def get_db_connection():
    """Reusable function to establish a database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def transliterate_text(text):
    if text is None:
        return None
    try:
        if any(ord(char) in range(0x0400, 0x04FF) for char in text):
            return translit(text, "ru", reversed=True)
        return text

    except Exception as e:
        print(f"Error in transliteration: {e}")
        return text


def clean_company_name(name):
    if not name:
        return None

    # Replace full names with abbreviations

    for full_name, abbreviation in ENTITY_ABBREVIATIONS.items():
        name = re.sub(re.escape(full_name), abbreviation, name, flags=re.IGNORECASE)

    # Remove additional labels (if needed)
    pattern = r"\b(?:" + "|".join(ENTITY_LABELS) + r")\b"
    name = re.sub(pattern, "", name, flags=re.IGNORECASE).strip()

    # Clean up unnecessary characters
    name = re.sub(r"[\"\'/]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def is_company_name(name):
    if not name:
        return False

    name_upper = name.upper()

    pattern = (
        r"\b(?:"
        + "|".join(re.escape(label).upper() for label in ENTITY_LABELS)
        + r")\b"
    )

    return bool(re.search(pattern, name_upper))


def request_with_delay(delay=1):

    time.sleep(delay)


def extract_jurisdiction(company_name):

    jurisdictions = {
        "S.P.A.": "Italy",
        "SA": "Multiple",
        "AG": "Germany/Switzerland",
        "GmbH": "Germany",
        "Ltd": "UK",
        "Inc": "USA",
        "LLC": "USA",
        "B.V.": "Netherlands",
        "N.V.": "Netherlands/Belgium",
    }

    company_name_upper = company_name.upper()

    for suffix, country in jurisdictions.items():

        if suffix.upper() in company_name_upper:

            return country

    return "Unknown"


class SwiftMessageSchema(Schema):

    message = fields.Str(required=True)

    reference = fields.Str(required=True)
