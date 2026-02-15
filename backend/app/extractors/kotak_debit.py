import re
import pandas as pd
from typing import List, Optional
from datetime import datetime
import pdfplumber

from backend.app.models import Transaction
from backend.app.extractors.base import BankExtractor

class KotakDebitExtractor(BankExtractor):
    def extract(self) -> List[Transaction]:
        """Extract transactions from Kotak Bank savings account statements."""
        transactions: List[Transaction] = []
        
        try:
            with pdfplumber.open(self.pdf_path, password=self.password) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    page_txns = self._parse_transactions(text)
                    transactions.extend(page_txns)
        
        except Exception as e:
            print(f"Error extracting {self.pdf_path}: {e}")
            
        # Deduplicate
        # valid transactions only
        unique_txns = []
        seen = set()
        for txn in transactions:
            # Create a simplified tuple for dedup hash
            # (date, amount, description)
            key = (txn.date, txn.amount, txn.description)
            if key not in seen:
                seen.add(key)
                unique_txns.append(txn)
        
        return unique_txns

    @classmethod
    def can_handle(cls, first_page_text: str) -> bool:
        return "kotak" in first_page_text.lower() and "statement" in first_page_text.lower()

    def _parse_transactions(self, text: str) -> List[Transaction]:
        transactions = []
        lines = text.split('\n')
        
        # Regex for date: DD Mon, YYYY (e.g., 01 Jan, 2025)
        date_pattern = r'^(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec),?\s+\d{4})'

        for line in lines:
            line = line.strip()
            if not line: continue

            date_match = re.match(date_pattern, line)
            if not date_match: continue

            date_str = date_match.group(1)
            rest = line[date_match.end():].strip()

            # Skip headers/footers
            if any(x in rest for x in ['TRANSACTION DETAILS', 'CHEQUE/REFERENCE', 'OPENING BALANCE', 'CLOSING BALANCE', 'Opening Balance', 'Closing Balance']):
                continue
            
            # Skip page headers repeated
            if re.match(r'^\s*-\s*\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec),?\s+\d{4}\s*$', rest):
                continue

            txn = self._parse_transaction_line(date_str, rest)
            if txn:
                # Filter out term deposits/sweeps (as per original logic)
                if self._is_savings_transaction(txn.description):
                    transactions.append(txn)
        
        return transactions

    def _parse_transaction_line(self, date_str: str, rest: str) -> Optional[Transaction]:
        # Logic adapted from original KotakDebitExtractor
        
        # We need to find amounts. The line usually ends with Balance, then Amount
        # Or Amount then Balance? 
        # Original logic:
        # balance_match = re.search(amount_pattern, rest) (last number)
        # amount_match = re.search(amount_pattern, rest_before_balance) (second to last number)
        
        amount_pattern = r'([+-]?[\d,]+\.\d{2})\s*$'
        
        # 1. Find Balance (last number)
        balance_match = re.search(amount_pattern, rest)
        if not balance_match: return None
        
        balance_str = balance_match.group(1)
        rest = rest[:balance_match.start()].strip()
        
        # 2. Find Amount (transaction amount)
        amount_match = re.search(amount_pattern, rest)
        if not amount_match: return None
        
        amount_str = amount_match.group(1)
        rest = rest[:amount_match.start()].strip()
        
        # 3. Check for another amount (some lines have multiple?)
        # Original logic checked for a third amount, if found, it took the middle one as amount?
        # Let's stick to the extracted amount_str for now.
        
        # 4. Reference Number / Description split
        # ref_pattern = r'(UPI-\d+|NACH\w+|NEFT\w+-\d+|\[\d+\]|\d{10,}TO|\d{10,})$'
        # ref_match = re.search(ref_pattern, rest)
        # if ref_match: description = rest[:ref_match.start()] ...
        
        description = rest
        # (simplifying description extraction for now, can enhance if needed)

        # Parse Amount and Type
        txn_type = "Unknown"
        if amount_str.startswith('+'):
            txn_type = 'Credit'
            amount_str = amount_str[1:]
        elif amount_str.startswith('-'):
            txn_type = 'Debit'
            amount_str = amount_str[1:]
        
        # Parse Amount Value
        try:
            amount_val = float(amount_str.replace(',', ''))
        except ValueError:
            return None
        
        # Parse Balance Value
        try:
            balance_val = float(balance_str.replace(',', '').replace('+','').replace('-',''))
        except ValueError:
            balance_val = None

        # Parse Date
        try:
            dt = datetime.strptime(date_str, '%d %b, %Y').date()
        except ValueError:
             # try without comma
            try:
                dt = datetime.strptime(date_str, '%d %b %Y').date()
            except ValueError:
                return None

        return Transaction(
            date=dt,
            description=description.strip(),
            amount=amount_val,
            type=txn_type,
            balance=balance_val,
            source_file=self.pdf_path
        )

    def _is_savings_transaction(self, description: str) -> bool:
        term_patterns = ['Tran. For Principal', 'Sweep Trf To:', 'Closure Int After Tax',
                         'SWEEP TRANSFER FROM', 'Opening Balance', 'Closing Balance']
        return not any(p in description for p in term_patterns)
