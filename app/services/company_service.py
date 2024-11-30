import json
import os
import requests
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime
from unidecode import unidecode
from typing import Dict, Any, Set, Optional
import logging
from urllib.parse import quote, urljoin
from app.utils import is_company_name as utils_is_company_name
from transliterate import translit
from typing import List


logger = logging.getLogger(__name__)

MAX_DEPTH = 5  # Maximum depth for recursive company checks
RATE_LIMIT_DELAY = 1  # Delay between requests in seconds

# Add these constants at the top of the file
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

# Standalone functions for backward compatibility
def search_orginfo(company_name: str) -> Optional[Dict[str, Any]]:
    return CompanyService.search_orginfo(company_name)

def search_egrul(inn: str) -> Optional[Dict[str, Any]]:
    return CompanyService.search_egrul(inn)

def is_company_name(name: str) -> bool:
    return CompanyService.is_company_name(name)

def fetch_company_details_orginfo(org_url: str) -> Optional[Dict[str, Any]]:
    """Fetch detailed company information from orginfo.uz"""
    if not org_url:
        return None

    try:
        time.sleep(RATE_LIMIT_DELAY)
        response = requests.get(org_url, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        company_details = {}

        # Extract company name
        name_tag = soup.find("h1", class_="h1-seo")
        if name_tag:
            company_details["name"] = name_tag.text.strip()

        # Extract TIN
        tin_tag = soup.find("span", id="organizationTinValue")
        if tin_tag:
            company_details["TIN"] = tin_tag.text.strip()

        # Extract CEO
        ceo_section = soup.find("h5", string="Management information")
        if ceo_section:
            ceo_name_tag = ceo_section.find_next("a")
            if ceo_name_tag:
                company_details["CEO"] = ceo_name_tag.text.strip()

        # Extract address
        address_section = soup.find("h5", string="Contact information")
        if address_section:
            address_row = address_section.find_next("div", class_="row")
            if address_row:
                address_tag = address_row.find("span")
                if address_tag:
                    company_details["address"] = address_tag.text.strip()

        # Extract founders
        founders = []
        founder_section = soup.find("h5", string="Founders")
        if founder_section:
            founder_rows = founder_section.find_next_sibling("div").find_all("div", class_="row")
            for row in founder_rows:
                founder_name_tag = row.find("a")
                if founder_name_tag:
                    founder_name = founder_name_tag.text.strip()
                    # Extract ownership percentage
                    ownership_text = row.get_text()
                    ownership_match = re.search(r'(\d+(?:\.\d+)?)%', ownership_text)
                    ownership_percentage = float(ownership_match.group(1)) if ownership_match else None
                    
                    founder = {
                        "owner": founder_name,
                        "isCompany": is_company_name(founder_name),
                        "ownershipPercentage": ownership_percentage
                    }
                    founders.append(founder)
                    print(f"Found Founder: {founder_name} ({ownership_percentage}%)")

        if founders:
            company_details["Founders"] = founders

        return company_details

    except Exception as e:
        logger.error(f"Error fetching company details from orginfo: {str(e)}")
        return None

def get_company_details(inn: str, depth: int = 0, processed_inns: Optional[Set[str]] = None) -> Optional[Dict[str, Any]]:
    """Backward compatibility function for getting company details."""
    return CompanyService.search_egrul(inn, depth, processed_inns)

def transliterate_text(text):
    if text is None:
        return None
    try:
        if any(ord(char) in range(0x0400, 0x04FF) for char in text):
            return translit(text, 'ru', reversed=True)
        return text
    except Exception as e:
        logger.error(f"Error in transliteration: {e}")
        return text

class CompanyService:
    @staticmethod
    def is_company_name(name: str) -> bool:
        """Check if a name represents a company based on common business suffixes."""
        if not name:
            return False
        
        company_indicators = [
            'ООО', 'OOO', 'АО', 'AO', 'ЗАО', 'ZAO', 'ПАО', 'PAO',
            'LLC', 'LTD', 'INC', 'CORP', 'GMBH', 'AG',
            'МЧЖ', 'MChJ', 'Ж', 'AJ'
        ]
        
        return any(indicator in name.upper() for indicator in company_indicators)

    @staticmethod
    def search_egrul(inn: str, depth: int = 0, processed_inns: Optional[Set[str]] = None) -> Optional[Dict[str, Any]]:
        """Search EGRUL database for company information with recursive founder lookup."""
        if not inn:
            return None

        if processed_inns is None:
            processed_inns = set()

        # Avoid infinite recursion and circular ownership
        if depth >= MAX_DEPTH or inn in processed_inns:
            return {
                "error": "Maximum depth reached or circular ownership detected",
                "inn": inn,
                "processed_inns": list(processed_inns),
            }

        processed_inns.add(inn)
        time.sleep(RATE_LIMIT_DELAY)

        if inn.isdigit():
            url = f"https://egrul.itsoft.ru/{inn}"
            headers = {"User-Agent": "Mozilla/5.0"}

            try:
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')

                company_info = {
                    'inn': inn,
                    'name': None,
                    'registrationDate': None,
                    'address': None,
                    'CEO': None,
                    'Founders': [],
                }

                # Extract and abbreviate company name
                name_tag = soup.find('h1', id='short_name')
                if name_tag:
                    company_info['name'] = CompanyService.apply_abbreviations(name_tag.text.strip())
                    logger.info(f"Company Name (abbreviated): {company_info['name']}")

                # Extract address
                address_div = soup.find('div', id='address')
                if address_div:
                    company_info['address'] = address_div.text.strip()

                # Extract registration date
                reg_date_div = soup.find('div', string=re.compile(r'Дата регистрации'))
                if reg_date_div:
                    date_match = re.search(r'\d{2}\.\d{2}\.\d{4}', reg_date_div.text)
                    if date_match:
                        company_info['registrationDate'] = date_match.group()

                # Extract and abbreviate CEO information
                ceo_div = soup.find('div', id='chief')
                if ceo_div:
                    ceo_name_tag = ceo_div.find('a')
                    if ceo_name_tag:
                        ceo_name = ceo_name_tag.text.strip()
                        company_info['CEO'] = transliterate_text(ceo_name)  # Transliterate CEO name
                        logger.info(f"CEO: {company_info['CEO']}")

                # Extract and process founders
                founders_div = soup.find('div', id='СвУчредит')
                if founders_div:
                    founders = []
                    # Get all text nodes between <a> tags
                    for founder_element in founders_div.find_all('a'):
                        founder_name = founder_element.text.strip()
                        founder_inn = founder_element.get('href', '').strip('/')
                        
                        # Get the text after the <a> tag until the next <br> or end of parent
                        founder_details = founder_element.next_sibling
                        if founder_details:
                            founder_text = founder_details.string.strip()
                            # Extract ownership percentage
                            ownership_match = re.search(r'Доля \d+р\. \((\d+(?:\.\d+)?)%\)', founder_text)
                            ownership_percentage = float(ownership_match.group(1)) if ownership_match else None

                            logger.info(f"Processing founder: {founder_name}")
                            logger.info(f"Details text: {founder_text}")
                            logger.info(f"Extracted ownership: {ownership_percentage}%")

                            founder = {
                                "owner": transliterate_text(founder_name),
                                "originalName": founder_name,
                                "cleanName": transliterate_text(CompanyService.apply_abbreviations(founder_name)),
                                "inn": founder_inn,
                                "isCompany": utils_is_company_name(founder_name),
                                "ownershipPercentage": ownership_percentage
                            }

                            # Recursively fetch company details for company founders
                            if founder['isCompany'] and founder_inn and founder_inn.isdigit():
                                nested_details = CompanyService.search_egrul(
                                    founder_inn, 
                                    depth + 1, 
                                    processed_inns.copy()
                                )
                                if nested_details:
                                    founder['companyDetails'] = {
                                        'name': transliterate_text(nested_details.get('name')),
                                        'cleanName': transliterate_text(CompanyService.apply_abbreviations(nested_details.get('name'))),
                                        'inn': nested_details.get('inn'),
                                        'CEO': transliterate_text(nested_details.get('CEO')),
                                        'Founders': nested_details.get('Founders', [])
                                    }

                            founders.append(founder)
                            logger.info(f"Added founder: {transliterate_text(founder_name)} (INN: {founder_inn})")

                    company_info['Founders'] = founders

                    # Validate total ownership
                    total_ownership = sum(f.get('ownershipPercentage', 0) or 0 for f in founders)
                    if abs(total_ownership - 100.0) > 0.1:  # Allow small rounding errors
                        logger.warning(f"Total ownership {total_ownership}% differs from 100% for company {inn}")

                return company_info if company_info['name'] or company_info['Founders'] else None

            except Exception as e:
                logger.error(f"Error retrieving company data for INN {inn}: {e}")
                return None
        else:
            # Handle foreign companies or non-numeric INNs
            return {
                'inn': inn,
                'registrationDate': None,
                'address': None,
                'CEO': None,
                'Founders': [],
                'isForeign': True,
                'jurisdiction': CompanyService.extract_jurisdiction(inn)
            }

    @staticmethod
    def extract_jurisdiction(company_name: str) -> str:
        """Extract jurisdiction from company name or identifier."""
        jurisdictions = {
            'S.P.A.': 'Italy',
            'SA': 'Multiple',
            'AG': 'Germany/Switzerland',
            'GmbH': 'Germany',
            'Ltd': 'UK',
            'Inc': 'USA',
            'LLC': 'USA',
            'B.V.': 'Netherlands',
            'N.V.': 'Netherlands/Belgium'
        }
        
        company_name_upper = company_name.upper()
        for suffix, country in jurisdictions.items():
            if suffix.upper() in company_name_upper:
                return country
            
        return 'Unknown'

    @staticmethod
    def search_orginfo(company_name):
        if not company_name:
            print("Company name is empty.")
            return None

        encoded_name = quote(company_name)
        search_url = f"https://orginfo.uz/en/search/organizations/?q={encoded_name}&sort=active"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        try:
            time.sleep(RATE_LIMIT_DELAY)
            response = requests.get(search_url, headers=headers, timeout=15)
            response.raise_for_status()  # Check if the request was successful
            print(f"Searching orginfo for {company_name}: Status {response.status_code}")

            soup = BeautifulSoup(response.text, "html.parser")
            
            # Log response text to verify if structure matches expectations
            print(soup.prettify())  # Print the HTML structure for debugging

            for link in soup.find_all("a", href=True):
                if company_name.lower() in link.text.lower():
                    print(f"Found match for {company_name} with URL: {link['href']}")
                    return urljoin("https://orginfo.uz", link['href'])
            print(f"No match found for {company_name} on orginfo.")
        except requests.RequestException as e:
            print(f"Error searching for company: {e}")
        return None
    
    @staticmethod
    def fetch_company_details_orginfo(org_url):
        if not org_url:
            print("Org URL is empty.")
            return None

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        try:
            time.sleep(RATE_LIMIT_DELAY)
            response = requests.get(org_url, headers=headers, timeout=15)
            response.raise_for_status()
            print(f"Fetching company details from {org_url}")

            soup = BeautifulSoup(response.text, "html.parser")
            company_details = {}

            # Extract and abbreviate company name
            company_name_tag = soup.find("h1", class_="h1-seo")
            if company_name_tag:
                company_details["name"] = company_name_tag.text.strip()
                print(f"Company Name (abbreviated): {company_details['name']}")

            # Extract TIN
            tin_tag = soup.find("span", id="organizationTinValue")
            if tin_tag:
                company_details["TIN"] = tin_tag.text.strip()
                print(f"TIN: {company_details['TIN']}")

            # Extract and abbreviate CEO information
            ceo_section = soup.find("h5", string="Management information")
            if ceo_section:
                ceo_name_tag = ceo_section.find_next("a")
                if ceo_name_tag:
                    company_details["CEO"] = ceo_name_tag.text.strip()
                    print(f"CEO (abbreviated): {company_details['CEO']}")

            # Extract address
            address_section = soup.find("h5", string="Contact information")
            if address_section:
                address_row = address_section.find_next("div", class_="row").find_all("div", class_="row")[-1]
                address_tag = address_row.find("span")
                if address_tag:
                    address_parts = address_row.find_all("span")
                    if len(address_parts) > 1:
                        company_details["address"] = address_parts[1].text.strip()
                        print(f"Address: {company_details['address']}")

            # Extract and abbreviate founders
            founders = []
            founder_section = soup.find("h5", string="Founders")
            if founder_section:
                founder_rows = founder_section.find_next_sibling("div").find_all("div", class_="row")
                for row in founder_rows:
                    founder_name_tag = row.find("a")
                    if founder_name_tag:
                        founder_name = founder_name_tag.text.strip()
                        # Extract ownership percentage
                        ownership_text = row.get_text()
                        ownership_match = re.search(r'(\d+(?:\.\d+)?)%', ownership_text)
                        ownership_percentage = float(ownership_match.group(1)) if ownership_match else None
                        
                        founder = {
                            "owner": founder_name,
                            "isCompany": is_company_name(founder_name),
                            "ownershipPercentage": ownership_percentage
                        }
                        founders.append(founder)
                        print(f"Found Founder: {founder_name} ({ownership_percentage}%)")

            if founders:
                company_details["Founders"] = founders

            return company_details

        except requests.RequestException as e:
            print(f"Error fetching company details from orginfo: {e}")
        return None
    
    @staticmethod
    def apply_abbreviations(name: str) -> str:
        """Apply abbreviations to entity names."""
        if not name:
            return name

        # Replace full names with abbreviations
        for full_name, abbreviation in ENTITY_ABBREVIATIONS.items():
            name = re.sub(re.escape(full_name), abbreviation, name, flags=re.IGNORECASE)

        # Remove additional labels
        pattern = r'\b(?:' + '|'.join(map(re.escape, ENTITY_LABELS)) + r')\b'
        name = re.sub(pattern, '', name, flags=re.IGNORECASE).strip()

        # Clean up unnecessary characters
        name = re.sub(r'["\'/]', '', name)  # Remove quotes or slashes
        name = re.sub(r'\s+', ' ', name)  # Normalize spaces

        return name
    
    @staticmethod
    def apply_abbreviations(name: str) -> str:
        """Apply abbreviations to entity names."""
        if not name:
            return name

        # Replace full names with abbreviations
        for full_name, abbreviation in ENTITY_ABBREVIATIONS.items():
            name = re.sub(re.escape(full_name), abbreviation, name, flags=re.IGNORECASE)

        # Remove additional labels
        pattern = r'\b(?:' + '|'.join(map(re.escape, ENTITY_LABELS)) + r')\b'
        name = re.sub(pattern, '', name, flags=re.IGNORECASE).strip()

        # Clean up unnecessary characters
        name = re.sub(r'["\'/]', '', name)  # Remove quotes or slashes
        name = re.sub(r'\s+', ' ', name)  # Normalize spaces

        return name