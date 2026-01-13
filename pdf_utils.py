from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from io import BytesIO
from PIL import Image
import tempfile


def render_pdf_inline(content_list):
    """
    Render text and images inline in a PDF preserving order.

    content_list: [{'type': 'text', 'value': ...}, {'type': 'image', 'image_bytes': ...}]
    Returns: BytesIO with PDF data
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 20 * mm
    y_cursor = height - margin

    for item in content_list:
        if item['type'] == 'text':
            lines = item['value'].split("\n")
            c.setFont("Helvetica", 10)
            for line in lines:
                if y_cursor < margin:
                    c.showPage()
                    y_cursor = height - margin
                    c.setFont("Helvetica", 10)
                c.drawString(margin, y_cursor, line)
                y_cursor -= 12

        elif item['type'] == 'image':
            try:
                pil_img = Image.open(BytesIO(item['image_bytes']))
                max_width = width - 2 * margin
                max_height = y_cursor - margin
                pil_img.thumbnail((max_width, max_height))

                temp_img_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                pil_img.save(temp_img_file.name)
                c.drawImage(temp_img_file.name, margin, y_cursor - pil_img.height,
                            width=pil_img.width, height=pil_img.height)
                y_cursor -= pil_img.height + 10
                temp_img_file.close()
            except Exception as e:
                print(f"⚠ Could not render image: {e}")
                continue

    c.save()
    buffer.seek(0)
    return buffer
