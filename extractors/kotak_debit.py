"""
Kotak Bank Savings Account Statement Extraction
"""

import re
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import pandas as pd

from .base import DebitAccountExtractor


class KotakDebitExtractor(DebitAccountExtractor):
    """Extract transactions from Kotak Bank savings account statements."""

    FILE_PATTERNS = ["6006*", "27065*"]
    BANK_NAME = "Kotak Debit"

    def __init__(self, pdf_path: str):
        super().__init__(pdf_path)
        self.transactions: List[dict] = []

    def extract_transactions(self) -> pd.DataFrame:
        """Extract all transactions from the PDF."""
        print(f"Extracting from: {self.pdf_path}")

        with self.open_pdf() as pdf:
            print(f"Total pages: {len(pdf.pages)}")

            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if not text:
                    continue

                page_txns = self._parse_transactions(text)
                if page_txns:
                    print(f"  Page {page_num}: {len(page_txns)} transactions")
                    self.transactions.extend(page_txns)

        if not self.transactions:
            print("No transactions found.")
            return pd.DataFrame()

        df = pd.DataFrame(self.transactions)
        df = df.drop_duplicates(subset=['Date', 'Description', 'Amount'], keep='first')
        print(f"\nTotal unique transactions: {len(df)}")

        df = self._filter_savings_account(df)
        print(f"Filtered to savings account: {len(df)} transactions")

        return df

    def _parse_transactions(self, text: str) -> List[dict]:
        """Parse transactions from raw text."""
        transactions = []
        lines = text.split('\n')

        date_pattern = r'^(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec),?\s+\d{4})'

        for line in lines:
            line = line.strip()
            if not line:
                continue

            date_match = re.match(date_pattern, line)
            if not date_match:
                continue

            date_str = date_match.group(1)
            rest = line[date_match.end():].strip()

            if 'TRANSACTION DETAILS' in rest or 'CHEQUE/REFERENCE' in rest:
                continue
            if 'OPENING BALANCE' in rest or 'Opening Balance' in rest:
                continue
            if 'CLOSING BALANCE' in rest or 'Closing Balance' in rest:
                continue
            if re.match(r'^\s*-\s*\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec),?\s+\d{4}\s*$', rest):
                continue

            txn = self._parse_transaction_line(date_str, rest)
            if txn:
                transactions.append(txn)

        return transactions

    def _parse_transaction_line(self, date_str: str, rest: str) -> Optional[dict]:
        """Parse a single transaction line."""
        amount_pattern = r'([+-]?[\d,]+\.\d{2})\s*$'

        balance_match = re.search(amount_pattern, rest)
        if not balance_match:
            return None

        rest = rest[:balance_match.start()].strip()

        amount_match = re.search(amount_pattern, rest)
        if not amount_match:
            return None

        amount = amount_match.group(1)
        rest = rest[:amount_match.start()].strip()

        another_amount = re.search(amount_pattern, rest)
        if another_amount:
            amount = another_amount.group(1)
            rest = rest[:another_amount.start()].strip()

        ref_pattern = r'(UPI-\d+|NACH\w+|NEFT\w+-\d+|\[\d+\]|\d{10,}TO|\d{10,})$'
        ref_match = re.search(ref_pattern, rest)

        if ref_match:
            description = rest[:ref_match.start()].strip()
        else:
            description = rest

        if amount.startswith('+'):
            amount = amount[1:]
            txn_type = 'Credit'
        elif amount.startswith('-'):
            amount = amount[1:]
            txn_type = 'Debit'
        else:
            txn_type = 'Unknown'

        try:
            dt = datetime.strptime(date_str, '%d %b, %Y')
            date_formatted = dt.strftime('%d/%m/%Y')
        except ValueError:
            date_formatted = date_str

        amount_clean = amount.replace(',', '')
        try:
            amount_float = float(amount_clean)
        except ValueError:
            amount_float = 0.0

        return {
            'Date': date_formatted,
            'Description': description.strip(),
            'Amount': amount_float,
            'Type': txn_type
        }

    def _filter_savings_account(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter to only savings account transactions."""
        term_patterns = ['Tran. For Principal', 'Sweep Trf To:', 'Closure Int After Tax',
                         'SWEEP TRANSFER FROM', 'Opening Balance', 'Closing Balance']

        def is_term_deposit(desc):
            return any(p in desc for p in term_patterns)

        return df[~df['Description'].apply(is_term_deposit)]


# Alias for backwards compatibility
KotakExtractor = KotakDebitExtractor


def main():
    """Main execution."""
    pdf_dir = Path("encrypted_pdf")
    pdf_files = list(pdf_dir.glob("6006279*.pdf"))

    if not pdf_files:
        print("No Kotak PDF files found.")
        return

    for pdf_file in pdf_files:
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_file.name}")
        print(f"{'='*60}")

        extractor = KotakDebitExtractor(str(pdf_file))
        df = extractor.extract_transactions()

        if not df.empty:
            extractor.save_results(df)


if __name__ == "__main__":
    main()
