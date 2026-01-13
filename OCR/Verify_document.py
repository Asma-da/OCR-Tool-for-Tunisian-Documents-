"""
Document Verification Module
Validates extracted OCR data for authenticity
"""
import re
from datetime import datetime
from typing import Dict, Any, Optional

import PyPDF2
from typing import Dict, Any


def verify_pdf_document(pdf_path: str) -> Dict[str, Any]:
    """
    Verify PDF document structure and integrity
    Returns format matching verify_cin() and verify_passport()

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary with overall_score, is_authentic, confidence_level, and checks
    """
    checks = {}
    total_score = 0
    max_score = 0

    try:
        with open(pdf_path, 'rb') as f:
            # 1. PDF Header Validation
            max_score += 20
            header = f.read(8)
            f.seek(0)
            if header.startswith(b'%PDF-'):
                checks['pdf_header'] = {
                    "passed": True,
                    "score": 20,
                    "details": "Valid PDF header"
                }
                total_score += 20
            else:
                checks['pdf_header'] = {
                    "passed": False,
                    "score": 0,
                    "details": "Invalid PDF header"
                }

            reader = PyPDF2.PdfReader(f)

            # 2. Encryption Check
            max_score += 15
            if not reader.is_encrypted:
                checks['encryption'] = {
                    "passed": True,
                    "score": 15,
                    "details": "Document is not encrypted"
                }
                total_score += 15
            else:
                checks['encryption'] = {
                    "passed": False,
                    "score": 0,
                    "details": "Document is encrypted (suspicious)"
                }



            # 4. File Size Check
            max_score += 10
            f.seek(0, 2)
            size_mb = f.tell() / (1024 * 1024)
            if size_mb <= 10:
                checks['file_size'] = {
                    "passed": True,
                    "score": 10,
                    "details": f"Reasonable file size: {round(size_mb, 2)} MB"
                }
                total_score += 10
            else:
                checks['file_size'] = {
                    "passed": False,
                    "score": 0,
                    "details": f"Unusually large file: {round(size_mb, 2)} MB"
                }

            # 5. Metadata Check
            max_score += 20
            metadata = reader.metadata
            if metadata:
                creator = metadata.get('/Creator', 'Unknown')
                suspicious_tools = ['photoshop', 'gimp', 'paint', 'canva', 'pixlr']

                if not any(sus in creator.lower() for sus in suspicious_tools):
                    checks['metadata'] = {
                        "passed": True,
                        "score": 20,
                        "details": f"Creator software appears legitimate: {creator}"
                    }
                    total_score += 20
                else:
                    checks['metadata'] = {
                        "passed": False,
                        "score": 0,
                        "details": f"Suspicious creator software detected: {creator}"
                    }
            else:
                checks['metadata'] = {
                    "passed": False,
                    "score": 10,
                    "details": "No metadata found (partial credit)"
                }
                total_score += 10

            # 6. Document Modification Check
            max_score += 20
            if metadata:
                creation_date = metadata.get('/CreationDate', 'Unknown')
                mod_date = metadata.get('/ModDate', 'Unknown')

                if creation_date == mod_date or mod_date == 'Unknown':
                    checks['modification'] = {
                        "passed": True,
                        "score": 20,
                        "details": "No modifications detected"
                    }
                    total_score += 20
                else:
                    checks['modification'] = {
                        "passed": False,
                        "score": 10,
                        "details": "Document was modified after creation (partial credit)"
                    }
                    total_score += 10
            else:
                checks['modification'] = {
                    "passed": True,
                    "score": 20,
                    "details": "Cannot verify (no metadata)"
                }
                total_score += 20

    except Exception as e:
        return {
            "overall_score": 0,
            "is_authentic": False,
            "confidence_level": "low",
            "checks": {
                "error": {
                    "passed": False,
                    "score": 0,
                    "details": f"PDF verification failed: {str(e)}"
                }
            },
            "doc_type": "pdf"
        }

    # Calculate overall score as percentage
    overall_score = int((total_score / max_score) * 100) if max_score > 0 else 0

    # Determine authenticity and confidence level
    is_authentic = overall_score >= 60
    if overall_score >= 80:
        confidence_level = "high"
    elif overall_score >= 60:
        confidence_level = "medium"
    else:
        confidence_level = "low"

    return {
        "overall_score": overall_score,
        "is_authentic": is_authentic,
        "confidence_level": confidence_level,
        "checks": checks,
        "doc_type": "pdf"
    }


def parse_date(date_str: str, formats: list = None) -> Optional[datetime]:
    """
    Try to parse a date string with multiple format options

    Args:
        date_str: The date string to parse
        formats: List of date formats to try (default: common formats)

    Returns:
        datetime object if successful, None otherwise
    """
    if not date_str:
        return None

    if formats is None:
        formats = [
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%d/%m/%Y',
            '%Y/%m/%d',
            '%d.%m.%Y',
            '%Y.%m.%d'
        ]

    for fmt in formats:
        try:
            return datetime.strptime(str(date_str).strip(), fmt)
        except (ValueError, AttributeError):
            continue

    return None


