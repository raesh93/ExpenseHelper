from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from sqlmodel import Session, select
import shutil
import os
import uuid

from backend.app.core.db import get_session
from backend.app.models import Transaction
from backend.app.extractors.factory import get_extractor

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/", response_model=dict)
def upload_pdf(
    file: UploadFile = File(...), 
    password: str = Form(None),
    session: Session = Depends(get_session)
):
    # 1. Save file locally
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")

    # 2. Get Extractor
    extractor = get_extractor(file_path, password)
    
    if not extractor:
        # cleanup
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="Could not identify a valid extractor for this PDF")

    # 3. Extract
    try:
        transactions = extractor.extract()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

    # 4. Save to DB
    saved_count = 0
    for txn in transactions:
        # Deduplication check could go here (e.g. check if same date+amount+desc exists)
        # For now, just insert.
        session.add(txn)
        saved_count += 1
    
    session.commit()

    return {
        "filename": file.filename,
        "saved_filename": os.path.basename(file_path),
        "extractor": extractor.__class__.__name__,
        "transactions_found": len(transactions),
        "transactions_saved": saved_count
    }
