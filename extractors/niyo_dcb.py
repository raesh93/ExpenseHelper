"""
Niyo DCB Bank Savings Account Statement Extraction
"""

import re
from pathlib import Path
from typing import List
import pandas as pd

from .base import DebitAccountExtractor


class NiyoDCBExtractor(DebitAccountExtractor):
    """Extract transactions from Niyo DCB bank statements."""

    FILE_PATTERNS = ["Email_Bank_Statement_*"]
    BANK_NAME = "Niyo DCB"

    def __init__(self, pdf_path: str):
        super().__init__(pdf_path)
        self.transactions: List[dict] = []

    def extract_transactions(self) -> pd.DataFrame:
        """Extract all transactions from the PDF."""
        print(f"Extracting from: {self.pdf_path}")

        with self.open_pdf() as pdf:
            print(f"Total pages: {len(pdf.pages)}")

            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

            self.transactions = self._parse_text(full_text)
            if self.transactions:
                print(f"  Found {len(self.transactions)} transactions")

        if not self.transactions:
            print("No transactions found.")
            return pd.DataFrame()

        df = pd.DataFrame(self.transactions)
        df = df.drop_duplicates(subset=['Date', 'Description', 'Amount', 'Type'], keep='first')
        print(f"\nTotal unique transactions: {len(df)}")

        return df

    def _parse_text(self, text: str) -> List[dict]:
        """Parse transactions from text."""
        transactions = []
        lines = text.split('\n')

        date_pattern = r'^(\d{2}-\d{2}-\d{4})\s+'
        amount_pattern = r'([\d,]+\.\d{2})'

        for line in lines:
            line = line.strip()

            date_match = re.match(date_pattern, line)
            if not date_match:
                continue

            date_str = date_match.group(1)
            rest = line[date_match.end():].strip()

            if 'Opening Balance' in rest or 'Closing Balance' in rest:
                continue

            amounts = re.findall(amount_pattern, rest)
            if len(amounts) < 2:
                continue

            first_amount_pos = rest.find(amounts[0])
            description = rest[:first_amount_pos].strip() if first_amount_pos > 0 else ""

            if not description:
                continue

            is_credit = 'Int.' in description or 'Credit' in description or 'Deposit' in description

            amount = amounts[0].replace(',', '')
            txn_type = 'Credit' if is_credit else 'Debit'

            date_formatted = date_str.replace('-', '/')

            try:
                amount_float = float(amount)
            except ValueError:
                amount_float = 0.0

            transactions.append({
                'Date': date_formatted,
                'Description': description,
                'Amount': amount_float,
                'Type': txn_type
            })

        return transactions


def main():
    """Main execution."""
    pdf_dir = Path("encrypted_pdf")
    pdf_files = list(pdf_dir.glob("Email_Bank_Statement_*.pdf"))

    if not pdf_files:
        print("No Niyo DCB PDF files found.")
        return

    for pdf_file in pdf_files:
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_file.name}")
        print(f"{'='*60}")

        extractor = NiyoDCBExtractor(str(pdf_file))
        df = extractor.extract_transactions()

        if not df.empty:
            extractor.save_results(df)


if __name__ == "__main__":
    main()
