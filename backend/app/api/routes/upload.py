from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from sqlmodel import Session, select
import shutil
import os
import uuid
import traceback

from backend.app.core.db import get_session
from backend.app.models import Transaction
from backend.app.extractors.factory import get_extractor

router = APIRouter()

UPLOAD_DIR = "uploads"
# Ensure it exists at module level, but also inside function to be safe
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/", response_model=dict)
def upload_pdf(
    file: UploadFile = File(...), 
    password: str = Form(None),
    session: Session = Depends(get_session)
):
    print(f"DEBUG: Starting upload for {file.filename}")
    print(f"DEBUG: CWD is {os.getcwd()}")
    
    # 1. Save file locally
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
        print(f"DEBUG: Saving to {file_path}")
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"DEBUG: File saved successfully. Size: {os.path.getsize(file_path)} bytes")
    except Exception as e:
        print(f"ERROR: Failed to save file: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")

    # 2. Get Extractor
    try:
        print(f"DEBUG: Getting extractor for {file_path}")
        extractor = get_extractor(file_path, password)
        
        if not extractor:
            print("ERROR: No suitable extractor found")
            try:
                os.remove(file_path)
            except:
                pass
            raise HTTPException(status_code=400, detail="Could not identify a valid extractor for this PDF")
    except Exception as e:
        print(f"ERROR: get_extractor failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error identifying PDF: {e}")

    # 3. Extract
    try:
        print(f"DEBUG: Extracting with {extractor.__class__.__name__}")
        transactions = extractor.extract()
        print(f"DEBUG: Extracted {len(transactions)} transactions")
    except Exception as e:
        print(f"ERROR: Extraction failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

    # 4. Save to DB
    try:
        saved_count = 0
        for txn in transactions:
            session.add(txn)
            saved_count += 1
        
        session.commit()
        print(f"DEBUG: Saved {saved_count} transactions to DB")
    except Exception as e:
        print(f"ERROR: DB Save failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database save failed: {e}")

    return {
        "filename": file.filename,
        "saved_filename": os.path.basename(file_path),
        "extractor": extractor.__class__.__name__,
        "transactions_found": len(transactions),
        "transactions_saved": saved_count
    }
