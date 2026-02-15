from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session, select, desc

from backend.app.core.db import get_session
from backend.app.models import Transaction, TransactionRead

router = APIRouter()

@router.get("/", response_model=List[TransactionRead])
def read_transactions(
    offset: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    session: Session = Depends(get_session)
):
    query = select(Transaction).order_by(desc(Transaction.date))
    
    if category:
        query = query.where(Transaction.category == category)
        
    transactions = session.exec(query.offset(offset).limit(limit)).all()
    return transactions

@router.patch("/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: int,
    category: Optional[str] = None,
    session: Session = Depends(get_session)
):
    transaction = session.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    if category is not None:
        transaction.category = category
        
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction
