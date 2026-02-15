import re
import pandas as pd
from typing import List, Optional
from datetime import datetime
import pdfplumber

from backend.app.models import Transaction
from backend.app.extractors.base import BankExtractor

class NiyoExtractor(BankExtractor):
    def extract(self) -> List[Transaction]:
        transactions: List[Transaction] = []
        
        try:
            with pdfplumber.open(self.pdf_path, password=self.password) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if not text: continue
                    
                    # Niyo often simple text list
                    lines = text.split('\n')
                    for line in lines:
                        txn = self._parse_line(line)
                        if txn:
                            transactions.append(txn)

        except Exception as e:
            print(f"Error extracting {self.pdf_path}: {e}")
            
        return transactions

    @classmethod
    def can_handle(cls, first_page_text: str) -> bool:
        return "dcb bank" in first_page_text.lower() or "niyo" in first_page_text.lower()

    def _parse_line(self, line: str) -> Optional[Transaction]:
        # Niyo Format: DD-MM-YYYY Description Amount Type
        # Regex: (\d{2}-\d{2}-\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s*(Dr|Cr)
        
        match = re.match(r'^(\d{2}-\d{2}-\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s*(Dr|Cr|DR|CR)$', line.strip(), re.IGNORECASE)
        if not match:
            return None
            
        date_str = match.group(1)
        desc = match.group(2).strip()
        amount_str = match.group(3)
        type_str = match.group(4).lower()
        
        try:
            dt = datetime.strptime(date_str, '%d-%m-%Y').date()
            amount = float(amount_str.replace(',', ''))
            
            txn_type = "Credit" if type_str in ['cr', 'credit'] else "Debit"
            
            return Transaction(
                date=dt,
                description=desc,
                amount=amount,
                type=txn_type,
                source_file=self.pdf_path
            )
        except Exception:
            return None
