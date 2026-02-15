from typing import Optional
from datetime import date
from sqlmodel import SQLModel, Field

class TransactionBase(SQLModel):
    date: date
    description: str
    amount: float
    type: str = Field(..., description="Credit or Debit")
    category: Optional[str] = None
    balance: Optional[float] = None
    reference_number: Optional[str] = None  # SerNo or Ref No
    source_file: Optional[str] = None

class Transaction(TransactionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class TransactionCreate(TransactionBase):
    pass

class TransactionRead(TransactionBase):
    id: int
