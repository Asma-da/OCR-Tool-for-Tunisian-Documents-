import io
import cv2
import numpy as np
import re
from PIL import Image
import easyocr

# ========== LAZY LOADING - EasyOCR ==========
_reader_instance = None


def get_reader():
    global _reader_instance
    if _reader_instance is None:
        print("🔄 Loading EasyOCR models (Arabic + English)...")
        _reader_instance = easyocr.Reader(['ar', 'en'], gpu=False)
        print("✅ EasyOCR loaded!")
    return _reader_instance


# Arabic months
ARABIC_MONTHS = {
    "جانفي": "01", "فيفري": "02", "مارس": "03", "أفريل": "04",
    "ماي": "05", "جوان": "06", "جويلية": "07", "أوت": "08",
    "سبتمبر": "09", "أكتوبر": "10", "نوفمبر": "11", "ديسمبر": "12"
}

DOC_REQUIREMENTS = {
    "passport": {"min_width": 600, "min_height": 400},
    "cin": {"min_width": 500, "min_height": 300}
}


# ----- IMAGE QUALITY CHECK -----
def check_image_quality(img, doc_type, blur_threshold=100, brightness_threshold=(30, 240)):
    if isinstance(img, Image.Image):
        img = np.array(img)
    elif isinstance(img, bytes):
        img = np.array(Image.open(io.BytesIO(img)))

    if len(img.shape) == 3 and img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    h, w = img.shape[:2]
    req = DOC_REQUIREMENTS.get(doc_type, {"min_width": 600, "min_height": 400})
    if w < req["min_width"] or h < req["min_height"]:
        return False, f"❌ Resolution too low ({w}x{h})"

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    if blur_score < blur_threshold:
        return False, f"❌ Image too blurry (score: {blur_score:.2f})"

    mean_brightness = np.mean(gray)
    if mean_brightness < brightness_threshold[0]:
        return False, "❌ Image too dark"
    elif mean_brightness > brightness_threshold[1]:
        return True, "⚠️ Image bright, but usable"

    return True, "✅ Image quality acceptable"


# ----- OCR EXTRACTION WITH LAYOUT -----
def extract_text_with_layout(img):
    if isinstance(img, Image.Image):
        img = np.array(img)
    reader = get_reader()
    results = reader.readtext(img)
    lines = {}
    for bbox, text, conf in results:
        if conf > 0.2:
            center_y = sum(p[1] for p in bbox) / 4
            center_x = sum(p[0] for p in bbox) / 4
            key = round(center_y / 15) * 15
            lines.setdefault(key, []).append({"text": text, "x_pos": center_x, "conf": conf})
    sorted_lines = []
    for y in sorted(lines.keys()):
        items = sorted(lines[y], key=lambda x: x["x_pos"])
        line_text = " ".join(i["text"] for i in items)
        sorted_lines.append({"text": line_text, "y_pos": y, "items": items})
    return sorted_lines


# ----- PASSPORT FUNCTIONS -----
def normalize_passport_text(text):
    t = text.upper()
    replacements = {'$': 'S', '§': 'S', '5': 'S', 'O': '0', 'I': '1', 'Z': '2',
                    '₂': '2', '٢': '2', '٠': '0', '١': '1', '٣': '3', '٤': '4',
                    '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'}
    for bad, good in replacements.items():
        t = t.replace(bad, good)
    return t


def extract_passport_number(text):
    normalized = normalize_passport_text(text)
    patterns = [r'(?:TUN|2UN|٢UN)\s*([A-Z]\d{7})', r'\b([A-Z]\d{7})\b', r'\b([HS]\d{6,7})\b']
    for p in patterns:
        m = re.search(p, normalized)
        if m: return m.group(1)
    if 'PASSPORT' in text.upper() or 'جواز' in text:
        m = re.search(r'([SHsh$]\d{6,7})', text)
        if m: return m.group(1).upper().replace('$', 'S')
    return None


def structure_tunisian_passport_data(lines):
    structured_data = {}
    full_text = "\n".join([line["text"] for line in lines])

    # Passport number
    for line in lines:
        num = extract_passport_number(line["text"])
        if num:
            structured_data["Passport Number"] = num
            break

    # National ID
    m = re.search(r'\b(\d{8})\b', full_text)
    if m: structured_data["National ID"] = m.group(1)

    # Dates
    dates = re.findall(r'(\d{2}-\d{2}-\d{4})', full_text)
    if len(dates) >= 1: structured_data["Date of Birth"] = dates[0]
    if len(dates) >= 2: structured_data["Date of Issue"] = dates[1]
    if len(dates) >= 3: structured_data["Date of Expiry"] = dates[2]

    # Arabic Name
    for line in lines:
        arabic_words = re.findall(r'[\u0600-\u06FF]+', line["text"])
        if len(arabic_words) >= 3 and "جواز" not in line["text"]:
            structured_data["Arabic Name"] = line["text"]
            break

    # English Names
    family, given = None, None
    for i, line in enumerate(lines):
        t = line["text"].upper()
        if "SURNAME" in t and i + 1 < len(lines): family = lines[i + 1]["text"].replace(" ", "")
        if "GIVEN" in t and i + 1 < len(lines): given = lines[i + 1]["text"].replace(" ", " ")
    if family: structured_data["Family Name"] = family
    if given: structured_data["Given Names"] = given

    # Nationality
    if "TUNISIAN" in full_text.upper() or "تونسية" in full_text:
        structured_data["Nationality"] = "Tunisian"

    # Place of Birth
    pob = re.search(r'(TUNIS|FRANCE|PARIS|تونس|فرنسا)', full_text, re.I)
    if pob: structured_data["Place of Birth"] = pob.group().title()

    # Gender
    if re.search(r'\bM\b|ذكر', full_text):
        structured_data["Gender"] = "Male"
    elif re.search(r'\bF\b|أنثى', full_text):
        structured_data["Gender"] = "Female"

    # Issuing Authority
    if "TUNIS" in full_text.upper(): structured_data["Issuing Authority"] = "Tunis"

    # Profession
    for line in lines:
        if any(word in line["text"] for word in ["طبيب", "مهندس", "مشروع", "استاذ"]):
            structured_data["Profession"] = line["text"]
            break

    return structured_data, full_text


