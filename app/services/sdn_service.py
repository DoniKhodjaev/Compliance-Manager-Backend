import json
import os
import requests
import xml.etree.ElementTree as ET
import logging
from unidecode import unidecode
from datetime import datetime
import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DATA_DIR = os.path.abspath("./data")
XML_FILE_PATH = os.path.join(DATA_DIR, "sdn.xml")
CACHE_FILE_PATH = os.path.join(DATA_DIR, "sdn_cache.json")
SDN_URL = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML"
CACHE_EXPIRY_HOURS = 24

class SDNService:
    CACHE_FILE_PATH = os.path.join(DATA_DIR, "sdn_cache.json")
    @staticmethod
    def calculate_similarity(str1: str, str2: str) -> float:
        """Calculate similarity between two strings."""
        s1 = SDNService.normalize_string(str1)
        s2 = SDNService.normalize_string(str2)
        
        if s1 == s2:
            return 1.0
        if not s1 or not s2:
            return 0.0

        words1 = set(s1.split())
        words2 = set(s2.split())
        
        shorter_set = words1 if len(words1) < len(words2) else words2
        longer_set = words2 if len(words1) < len(words2) else words1
        
        matching_words = sum(1 for word in shorter_set 
                           if any(w.find(word) != -1 or word.find(w) != -1 
                                 for w in longer_set))
        
        return matching_words / len(shorter_set)

    @staticmethod
    def normalize_string(s: str) -> str:
        """Normalize string by removing special characters and extra spaces."""
        s = unidecode(s)
        return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', s.lower())).strip()

    @staticmethod
    def is_cache_valid() -> bool:
        """Check if the cache file is valid and not expired."""
        if not os.path.exists(CACHE_FILE_PATH):
            return False
            
        cache_mtime = datetime.fromtimestamp(os.path.getmtime(CACHE_FILE_PATH))
        age_hours = (datetime.now() - cache_mtime).total_seconds() / 3600
        
        return age_hours < CACHE_EXPIRY_HOURS

    @staticmethod
    def download_sdn_file() -> Dict[str, Any]:
        """Download the SDN XML file with error handling and validation."""
        try:
            logger.info("Downloading SDN file...")
            response = requests.get(SDN_URL, timeout=10)
            response.raise_for_status()

            if not response.content.strip().startswith(b'<?xml'):
                raise ValueError("Downloaded content is not valid XML")

            os.makedirs(os.path.dirname(XML_FILE_PATH), exist_ok=True)
            with open(XML_FILE_PATH, 'wb') as file:
                file.write(response.content)
            logger.info("SDN file downloaded successfully")

            if os.path.exists(CACHE_FILE_PATH):
                os.remove(CACHE_FILE_PATH)
                logger.info("Cache cleared")

            return {"status": "success", "message": "SDN list updated successfully"}
        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            return {"status": "error", "message": str(e)}

    @staticmethod
    def parse_xml_to_json():
        """Parses the XML file and saves data to JSON cache."""
        try:
            print("Parsing XML file to update SDN list...")
            
            # Ensure the directory for the cache file exists
            os.makedirs(os.path.dirname(CACHE_FILE_PATH), exist_ok=True)
            
            tree = ET.parse(XML_FILE_PATH)
            root = tree.getroot()

            namespace = ''
            if '}' in root.tag:
                namespace = root.tag.split('}')[0] + '}'

            sdn_entries = []
            for entry in root.findall(f".//{namespace}sdnEntry"):
                sdn_entry = {}
                sdn_entry['uid'] = entry.find(f"{namespace}uid").text if entry.find(f"{namespace}uid") is not None else ""

                # Extract full name by combining firstName, middleName, and lastName
                first_name = entry.find(f"{namespace}firstName").text if entry.find(f"{namespace}firstName") is not None else ""
                middle_name = entry.find(f"{namespace}middleName").text if entry.find(f"{namespace}middleName") is not None else ""
                last_name = entry.find(f"{namespace}lastName").text if entry.find(f"{namespace}lastName") is not None else ""
                full_name = " ".join([first_name, middle_name, last_name]).strip()
                sdn_entry['name'] = full_name

                sdn_entry['type'] = entry.find(f"{namespace}sdnType").text if entry.find(f"{namespace}sdnType") is not None else ""
                
                # AKA List (Alternate Names)
                aka_list = entry.find(f"{namespace}akaList")
                if aka_list is not None:
                    sdn_entry['aka_names'] = [
                        aka.find(f"{namespace}lastName").text for aka in aka_list.findall(f"{namespace}aka") 
                        if aka.find(f"{namespace}lastName") is not None
                    ]

                # Address List
                address_list = entry.find(f"{namespace}addressList")
                if address_list is not None:
                    addresses = []
                    for address in address_list.findall(f"{namespace}address"):
                        city = address.find(f"{namespace}city").text if address.find(f"{namespace}city") is not None else ""
                        country = address.find(f"{namespace}country").text if address.find(f"{namespace}country") is not None else ""
                        addresses.append({"city": city, "country": country})
                    sdn_entry['addresses'] = addresses

                # Program List (Sanctions programs)
                program_list = entry.find(f"{namespace}programList")
                if program_list is not None:
                    sdn_entry['programs'] = [
                        program.text for program in program_list.findall(f"{namespace}program") if program is not None
                    ]

                # Date of Birth
                dob_feature = entry.find(f"{namespace}dateOfBirthList")
                if dob_feature is not None:
                    dob_item = dob_feature.find(f"{namespace}dateOfBirthItem/{namespace}dateOfBirth")
                    sdn_entry['date_of_birth'] = dob_item.text if dob_item is not None else ""

                # ID List with idType and idNumber
                id_list = entry.find(f"{namespace}idList")  # Ensure lowercase 'idList' matches XML structure
                if id_list is not None:
                    ids = []
                    for id_item in id_list.findall(f"{namespace}id"):
                        id_type = id_item.find(f"{namespace}idType").text if id_item.find(f"{namespace}idType") is not None else ""
                        id_number = id_item.find(f"{namespace}idNumber").text if id_item.find(f"{namespace}idNumber") is not None else ""
                        ids.append({"id_type": id_type, "id_number": id_number})
                    sdn_entry['ids'] = ids

                # Remarks
                remarks = entry.find(f"{namespace}remarks")
                sdn_entry['remarks'] = remarks.text if remarks is not None else ""

                sdn_entries.append(sdn_entry)

            # Save the data to a JSON cache file
            print("Attempting to write to JSON cache file.")
            with open(CACHE_FILE_PATH, 'w') as cache_file:
                json.dump(sdn_entries, cache_file)
            print("Successfully wrote to JSON cache file.")

            return sdn_entries
        except ET.ParseError as e:
            print(f"XML parsing error: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error: {e}")
            return []

    @staticmethod
    def search_sdn(query: str) -> Dict[str, Any]:
        """Search SDN list with specific criteria."""
        try:
            query = query.lower().strip()
            if not query:
                return {"average_match_score": 0.0, "results": []}

            query = re.sub(r'\(.*?\)', '', query).replace('"', '').strip()

            if SDNService.is_cache_valid():
                with open(CACHE_FILE_PATH, 'r', encoding='utf-8') as cache_file:
                    sdn_entries = json.load(cache_file)
            else:
                sdn_entries = SDNService.parse_xml_to_json()

            results = []
            total_score = 0
            match_count = 0
            has_exact_match = False

            query_tokens = [unidecode(token) for token in query.split()]

            for entry in sdn_entries:
                match_result = SDNService._check_entry_match(entry, query, query_tokens)
                if match_result["is_match"]:
                    results.append(match_result["entry_data"])
                    total_score += match_result["score"]
                    match_count += 1
                    if match_result["is_exact"]:
                        has_exact_match = True

            average_match_score = 1.0 if has_exact_match else (
                total_score / match_count if match_count > 0 else 0.0
            )

            results.sort(key=lambda x: x['match_score'], reverse=True)
            return {"average_match_score": average_match_score, "results": results}

        except Exception as e:
            logger.error(f"Error in search_sdn: {str(e)}")
            raise

    @staticmethod
    def _check_entry_match(entry: Dict, query: str, query_tokens: List[str]) -> Dict:
        """Helper method to check if an entry matches the search criteria."""
        THRESHOLD = 0.85
        ALLOWED_ID_TYPES = {"Tax ID No.", "SWIFT/BIC", "BIK (RU)"}

        entry_name = unidecode(entry['name'].lower())
        aka_names = [unidecode(aka.lower()) for aka in entry.get('aka_names', [])]
        ids = [id_info for id_info in entry.get('ids', [])
               if id_info['id_type'] in ALLOWED_ID_TYPES]

        # Calculate similarity scores
        primary_score = SequenceMatcher(None, query, entry_name).ratio()
        aka_scores = [SequenceMatcher(None, query, aka).ratio() for aka in aka_names]
        best_score = max([primary_score] + aka_scores)

        is_exact = (
            best_score == 1.0 or
            all(token in entry_name for token in query_tokens) or
            any(all(token in aka for token in query_tokens) for aka in aka_names) or
            any(all(token in unidecode(id_info['id_number'].lower()) 
                for token in query_tokens) for id_info in ids)
        )

        if best_score >= THRESHOLD or is_exact:
            return {
                "is_match": True,
                "is_exact": is_exact,
                "score": 1.0 if is_exact else best_score,
                "entry_data": {
                    'name': entry['name'],
                    'aka_names': entry.get('aka_names', []),
                    'ids': ids,
                    'match_score': 1.0 if is_exact else best_score
                }
            }

        return {"is_match": False}


