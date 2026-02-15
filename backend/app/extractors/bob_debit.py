import re
import pandas as pd
from typing import List, Optional
from datetime import datetime
import pdfplumber

from backend.app.models import Transaction
from backend.app.extractors.base import BankExtractor

class BobDebitExtractor(BankExtractor):
    def extract(self) -> List[Transaction]:
        transactions: List[Transaction] = []
        
        try:
            with pdfplumber.open(self.pdf_path, password=self.password) as pdf:
                for page in pdf.pages:
                    # BoB often uses tables
                    tables = page.extract_tables()
                    for table in tables:
                        # Skip small/empty tables
                        if not table or len(table) < 2:
                             continue
                        
                        # Check header for Date, Particulars, etc.
                        header = str(table[0])
                        if 'Date' in header and 'Particulars' in header:
                            page_txns = self._parse_table(table)
                            transactions.extend(page_txns)

        except Exception as e:
            print(f"Error extracting {self.pdf_path}: {e}")
            
        return transactions

    @classmethod
    def can_handle(cls, first_page_text: str) -> bool:
        return "bank of baroda" in first_page_text.lower()

    def _parse_table(self, table: list) -> List[Transaction]:
        txns = []
        # BoB format: S.No, Date, Particulars, Cheque No, Withdrawals, Deposits, Balance
        # Specifics depend on the PDF version.
        
        for row in table[1:]:
             if not row or len(row) < 5:
                 continue
             
             # Attempt to map columns based on typical BoB layout
             # Row: [SNo, Date, Particulars, ChqNo, Withdrawal, Deposit, Balance]
             
             try:
                 date_str = row[1]
                 desc = row[2]
                 withdrawal = row[4]
                 deposit = row[5]
                 
                 # Clean values
                 if date_str: date_str = date_str.replace('\n', ' ').strip()
                 if desc: desc = desc.replace('\n', ' ').strip()
                 
                 dt = datetime.strptime(date_str, '%d-%m-%Y').date()
                 
                 amount = 0.0
                 txn_type = "Debit"
                 
                 if withdrawal and withdrawal.strip() and withdrawal.strip() != '0.00':
                     amount = float(withdrawal.replace(',', ''))
                     txn_type = "Debit"
                 elif deposit and deposit.strip() and deposit.strip() != '0.00':
                     amount = float(deposit.replace(',', ''))
                     txn_type = "Credit"
                 else:
                     continue # No transaction amount
                 
                 txns.append(Transaction(
                     date=dt,
                     description=desc,
                     amount=amount,
                     type=txn_type,
                     source_file=self.pdf_path
                 ))
                 
             except Exception:
                 continue
                 
        return txns