# ----- CIN FUNCTIONS -----
def parse_cin_front(lines):
    """Parse CIN front side data"""
    data = {}
    full_text = '\n'.join([line['text'] for line in lines])

    # National ID (8 digits)
    id_match = re.search(r'\b(\d{8})\b', full_text)
    if id_match:
        data['national_id'] = id_match.group(1)

    # Family Name & Given Name
    for i, line in enumerate(lines):
        text = line['text']
        if "اللقب" in text:
            surname = text.replace("اللقب", "").strip()
            if not surname and i + 1 < len(lines):
                surname = lines[i + 1]['text'].strip()
            data['family_name'] = surname

        if "الاسم" in text:
            given = text.replace("الاسم", "").strip()
            if not given and i + 1 < len(lines):
                given = lines[i + 1]['text'].strip()
            data['given_name'] = given

    # Father's Name
    father_match = re.search(r'بن\s+([^\n]+)', full_text)
    if father_match:
        data['father_name'] = father_match.group(1).strip()

    # Date of Birth
    dob_match = re.search(r'(\d{2})\s+(\w+)\s+(\d{4})', full_text)
    if dob_match:
        day, month_word, year = dob_match.groups()
        month = ARABIC_MONTHS.get(month_word, month_word)
        data['date_of_birth'] = f"{year}-{month}-{day}"

    # Place of Birth
    for i, line in enumerate(lines):
        if "تاريخ" in line['text'] and i + 1 < len(lines):
            place = lines[i + 1]['text']
            place = re.sub(r'[^ء-ي\sA-Za-z]', ' ', place)
            data['place_of_birth'] = ' '.join(place.split())
            break

    return data, full_text


def parse_cin_back(lines):
    """Parse CIN back side data"""
    data = {}
    full_text = '\n'.join([line['text'] for line in lines])

    # Address
    address_keywords = ["عنوان", "العنوان"]
    for i, line in enumerate(lines):
        if any(kw in line['text'] for kw in address_keywords):
            parts = []
            for j in range(i, min(i + 3, len(lines))):
                addr_line = lines[j]['text'].strip()
                if j == i:
                    for kw in address_keywords:
                        addr_line = addr_line.replace(kw, "")
                addr_line = addr_line.strip()
                if addr_line:
                    parts.append(addr_line)

            if parts:
                full_addr = ' '.join(parts)
                full_addr = re.sub(r'[^ء-ي\sA-Za-z0-9]', ' ', full_addr)
                data['address'] = ' '.join(full_addr.split())
            break

    # Profession
    prof_keywords = ["المهنة", "الصفة", "الوظيفة"]
    for line in lines:
        if any(kw in line['text'] for kw in prof_keywords):
            prof = line['text']
            for kw in prof_keywords:
                prof = prof.replace(kw, "")
            prof = prof.strip()
            if prof:
                data['profession'] = prof
            break

    # Issue Date
    date_match = re.search(r'(\d{2})\s+(\w+)\s+(\d{4})', full_text)
    if date_match:
        day, month_word, year = date_match.groups()
        month = ARABIC_MONTHS.get(month_word, month_word)
        data['date_of_issue'] = f"{year}-{month}-{day}"

    return data, full_text



# ----- FORMAT OUTPUT -----

def format_structured_data(data):
    lines = []
    if data:
        lines.append("📑 **Extracted Data:**")
        # Define a logical field order
        field_order = [
            "Passport Number", "National ID", "Date of Birth", "Date of Issue",
            "Date of Expiry", "Arabic Name", "Family Name", "Given Names",
            "Nationality", "Place of Birth", "Gender", "Profession", "Issuing Authority"
        ]
        # Add fields in order if they exist
        for key in field_order:
            if key in data:
                lines.append(f"- **{key}:** {data[key]}")
        # Add any other fields not in the order
        for key in data:
            if key not in field_order:
                lines.append(f"- **{key}:** {data[key]}")
    return "\n".join(lines)

# ----- UNIFIED PIPELINE -----
def pipeline(front_img=None, back_img=None, doc_type="cin"):
    quality_msgs=[]
    front_lines, back_lines=[], []

    if front_img:
        ok,msg=check_image_quality(front_img, doc_type)
        quality_msgs.append(f"Front: {msg}")
        if not ok: return {"success":False,"message":msg,"data":None,"raw_text":None}
        front_lines=extract_text_with_layout(front_img)

    if back_img:
        ok,msg=check_image_quality(back_img, doc_type)
        quality_msgs.append(f"Back: {msg}")
        if not ok: return {"success":False,"message":msg,"data":None,"raw_text":None}
        back_lines=extract_text_with_layout(back_img)

    if doc_type=="cin":
        front_data,_=parse_cin_front(front_lines)
        back_data,_=parse_cin_back(back_lines)
        structured={**front_data,**back_data}
        return {"success":True,"data":structured,"quality":quality_msgs}

    elif doc_type=="passport":
        structured_data, _ = structure_tunisian_passport_data(front_lines)
        formatted = format_structured_data(structured_data)
        return {"success": True, "data": structured_data, "message": formatted}

    else:
        return {"success":False,"message":f"Unknown document type: {doc_type}"}