def verify_document(extracted_data: Dict[str, Any], doc_type: str = "cin") -> Dict[str, Any]:
    """
    Verify document authenticity based on extracted OCR data

    Args:
        extracted_data: Dictionary containing extracted OCR fields
        doc_type: Type of document ("cin" or "passport")

    Returns:
        Dictionary containing verification results with overall score and detailed checks
    """
    # Handle None or empty data
    if not extracted_data or not isinstance(extracted_data, dict):
        return {
            "overall_score": 0,
            "is_authentic": False,
            "confidence_level": "low",
            "checks": {
                "data_validation": {
                    "passed": False,
                    "score": 0,
                    "details": "No data extracted or invalid data format"
                }
            },
            "doc_type": doc_type,
            "error": "Invalid or missing extracted data"
        }

    try:
        if doc_type == "cin":
            verification_results = verify_cin(extracted_data)
        elif doc_type == "passport":
            verification_results = verify_passport(extracted_data)
        else:
            verification_results = {
                "overall_score": 0,
                "is_authentic": False,
                "confidence_level": "low",
                "checks": {},
                "doc_type": doc_type,
                "error": f"Unknown document type: {doc_type}"
            }
    except Exception as e:
        verification_results = {
            "overall_score": 0,
            "is_authentic": False,
            "confidence_level": "low",
            "checks": {},
            "doc_type": doc_type,
            "error": f"Verification failed: {str(e)}"
        }

    return verification_results


