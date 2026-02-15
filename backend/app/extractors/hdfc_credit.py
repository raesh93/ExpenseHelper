import re
import pandas as pd
from typing import List, Optional
from datetime import datetime
import pdfplumber

from backend.app.models import Transaction
from backend.app.extractors.base import BankExtractor

class HDFCCreditExtractor(BankExtractor):
    def extract(self) -> List[Transaction]:
        transactions: List[Transaction] = []
        
        try:
            with pdfplumber.open(self.pdf_path, password=self.password) as pdf:
                for page in pdf.pages:
                    # 1. Try Table Extraction (Preferred for this layout)
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            for row in table:
                                # Check for single cell with multi-line content (common in this HDFC format)
                                if len(row) >= 1 and row[0] and isinstance(row[0], str):
                                    txn = self._parse_cell_text(row[0])
                                    if txn:
                                        transactions.append(txn)
                                        continue

                                # Check for standard columns (fallback for other formats)
                                # ... existing column logic if needed, but current file is single cell ...

                    # 2. Text Extraction (Fallback or for different formats)
                    text = page.extract_text()
                    if text:
                        lines = text.split('\n')
                        for line in lines:
                            # Avoid duplicates if we already found them in tables?
                            # For now, simple logic: if we found transactions in tables, rely on that.
                            # But if tables yielded nothing, try text.
                            if not transactions:
                                txn = self._parse_line(line)
                                if txn:
                                    transactions.append(txn)
                            
        except Exception as e:
            print(f"Error extracting {self.pdf_path}: {e}")
            
        return transactions

    @classmethod
    def can_handle(cls, first_page_text: str) -> bool:
        return "hdfc bank" in first_page_text.lower() and "credit card" in first_page_text.lower()

    def _parse_cell_text(self, text: str) -> Optional[Transaction]:
        """
        Parses multi-line text from a table cell.
        Format found:
            Line 1: Description part 1
            Line 2: Description part 2 (opt)
            Line 3: 16/10/2025| 00:00 C 15.30 l (or 30/10/2025| 09:37 + C 2,845.00 l)
            Line 4: Ref Number
        """
        lines = text.split('\n')
        
        # Find the line with the date
        date_line_idx = -1
        # Regex for the date line: Date | Time C Amount l
        # Supports: 16/10/2025| 00:00 C 7.00 l
        # Supports: 30/10/2025| 09:37 + C 2,845.00 l
        regex = r'^(\d{2}/\d{2}/\d{4})\|\s*(\d{2}:\d{2})\s*(\+)?\s*C\s*([\d,]+\.?\d*)\s*l?$'
        
        match = None
        for i, line in enumerate(lines):
            m = re.search(regex, line.strip())
            if m:
                match = m
                date_line_idx = i
                break
        
        if not match:
            return None
            
        date_str = match.group(1)
        # time_str = match.group(2)
        is_plus = bool(match.group(3)) # If '+' is present, it's a Credit
        amount_str = match.group(4)
        
        # Description is everything before the date line
        desc_lines = lines[:date_line_idx]
        description = " ".join(l.strip() for l in desc_lines).strip()
        
        # Ref number is usually the line after
        ref_number = ""
        if date_line_idx + 1 < len(lines):
            ref_number = lines[date_line_idx + 1].strip()

        try:
            dt = datetime.strptime(date_str, '%d/%m/%Y').date()
            amount = float(amount_str.replace(',', ''))
            
            # '+' indicates Credit (Payment received), otherwise Debit
            txn_type = "Credit" if is_plus else "Debit"
            
            return Transaction(
                date=dt,
                description=description,
                amount=amount,
                type=txn_type,
                reference_number=ref_number,
                source_file=self.pdf_path
            )
        except Exception:
            return None

    def _parse_line(self, line: str) -> Optional[Transaction]:
        # Legacy/Text-based regex from original script
        # Example pattern: 15/01/2025  AMAZON PAY INDIA PRIVAT  500.00 Dr
        match = re.match(r'^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s+(Cr|Dr)$', line.strip(), re.IGNORECASE)
        if not match:
            return None
            
        date_str = match.group(1)
        desc = match.group(2).strip()
        amount_str = match.group(3)
        type_str = match.group(4).lower()
        
        try:
            dt = datetime.strptime(date_str, '%d/%m/%Y').date()
            amount = float(amount_str.replace(',', ''))
            txn_type = "Credit" if type_str == 'cr' else "Debit"
            
            return Transaction(
                date=dt,
                description=desc,
                amount=amount,
                type=txn_type,
                source_file=self.pdf_path
            )
        except Exception:
            return None
