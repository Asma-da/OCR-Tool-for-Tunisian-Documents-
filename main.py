import base64
from pydantic import BaseModel
from typing import Dict, Any, Optional

from bson import ObjectId
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse , StreamingResponse, JSONResponse
import os
from io import BytesIO

from PIL import Image
from datetime import datetime

from starlette.responses import RedirectResponse
import uvicorn
import tempfile
from OCR.pdf_extractor import extract_pdf
from auth_utils import get_current_user, hash_password
from database import get_collection
from pdf_utils import render_pdf_inline
from schemas import OCRResponse
from OCR.EasyOCR import pipeline
from OCR.Verify_document import verify_document , verify_pdf_document
from config import Config
import auth_routes
import pandas as pd

templates = Jinja2Templates(directory="templates")
app = FastAPI(title="OCR API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth routes
app.include_router(auth_routes.router)

# Collections
users_col = get_collection("users")
ocr_col = get_collection("uploads")

# Create necessary folders
os.makedirs(Config.TEMP_FOLDER, exist_ok=True)
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

# Mount static files if you have any
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.post("/ocr/upload/pdf")
async def upload_pdf(
        file: UploadFile = File(...),
        current_user: dict = Depends(get_current_user)
):
    """Upload PDF for text, table, and image extraction (stored as a single record)"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    temp_pdf_path = None

    try:
        # Read file bytes
        file_bytes = await file.read()

        # Save to temporary file for PDF verification
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_pdf_path = temp_file.name
            temp_file.write(file_bytes)

        # Extract text/data/images from PDF
        extracted = extract_pdf(file_bytes, file.filename)

        if extracted.get("error"):
            return {
                "text": "",
                "tables": [],
                "images": [],
                "verification": {"error": extracted.get("error")},
                "error": extracted.get("error")
            }

        # Flatten all page content into single arrays
        all_text = []
        all_tables = []
        all_images = []

        for page in extracted.get("pages", []):
            for item in page.get("content", []):
                if item["type"] == "text":
                    all_text.append(item["value"])
                elif item["type"] == "table":
                    all_tables.append(item)
                elif item["type"] == "image":
                    all_images.append(item)

        # Merge text into one string
        merged_text = "\n\n".join(all_text)

        # Verify PDF
        verification_result = verify_pdf_document(temp_pdf_path)

        # Save to database
        record_id = None
        try:
            ocr_record = {
                "user_id": current_user["_id"],
                "username": current_user["username"],
                "doc_type": "pdf",
                "filename": file.filename,
                "text": merged_text,
                "tables": all_tables,
                "images": all_images,
                "verification": verification_result,
                "timestamp": datetime.utcnow()
            }

            result = ocr_col.insert_one(ocr_record)
            record_id = str(result.inserted_id)
            print(f" Saved to database with ID: {record_id}")
        except Exception as db_error:
            print(f" Warning: Could not save to database (likely too large): {db_error}")
            record_id = None

        # Return response
        return {
            "success": True,
            "message": f"PDF processed successfully. Found {len(all_tables)} tables and {len(all_images)} images.",
            "text": merged_text,
            "tables": all_tables,
            "images": all_images,
            "verification": verification_result,
            "record_id": record_id
        }

    except Exception as e:
        import traceback
        print(f" Error processing PDF: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")

    finally:
        # Clean up temporary file
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                os.unlink(temp_pdf_path)
            except Exception as cleanup_error:
                print(f"Warning: Could not delete temporary file: {cleanup_error}")


# -------------------- CIN UPLOAD ROUTE --------------------
@app.post("/ocr/upload/cin")
async def upload_cin(
        front: UploadFile = File(...),
        back: UploadFile = File(None),
        current_user: dict = Depends(get_current_user)
):
    """Upload CIN front and optionally back image for OCR processing"""
    try:
        # Process front image
        front_img = Image.open(front.file)

        # Process back image if provided
        back_img = None
        if back and back.filename:
            back_img = Image.open(back.file)

        # Run OCR pipeline
        ocr_result = pipeline(
            front_img=front_img,
            back_img=back_img,
            doc_type="cin"
        )

        # Check for OCR errors
        if ocr_result.get("error"):
            return {
                "extracted_data": {},
                "quality": ocr_result.get("quality", []),
                "verification": [ocr_result.get("error")],
                "error": ocr_result.get("error")
            }

        # Use YOUR existing verification function
        verification_result = verify_document(
            extracted_data=ocr_result.get("data", {}),
            doc_type="cin"
        )

        # Save to database
        ocr_record = {
            "user_id": current_user["_id"],
            "username": current_user["username"],
            "doc_type": "cin",
            "front_filename": front.filename,
            "back_filename": back.filename if back else None,
            "extracted_data": ocr_result.get("data", {}),
            "quality_check": ocr_result.get("quality", []),
            "verification": verification_result,
            "timestamp": datetime.utcnow()
        }
        result = ocr_col.insert_one(ocr_record)
        record_id = str(result.inserted_id)

        return {
            "extracted_data": ocr_result.get("data", {}),
            "quality": ocr_result.get("quality", []),
            "verification": verification_result,
            "record_id": record_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")


# -------------------- PASSPORT UPLOAD ROUTE --------------------
@app.post("/ocr/upload/passport")
async def upload_passport(
        file: UploadFile = File(...),
        current_user: dict = Depends(get_current_user)
):
    """Upload passport image for OCR processing"""
    try:
        # Process image
        img = Image.open(file.file)

        # Run OCR pipeline
        ocr_result = pipeline(
            front_img=img,
            doc_type="passport"
        )

        # Check for OCR errors
        if ocr_result.get("error"):
            return {
                "extracted_data": {},
                "quality": ocr_result.get("quality", []),
                "verification": [ocr_result.get("error")],
                "error": ocr_result.get("error")
            }

        # Use YOUR existing verification function
        verification_result = verify_document(
            extracted_data=ocr_result.get("data", {}),
            doc_type="passport"
        )

        # Save to database
        ocr_record = {
            "user_id": current_user["_id"],
            "username": current_user["username"],
            "doc_type": "passport",
            "filename": file.filename,
            "extracted_data": ocr_result.get("data", {}),
            "quality_check": ocr_result.get("quality", []),
            "verification": verification_result,
            "timestamp": datetime.utcnow()
        }
        result = ocr_col.insert_one(ocr_record)
        record_id = str(result.inserted_id)

        return {
            "extracted_data": ocr_result.get("data", {}),
            "quality": ocr_result.get("quality", []),
            "verification": verification_result,
            "record_id": record_id  # ADD THIS LINE
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")


@app.get("/ocr/history")
async def get_ocr_history(current_user: dict = Depends(get_current_user)):
    """
    Get OCR processing history for current user
    """
    history = list(ocr_col.find(
        {"user_id": current_user["_id"]},
        {"_id": 0}  # Exclude MongoDB _id from response
    ).sort("timestamp", -1))

    return {"history": history}


@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/admin/uploads", response_class=HTMLResponse)
async def admin_uploads(request: Request, current_user=Depends(get_current_user)):
    uploads = list(ocr_col.find().sort("timestamp", -1))
    for u in uploads:
        u["_id"] = str(u["_id"])

    return templates.TemplateResponse("admin_uploads.html", {
        "request": request,
        "title": "All Uploads",
        "username": current_user["username"],
        "uploads": uploads
    })

@app.get("/admin/uploads/{doc_id}")
async def admin_upload_details(doc_id: str):
    doc = ocr_col.find_one({"_id": ObjectId(doc_id)})
    doc["_id"] = str(doc["_id"])
    return doc

@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request, current_user=Depends(get_current_user)):
    users = list(users_col.find())

    for u in users:
        u["_id"] = str(u["_id"])

    return templates.TemplateResponse("admin_users.html", {
        "request": request,
        "title": "Users",
        "username": current_user["username"],
        "users": users
    })

@app.delete("/admin/users/delete/{user_id}")
async def delete_user(user_id: str):
    users_col.delete_one({"_id": ObjectId(user_id)})
    return {"success": True}
@app.put("/admin/users/modify/{user_id}")
async def modify_user(user_id: str, payload: dict):
    new_pw = payload.get("password")
    if not new_pw:
        return {"error": "Password required"}
    hashed_pw = hash_password(new_pw)
    users_col.update_one({"_id": ObjectId(user_id)}, {"$set": {"password": hashed_pw}})
    return {"success": True}


from fastapi.responses import StreamingResponse


@app.get("/ocr/pdf/render/{record_id}")
async def render_pdf(record_id: str):
    record = ocr_col.find_one({"_id": ObjectId(record_id)})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    # Flatten content preserving order
    all_content = []
    for page in record.get("pages", []):
        for item in page.get("content", []):
            if item['type'] == 'text':
                all_content.append({'type': 'text', 'value': item['value']})
            elif item['type'] == 'image':
                img_bytes = base64.b64decode(item['base64'].split(",", 1)[-1])
                all_content.append({'type': 'image', 'image_bytes': img_bytes})

    pdf_bytes = render_pdf_inline(all_content)
    return StreamingResponse(
        pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={record['filename']}"}
    )


class UpdateExtractedDataRequest(BaseModel):
    extracted_data: Dict[str, Any]
    doc_type: str


@app.put("/ocr/update/{record_id}")
async def update_extracted_data(
        record_id: str,
        request: UpdateExtractedDataRequest,
        current_user: dict = Depends(get_current_user)
):
    """
    Update the extracted data for a specific OCR record
    """
    try:
        # Find the record
        record = ocr_col.find_one({"_id": ObjectId(record_id)})

        if not record:
            raise HTTPException(status_code=404, detail="Record not found")

        # Check if user owns this record (optional security check)
        if str(record.get("user_id")) != str(current_user["_id"]):
            raise HTTPException(status_code=403, detail="Not authorized to update this record")

        # Prepare update based on document type
        update_data = {}

        if request.doc_type == "contract":
            # For PDF/Contract documents
            update_data["text"] = request.extracted_data.get("text", "")
            update_data["tables"] = request.extracted_data.get("tables", [])
            update_data["images"] = request.extracted_data.get("images", [])
        else:
            # For CIN/Passport documents
            update_data["extracted_data"] = request.extracted_data

        # Add timestamp for last update
        update_data["last_updated"] = datetime.utcnow()

        # Update the record in database
        result = ocr_col.update_one(
            {"_id": ObjectId(record_id)},
            {"$set": update_data}
        )

        if result.modified_count == 0:
            return {
                "success": False,
                "message": "No changes were made"
            }

        return {
            "success": True,
            "message": "Data updated successfully",
            "record_id": record_id,
            "modified_count": result.modified_count
        }

    except Exception as e:
        print(f"Error updating record: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update record: {str(e)}")


@app.get("/ocr/record/{record_id}")
async def get_ocr_record(
        record_id: str,
        current_user: dict = Depends(get_current_user)
):
    """
    Get a specific OCR record by ID
    """
    try:
        record = ocr_col.find_one({"_id": ObjectId(record_id)})

        if not record:
            raise HTTPException(status_code=404, detail="Record not found")

        # Check if user owns this record
        if str(record.get("user_id")) != str(current_user["_id"]):
            raise HTTPException(status_code=403, detail="Not authorized to view this record")

        # Convert ObjectId to string
        record["_id"] = str(record["_id"])
        record["user_id"] = str(record["user_id"])

        return {
            "success": True,
            "record": record
        }

    except Exception as e:
        print(f"Error fetching record: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch record: {str(e)}")


@app.get("/ocr/export/{record_id}/{export_format}")
async def export_ocr_record(record_id: str, export_format: str, current_user: dict = Depends(get_current_user)):
    """
    Export extracted data and verification as PDF, Excel, CSV, or JSON
    """
    record = ocr_col.find_one({"_id": ObjectId(record_id)})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    # Check if user owns the record
    if str(record.get("user_id")) != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized to access this record")

    export_format = export_format.lower()
    filename_base = f"{record.get('filename', 'ocr_record')}_export"

    # Prepare content for PDF export
    content_list = []

    # For PDFs (text + tables + images)
    if record.get("doc_type") == "pdf":
        if "text" in record:
            content_list.append({"type": "text", "value": record["text"]})
        # Optionally, serialize tables
        if "tables" in record:
            for table in record["tables"]:
                content_list.append({"type": "text", "value": str(table)})
        # Include verification summary
        content_list.append({"type": "text", "value": "Verification Results:\n" + str(record.get("verification", {}))})

    else:  # CIN or Passport
        extracted_data_str = pd.json_normalize(record.get("extracted_data", {})).to_string()
        content_list.append({"type": "text", "value": extracted_data_str})
        content_list.append({"type": "text", "value": "Verification Results:\n" + str(record.get("verification", {}))})

    # Export by format
    if export_format == "pdf":
        pdf_bytes = render_pdf_inline(content_list)
        return StreamingResponse(
            pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.pdf"}
        )

    elif export_format in ["excel", "csv"]:
        df = pd.json_normalize(record.get("extracted_data", {}))
        if df.empty:
            df = pd.DataFrame([record.get("extracted_data", {})])
        output = BytesIO()
        if export_format == "excel":
            df.to_excel(output, index=False)
            output.seek(0)
            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={filename_base}.xlsx"}
            )
        else:
            df.to_csv(output, index=False)
            output.seek(0)
            return StreamingResponse(
                output,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename_base}.csv"}
            )

    elif export_format == "json":
        return JSONResponse(
            content=record,
            headers={"Content-Disposition": f"attachment; filename={filename_base}.json"}
        )

    else:
        raise HTTPException(status_code=400, detail="Invalid export format. Use pdf, excel, csv, or json.")
if __name__ == "__main__":
   uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)