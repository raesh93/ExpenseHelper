import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlmodel import Session, select, func
from typing import List, Dict, Any

from backend.app.core.db import get_session
from backend.app.models import Transaction

router = APIRouter()

UPLOAD_DIR = "uploads"

@router.get("/", response_model=List[Dict[str, Any]])
def list_files(session: Session = Depends(get_session)):
    """List all processed files with summary statistics."""
    # Aggregate transactions by source_file
    statement = (
        select(
            Transaction.source_file,
            func.count(Transaction.id).label("count"),
            func.sum(Transaction.amount).label("total_amount"),
            func.max(Transaction.date).label("last_date")
        )
        .group_by(Transaction.source_file)
        .where(Transaction.source_file != None)
    )
    
    results = session.exec(statement).all()
    
    files = []
    for row in results:
        source_file = row[0]
        # Handle full path vs relative path
        filename = os.path.basename(source_file)
        
        files.append({
            "name": filename,
            "count": row[1],
            "totalAmount": row[2] or 0.0,
            "lastDate": row[3],
            "id": filename
        })
        
    # Sort by lastDate desc
    files.sort(key=lambda x: x['lastDate'] or '', reverse=True)
    return files

@router.get("/{filename}")
def get_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Security check: prevent directory traversal
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(file_path, media_type="application/pdf")