def verify_cin(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify Tunisian CIN (Carte d'Identité Nationale)
    """
    checks = {}
    total_score = 0
    max_score = 0

    # 1. National ID Format Check (8 digits)
    max_score += 20
    national_id = str(data.get('national_id', '')).strip()
    if national_id and re.match(r'^\d{8}$', national_id):
        checks['national_id_format'] = {
            "passed": True,
            "score": 20,
            "details": "National ID format is valid (8 digits)"
        }
        total_score += 20
    else:
        checks['national_id_format'] = {
            "passed": False,
            "score": 0,
            "details": f"Invalid National ID format (must be 8 digits, got: '{national_id}')"
        }

    # 2. Date of Birth Validation
    max_score += 15
    dob = data.get('date_of_birth', '')
    dob_date = parse_date(dob)

    if dob_date:
        age = (datetime.now() - dob_date).days // 365
        if 0 <= age <= 120:
            checks['date_of_birth'] = {
                "passed": True,
                "score": 15,
                "details": f"Valid date of birth (Age: {age} years)"
            }
            total_score += 15
        else:
            checks['date_of_birth'] = {
                "passed": False,
                "score": 0,
                "details": f"Suspicious age: {age} years"
            }
    else:
        checks['date_of_birth'] = {
            "passed": False,
            "score": 0,
            "details": f"Invalid or missing date of birth: '{dob}'"
        }

    # 3. Date of Issue Validation
    max_score += 15
    doi = data.get('date_of_issue', '')
    doi_date = parse_date(doi)

    if doi_date:
        if doi_date <= datetime.now():
            checks['date_of_issue'] = {
                "passed": True,
                "score": 15,
                "details": "Valid issue date"
            }
            total_score += 15
        else:
            checks['date_of_issue'] = {
                "passed": False,
                "score": 0,
                "details": "Issue date is in the future"
            }
    else:
        checks['date_of_issue'] = {
            "passed": False,
            "score": 0,
            "details": f"Invalid or missing issue date: '{doi}'"
        }

    # 4. Name Validation (Arabic characters)
    max_score += 15
    given_name = str(data.get('given_name', '')).strip()
    family_name = str(data.get('family_name', '')).strip()

    if given_name and family_name:
        has_arabic_given = bool(re.search(r'[\u0600-\u06FF]', given_name))
        has_arabic_family = bool(re.search(r'[\u0600-\u06FF]', family_name))

        if has_arabic_given and has_arabic_family:
            checks['names'] = {
                "passed": True,
                "score": 15,
                "details": "Names contain Arabic characters"
            }
            total_score += 15
        else:
            checks['names'] = {
                "passed": False,
                "score": 5,
                "details": "Names should contain Arabic characters (partial credit)"
            }
            total_score += 5
    else:
        checks['names'] = {
            "passed": False,
            "score": 0,
            "details": f"Name fields missing (given: '{given_name}', family: '{family_name}')"
        }

    # 5. Place of Birth (Arabic)
    max_score += 10
    place_of_birth = str(data.get('place_of_birth', '')).strip()
    if place_of_birth and re.search(r'[\u0600-\u06FF]', place_of_birth):
        checks['place_of_birth'] = {
            "passed": True,
            "score": 10,
            "details": "Valid place of birth"
        }
        total_score += 10
    else:
        checks['place_of_birth'] = {
            "passed": False,
            "score": 0,
            "details": f"Place of birth missing or invalid: '{place_of_birth}'"
        }

    # 6. Address (if available)
    max_score += 10
    address = str(data.get('address', '')).strip()
    if address and re.search(r'[\u0600-\u06FF]', address):
        checks['address'] = {
            "passed": True,
            "score": 10,
            "details": "Valid address format"
        }
        total_score += 10
    else:
        checks['address'] = {
            "passed": False,
            "score": 0,
            "details": "Address missing or invalid (optional field)"
        }

    # 7. Data Completeness
    max_score += 15
    required_fields = ['national_id', 'given_name', 'family_name', 'date_of_birth']
    missing_fields = [field for field in required_fields if not str(data.get(field, '')).strip()]

    if not missing_fields:
        checks['completeness'] = {
            "passed": True,
            "score": 15,
            "details": "All required fields present"
        }
        total_score += 15
    else:
        checks['completeness'] = {
            "passed": False,
            "score": 0,
            "details": f"Missing fields: {', '.join(missing_fields)}"
        }

    # Calculate overall score as percentage
    overall_score = int((total_score / max_score) * 100) if max_score > 0 else 0

    # Determine authenticity and confidence level
    is_authentic = overall_score >= 60
    if overall_score >= 80:
        confidence_level = "high"
    elif overall_score >= 60:
        confidence_level = "medium"
    else:
        confidence_level = "low"

    return {
        "overall_score": overall_score,
        "is_authentic": is_authentic,
        "confidence_level": confidence_level,
        "checks": checks,
        "doc_type": "cin"
    }


def verify_passport(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify Tunisian Passport
    """
    checks = {}
    total_score = 0
    max_score = 0

    # 1. Passport Number Format Check
    max_score += 20
    passport_number = str(data.get('Passport Number', '')).strip()
    if passport_number and re.match(r'^[A-Z]\d{6,8}$', passport_number.upper()):
        checks['passport_number_format'] = {
            "passed": True,
            "score": 20,
            "details": "Valid passport number format"
        }
        total_score += 20
    else:
        checks['passport_number_format'] = {
            "passed": False,
            "score": 0,
            "details": f"Invalid passport number format: '{passport_number}'"
        }

    # 2. National ID Check
    max_score += 15
    national_id = str(data.get('National ID', '')).strip()
    if national_id and re.match(r'^\d{8}$', national_id):
        checks['national_id'] = {
            "passed": True,
            "score": 15,
            "details": "Valid national ID"
        }
        total_score += 15
    else:
        checks['national_id'] = {
            "passed": False,
            "score": 0,
            "details": f"National ID missing or invalid: '{national_id}'"
        }

    # 3. Date Validations
    max_score += 25
    dob = data.get('Date of Birth', '')
    doi = data.get('Date of Issue', '')
    doe = data.get('Date of Expiry', '')

    dob_date = parse_date(dob)
    doi_date = parse_date(doi)
    doe_date = parse_date(doe)

    date_score = 0
    if all([dob_date, doi_date, doe_date]):
        if doi_date < doe_date and dob_date < doi_date:
            date_score = 25
            checks['dates'] = {
                "passed": True,
                "score": 25,
                "details": "All dates are valid and in correct order"
            }
        else:
            checks['dates'] = {
                "passed": False,
                "score": 0,
                "details": "Date logic error (birth < issue < expiry)"
            }
    else:
        missing = []
        if not dob_date: missing.append(f"birth: '{dob}'")
        if not doi_date: missing.append(f"issue: '{doi}'")
        if not doe_date: missing.append(f"expiry: '{doe}'")

        checks['dates'] = {
            "passed": False,
            "score": 0,
            "details": f"Invalid or missing dates: {', '.join(missing)}"
        }
    total_score += date_score

    # 4. Arabic Name Check
    max_score += 20
    arabic_name = str(data.get('Arabic Name', '')).strip()
    if arabic_name and re.search(r'[\u0600-\u06FF]', arabic_name):
        checks['full_name_ar'] = {
            "passed": True,
            "score": 20,
            "details": "Valid Arabic name"
        }
        total_score += 20
    else:
        checks['Arabic Name'] = {
            "passed": False,
            "score": 0,
            "details": f"Arabic name missing or invalid: '{arabic_name}'"
        }

    # 5. Data Completeness
    max_score += 20
    required_fields = ['Passport Number', 'National ID', 'Date of Birth', 'Arabic Name']
    missing_fields = [field for field in required_fields if not str(data.get(field, '')).strip()]

    if not missing_fields:
        checks['completeness'] = {
            "passed": True,
            "score": 20,
            "details": "All required fields present"
        }
        total_score += 20
    else:
        checks['completeness'] = {
            "passed": False,
            "score": 0,
            "details": f"Missing fields: {', '.join(missing_fields)}"
        }

    # Calculate overall score
    overall_score = int((total_score / max_score) * 100) if max_score > 0 else 0

    # Determine authenticity
    is_authentic = overall_score >= 60
    if overall_score >= 80:
        confidence_level = "high"
    elif overall_score >= 60:
        confidence_level = "medium"
    else:
        confidence_level = "low"

    return {
        "overall_score": overall_score,
        "is_authentic": is_authentic,
        "confidence_level": confidence_level,
        "checks": checks,
        "doc_type": "passport"
    }