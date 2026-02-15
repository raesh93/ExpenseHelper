import re
import pandas as pd
from typing import List, Optional
from datetime import datetime
import pdfplumber

from backend.app.models import Transaction
from backend.app.extractors.base import BankExtractor

class SBICreditExtractor(BankExtractor):
    def extract(self) -> List[Transaction]:
        transactions: List[Transaction] = []
        
        try:
            with pdfplumber.open(self.pdf_path, password=self.password) as pdf:
                # SBI usually has a summary at top, then transactions.
                # Table-based extraction often checks headers.
                
                for page in pdf.pages:
                    # Try text based line parsing first as it's often more robust for simple lists
                   text = page.extract_text()
                   if text:
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
        return "sbi card" in first_page_text.lower() or "state bank of india" in first_page_text.lower()

    def _parse_line(self, line: str) -> Optional[Transaction]:
        # Based on typical SBI format: Date Description Amount Ref (sometimes keys vary)
        # Ref: DD MMM YY   Description   Amount(Dr/Cr)
        # Regex: (\d{2}\s+[A-Za-z]{3}\s+\d{2})\s+(.+?)\s+([\d,]+\.\d{2})(D|C)?
        
        match = re.search(r'(\d{2}\s+[A-Za-z]{3}\s+\d{2})\s+(.+?)\s+([\d,]+\.\d{2})([DC])?', line)
        if not match:
            return None
            
        date_str = match.group(1)
        desc = match.group(2).strip()
        amount_str = match.group(3)
        dc_flag = match.group(4) # D or C
        
        try:
            # Date format: 15 Jan 25
            dt = datetime.strptime(date_str, '%d %b %y').date()
            amount = float(amount_str.replace(',', ''))
            
            # If D/C flag is present, use it. Else default to Debit unless negative?
            # SBI usually marks Credit with 'C' suffix or negative sign in some formats.
            # Assuming D=Debit, C=Credit if present.
            
            txn_type = "Debit"
            if dc_flag == 'C':
                txn_type = "Credit"
            
            return Transaction(
                date=dt,
                description=desc,
                amount=amount,
                type=txn_type,
                source_file=self.pdf_path
            )
        except Exception:
            return None
