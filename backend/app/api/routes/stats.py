from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func
from sqlalchemy import func as sa_func

from backend.app.core.db import get_session
from backend.app.models import Transaction

router = APIRouter()

@router.get("/category")
def get_category_stats(session: Session = Depends(get_session)):
    # Group by category and sum amount
    # Note: Amount is positive for both credit and debit in our extraction?
    # We need to handle Debit vs Credit.
    # Usually stats are for spending (Debits).
    
    query = select(
        Transaction.category, 
        sa_func.sum(Transaction.amount).label("total")
    ).where(Transaction.type == "Debit").group_by(Transaction.category)
    
    results = session.exec(query).all()
    
    return [
        {"category": row[0] or "Uncategorized", "total": row[1]} 
        for row in results
    ]

@router.get("/monthly")
def get_monthly_stats(session: Session = Depends(get_session)):
    # SQLite doesn't have easy date truncation functions compared to Postgres
    # We will just fetch all debits and aggregate in python for simplicity for now,
    # or use strftime if available.
    
    # Let's try flexible aggregation
    transactions = session.exec(select(Transaction).where(Transaction.type == "Debit")).all()
    
    stats = {}
    for txn in transactions:
        month_key = txn.date.strftime("%Y-%m")
        stats[month_key] = stats.get(month_key, 0) + txn.amount
        
    return [{"month": k, "total": v} for k, v in sorted(stats.items())]
