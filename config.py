import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # MongoDB connection
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

    # Database name
    DATABASE_NAME: str = "OCR"

    # JWT configuration
    SECRET_KEY: str = os.getenv("JWT_SECRET", "Ztya58**+T00")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

    # Upload folder for OCR files
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", "uploads")
    TEMP_FOLDER: str = os.getenv("TEMP_FOLDER", "temp")