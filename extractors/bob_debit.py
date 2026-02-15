"""
Bank of Baroda (BOB) Savings Account Statement Extraction
"""

import re
from pathlib import Path
from typing import List
import pandas as pd

from .base import DebitAccountExtractor


class BOBDebitExtractor(DebitAccountExtractor):
    """Extract transactions from BOB savings account statements."""

    FILE_PATTERNS = ["5879*"]
    BANK_NAME = "BOB Debit"

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

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            date_match = re.match(date_pattern, line)
            if not date_match:
                i += 1
                continue

            date_str = date_match.group(1)
            rest = line[date_match.end():].strip()

            if 'Opening Balance' in rest or 'Closing Balance' in rest:
                i += 1
                continue

            amounts = re.findall(amount_pattern, rest)
            if not amounts:
                i += 1
                continue

            is_credit = 'Cr' in line

            narration_parts = []
            j = i - 1
            while j >= 0:
                prev_line = lines[j].strip()
                if re.match(date_pattern, prev_line):
                    break
                if not prev_line or 'Page' in prev_line or 'DATE' in prev_line or 'NARRATION' in prev_line:
                    break
                if 'Opening Balance' in prev_line or 'Closing Balance' in prev_line:
                    break
                if 'SAVINGS ACCOUNT' in prev_line:
                    break
                narration_parts.insert(0, prev_line)
                j -= 1
                if len(narration_parts) >= 2:
                    break

            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and not re.match(date_pattern, next_line):
                    if not any(x in next_line for x in ['Page', 'Balance', 'DATE', 'NARRATION', 'SAVINGS ACCOUNT']):
                        if not re.search(amount_pattern, next_line):
                            narration_parts.append(next_line)

            narration = ' '.join(narration_parts).strip()
            if not narration:
                i += 1
                continue

            amount = amounts[0].replace(',', '')
            txn_type = 'Credit' if is_credit else 'Debit'

            date_formatted = date_str.replace('-', '/')

            try:
                amount_float = float(amount)
            except ValueError:
                amount_float = 0.0

            transactions.append({
                'Date': date_formatted,
                'Description': narration,
                'Amount': amount_float,
                'Type': txn_type
            })

            i += 1

        return transactions


# Alias for backwards compatibility
BOBExtractor = BOBDebitExtractor


def main():
    """Main execution."""
    pdf_dir = Path("encrypted_pdf")
    pdf_files = list(pdf_dir.glob("5879*.pdf"))

    if not pdf_files:
        print("No BOB PDF files found.")
        return

    for pdf_file in pdf_files:
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_file.name}")
        print(f"{'='*60}")

        extractor = BOBDebitExtractor(str(pdf_file))
        df = extractor.extract_transactions()

        if not df.empty:
            extractor.save_results(df)


if __name__ == "__main__":
    main()
