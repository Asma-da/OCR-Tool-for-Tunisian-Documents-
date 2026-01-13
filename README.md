# Tunisian Document OCR & Verification Platform

A secure, fully on-premise Optical Character Recognition (OCR) system designed specifically for Tunisian official documents.  
The platform extracts text, verifies document authenticity, and exports structured data while ensuring data privacy and regulatory compliance.

---

## 📌 Project Overview

This project automates the processing of Tunisian administrative documents by combining OCR, data validation, and authenticity verification in a single platform.  

It supports bilingual content (Arabic & French) and addresses the unique challenges of Tunisian documents such as cursive Arabic script, security elements, and varying document quality.

---

## ✨ Key Features

- **🏠 Fully On-Premise Deployment**  
  All processing is done locally , no cloud dependency for enhanced data privacy.

- **🧠 Advanced OCR Extraction**  
  Accurate text extraction from images and PDFs with Arabic and French support.

- **🔍 Document Authenticity Verification**  
  - Format validation (CIN, Passport numbers)  
  - Logical consistency checks (e.g., date of issue > date of birth)  
  - Completeness and integrity validation  
  - Confidence scoring for reliability assessment

- **🔐 Secure Access Control**  
  - JWT-based authentication  
  - Role-based access control (Admin / User)

- **📤 Multi-Format Data Export**  
  Export extracted data and verification results to: PDF, Excel, CSV, JSON

- **🌐 RESTful API**  
  Easily integrates with existing systems and workflows.

---

## 📄 Supported Documents

- 🇹🇳 Tunisian National Identity Card (CIN) – Front & Back  
- 🛂 Tunisian Passport  
- 📑 PDF Documents (e.g., contracts, administrative files)

---

## 🧩 Tunisian Document Specificities

- Bilingual content 
- Right-to-left cursive Arabic script  
- Security elements (watermarks, stamps, background patterns)  
- Machine Readable Zone (MRZ) for passports  
- Variable quality due to scans and mobile captures

---

## 🛠️ Tech Stack

**Backend**  
- Python (FastAPI / Flask)  
- OCR Engines (Tesseract / custom pipelines)  
- ReportLab (PDF generation)  
- OpenPyXL (Excel export)  

**Frontend**  
- HTML5 / CSS3  
- JavaScript (Vanilla JS)  
- Bootstrap 5  
- PDF.js (PDF preview)  

**Security**  
- JWT Authentication  
- Role-based authorization

---

## 🚀 Getting Started

### 1️⃣ Clone the repository
```bash
git clone https://github.com/your-username/tunisian-ocr-platform.git
cd tunisian-ocr-platform
```
### 2️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

### 3️⃣ Run the application
```bash
python app.py
```

The application will be available at: **http://localhost:8000**

## 🔮 Future Improvements

- ✍️ Handwritten text recognition
- 📚 Support for additional administrative documents
- 🤖 Machine learning-based verification enhancement
- 📊 Improved confidence scoring and analytics dashboard
- 🌍 Multi-language support (Arabic, French, English)
- 🔐 Enhanced security features and encryption

## 📜 License

This project is intended for academic and educational use.

