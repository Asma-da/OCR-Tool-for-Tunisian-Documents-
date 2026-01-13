import fitz
import re
import base64
from typing import Optional
from io import BytesIO


def merge_lines(text: str) -> str:
    """Merge hyphenated lines and join paragraphs intelligently."""
    lines = text.split('\n')
    merged, buffer = [], ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if buffer:
                merged.append(buffer)
                buffer = ""
            continue

        is_section = re.match(r'^\d+(\.\d+)?\s+[A-ZÀ-Ý]', stripped)
        is_list = re.match(r'^(—|\-|•|\d+\.)\s', stripped)
        ends_sentence = buffer and buffer[-1] in '.!?:'

        if not buffer:
            buffer = stripped
        elif is_section or is_list:
            merged.append(buffer)
            buffer = stripped
        elif ends_sentence and stripped[0].isupper() and len(buffer) >= 60:
            merged.append(buffer)
            buffer = stripped
        else:
            buffer = buffer[:-1] + stripped if buffer.endswith('-') else buffer + " " + stripped

    if buffer:
        merged.append(buffer)
    return '\n\n'.join(merged)


def clean_text(text: str) -> str:
    """Clean extracted text."""
    text = re.sub(r'\s*\.{3,}\s*', ' ', text)
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+\d+\s*$', '', text, flags=re.MULTILINE)
    text = merge_lines(text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def extract_tables(doc) -> list:
    """Extract all tables from document."""
    all_tables = []
    for page_num, page in enumerate(doc):
        try:
            for table in page.find_tables().tables:
                raw = table.extract()
                if not raw:
                    continue
                cleaned = []
                for row in raw:
                    clean_row = [re.sub(r'\s+', ' ', re.sub(r'\n', ' ', str(c or ''))).strip() for c in row]
                    if any(clean_row):
                        cleaned.append(clean_row)
                if cleaned:
                    all_tables.append({
                        'page': page_num + 1,
                        'data': cleaned,
                        'bbox': table.bbox,
                        'y_pos': table.bbox[1]
                    })
        except Exception as e:
            print(f"Error extracting tables from page {page_num + 1}: {str(e)}")
            continue
    return all_tables


def extract_images(doc) -> list:
    """Extract all images from document and convert to base64."""
    all_images = []
    image_counter = 0

    for page_num, page in enumerate(doc):
        try:
            image_list = page.get_images(full=True)

            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    # Convert to base64
                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')

                    # Get image bounding box
                    try:
                        # FIX: Use get_image_rects instead of get_image_bbox
                        rects = page.get_image_rects(xref)
                        if rects:
                            bbox = rects[0]
                            y_pos = bbox[1]
                            bbox_tuple = tuple(bbox)
                        else:
                            bbox_tuple = None
                            y_pos = 0
                    except Exception as e:
                        print(f"Warning: Could not get bbox for image on page {page_num + 1}: {str(e)}")
                        bbox_tuple = None
                        y_pos = 0

                    image_counter += 1
                    all_images.append({
                        'page': page_num + 1,
                        'image_number': image_counter,
                        'format': image_ext,
                        'base64': f"data:image/{image_ext};base64,{image_base64}",
                        'bbox': bbox_tuple,
                        'y_pos': y_pos
                    })

                    print(f"✓ Extracted image {image_counter} from page {page_num + 1} (format: {image_ext})")

                except Exception as e:
                    print(f"Error extracting image {img_index} from page {page_num + 1}: {str(e)}")
                    continue

        except Exception as e:
            print(f"Error processing images on page {page_num + 1}: {str(e)}")
            continue

    print(f"Total images extracted: {image_counter}")
    return all_images


def get_text_blocks(page, table_bboxes: list, image_bboxes: list) -> list:
    """Extract text blocks excluding table and image regions."""
    blocks = page.get_text("dict")["blocks"]
    text_blocks = []

    for block in blocks:
        if block.get("type") != 0:
            continue
        bbox = block["bbox"]

        # Check if text overlaps with tables
        in_table = any(
            bbox[1] >= tb[1] - 10 and bbox[3] <= tb[3] + 10 and
            bbox[0] >= tb[0] - 10 and bbox[2] <= tb[2] + 10
            for tb in table_bboxes
        )

        # Check if text overlaps with images
        in_image = any(
            ib and bbox[1] >= ib[1] - 10 and bbox[3] <= ib[3] + 10 and
            bbox[0] >= ib[0] - 10 and bbox[2] <= ib[2] + 10
            for ib in image_bboxes if ib
        )

        if not in_table and not in_image:
            text = "".join(
                span.get("text", "") + "\n"
                for line in block.get("lines", [])
                for span in line.get("spans", [])
            )
            if text.strip():
                text_blocks.append({'text': text.strip(), 'y_pos': bbox[1]})
    return text_blocks


def extract_pdf(file_bytes: bytes, filename: str) -> dict:
    """Main extraction function - returns structured data with images."""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        return {"error": f"Failed to open PDF: {str(e)}"}

    result = {
        "filename": filename,
        "total_pages": len(doc),
        "pages": [],
        "tables_count": 0,
        "images_count": 0,
        "full_text": ""
    }

    try:
        # Extract all tables and images
        print(f"\n{'=' * 50}")
        print(f"Processing PDF: {filename}")
        print(f"Total pages: {len(doc)}")
        print(f"{'=' * 50}\n")

        all_tables = extract_tables(doc)
        print(f"Tables found: {len(all_tables)}")

        all_images = extract_images(doc)
        print(f"Images found: {len(all_images)}")

        # Organize by page
        page_tables = {}
        for t in all_tables:
            page_tables.setdefault(t['page'], []).append(t)

        page_images = {}
        for img in all_images:
            page_images.setdefault(img['page'], []).append(img)

        full_text_parts = []
        table_counter = 0
        image_counter = 0

        for page_num, page in enumerate(doc):
            current_page = page_num + 1
            tables_on_page = page_tables.get(current_page, [])
            images_on_page = page_images.get(current_page, [])

            table_bboxes = [t['bbox'] for t in tables_on_page]
            image_bboxes = [img['bbox'] for img in images_on_page]

            text_blocks = get_text_blocks(page, table_bboxes, image_bboxes)

            # Merge content by position (text, tables, images)
            content = [{'type': 'text', 'y_pos': tb['y_pos'], 'content': tb['text']} for tb in text_blocks]
            content += [{'type': 'table', 'y_pos': t['y_pos'], 'data': t['data']} for t in tables_on_page]
            content += [{'type': 'image', 'y_pos': img['y_pos'], 'data': img} for img in images_on_page]
            content.sort(key=lambda x: x['y_pos'])

            page_data = {"page_number": current_page, "content": []}

            for item in content:
                if item['type'] == 'text':
                    cleaned = clean_text(item['content'])
                    if cleaned:
                        page_data["content"].append({"type": "text", "value": cleaned})
                        full_text_parts.append(cleaned)

                elif item['type'] == 'table':
                    table_counter += 1
                    page_data["content"].append({
                        "type": "table",
                        "table_number": table_counter,
                        "headers": item['data'][0] if item['data'] else [],
                        "rows": item['data'][1:] if len(item['data']) > 1 else []
                    })

                elif item['type'] == 'image':
                    image_counter += 1
                    page_data["content"].append({
                        "type": "image",
                        "image_number": image_counter,
                        "format": item['data']['format'],
                        "base64": item['data']['base64']
                    })

            result["pages"].append(page_data)
            print(
                f"Page {current_page}: {len(text_blocks)} text blocks, {len(tables_on_page)} tables, {len(images_on_page)} images")

        result["tables_count"] = table_counter
        result["images_count"] = image_counter
        result["full_text"] = "\n\n".join(full_text_parts)

        print(f"\n{'=' * 50}")
        print(f"Extraction complete!")
        print(f"Total tables: {table_counter}")
        print(f"Total images: {image_counter}")
        print(f"{'=' * 50}\n")

    except Exception as e:
        print(f"Error during extraction: {str(e)}")
        import traceback
        traceback.print_exc()
        result["error"] = str(e)
    finally:
        doc.close()

    return result