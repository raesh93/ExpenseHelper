"""
Niyo DCB Bank Statement Extraction
Extracts transactions from Niyo DCB bank PDF statements.
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
import pdfplumber
import pandas as pd
from typing import List


class NiyoDCBExtractor:
    """Extract transactions from Niyo DCB bank statements."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.transactions: List[dict] = []

    def _get_password_from_filename(self) -> str:
        """Extract password from filename (last segment after '_')."""
        filename = Path(self.pdf_path).stem
        parts = filename.split('_')
        return parts[-1] if parts else ""

    def _open_pdf(self):
        """Open PDF, handling password-protected files."""
        password = self._get_password_from_filename()

        try:
            pdf = pdfplumber.open(self.pdf_path)
            _ = len(pdf.pages)
            return pdf
        except Exception:
            pass

        if password:
            try:
                pdf = pdfplumber.open(self.pdf_path, password=password)
                print(f"  Opened with password from filename")
                return pdf
            except Exception as e:
                raise Exception(f"Failed to open PDF: {e}")

        raise Exception("Failed to open PDF - may be encrypted")

    def extract_transactions(self) -> pd.DataFrame:
        """Extract all transactions from the PDF."""
        print(f"Extracting from: {self.pdf_path}")

        with self._open_pdf() as pdf:
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

        # Date pattern: DD-MM-YYYY at start of line
        date_pattern = r'^(\d{2}-\d{2}-\d{4})\s+'
        # Amount pattern
        amount_pattern = r'([\d,]+\.\d{2})'

        for line in lines:
            line = line.strip()

            # Check if line starts with a date
            date_match = re.match(date_pattern, line)
            if not date_match:
                continue

            date_str = date_match.group(1)
            rest = line[date_match.end():].strip()

            # Skip Opening/Closing Balance
            if 'Opening Balance' in rest or 'Closing Balance' in rest:
                continue

            # Find amounts in the line
            amounts = re.findall(amount_pattern, rest)
            if len(amounts) < 2:  # Need at least transaction amount and balance
                continue

            # Extract description (everything before the amounts)
            first_amount_pos = rest.find(amounts[0])
            description = rest[:first_amount_pos].strip() if first_amount_pos > 0 else ""

            if not description:
                continue

            # In Niyo format: Description | Withdrawal | Deposit | Balance
            # If withdrawal is present, it's before deposit
            # The last amount is always balance

            # Determine type based on description or position
            is_credit = 'Int.' in description or 'Credit' in description or 'Deposit' in description

            # First amount is the transaction, last is balance
            amount = amounts[0]
            txn_type = 'Credit' if is_credit else 'Debit'

            date_formatted = self._convert_date(date_str)
            category = self._categorize(description)

            transactions.append({
                'Date': date_formatted,
                'Description': description,
                'Amount': amount,
                'Type': txn_type,
                'Category': category
            })

        return transactions

    def _convert_date(self, date_str: str) -> str:
        """Convert 'DD-MM-YYYY' to 'DD/MM/YYYY'."""
        return date_str.replace('-', '/')

    def _categorize(self, description: str) -> str:
        """Categorize transaction based on description."""
        desc_lower = description.lower()

        if 'int.' in desc_lower or 'interest' in desc_lower:
            return 'Interest'
        elif 'upi' in desc_lower:
            return 'UPI'
        elif 'neft' in desc_lower:
            return 'NEFT'
        elif 'imps' in desc_lower:
            return 'IMPS'
        elif 'atm' in desc_lower:
            return 'ATM'

        return 'Other'

    def save_results(self, df: pd.DataFrame, output_dir: str = "output"):
        """Save the extracted transactions."""
        if df.empty:
            return

        pdf_name = Path(self.pdf_path).stem
        output_folder = os.path.join(output_dir, pdf_name)
        os.makedirs(output_folder, exist_ok=True)

        # Sort by date
        try:
            df = df.copy()
            df['_date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
            df = df.sort_values('_date')
            df = df.drop('_date', axis=1)
        except Exception:
            pass

        # Save CSV
        csv_path = os.path.join(output_folder, "transactions.csv")
        df.to_csv(csv_path, index=False)
        print(f"Saved to {csv_path}")

        # Save Excel
        excel_path = os.path.join(output_folder, "transactions.xlsx")
        df.to_excel(excel_path, index=False)
        print(f"Saved to {excel_path}")

        # Print summary
        print(f"\nSummary:")
        print(f"  Total transactions: {len(df)}")
        print(f"  Debits: {len(df[df['Type'] == 'Debit'])}")
        print(f"  Credits: {len(df[df['Type'] == 'Credit'])}")

        # Save summary JSON
        summary = {
            "extraction_timestamp": datetime.now().isoformat(),
            "source_pdf": self.pdf_path,
            "total_transactions": len(df),
            "debits": len(df[df['Type'] == 'Debit']),
            "credits": len(df[df['Type'] == 'Credit']),
            "columns": list(df.columns)
        }
        summary_path = os.path.join(output_folder, "summary.json")
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"Saved summary to {summary_path}")


def main():
    """Main execution."""
    pdf_dir = Path("encrypted_pdf")

    # Niyo DCB pattern: Email_Bank_Statement_*
    pdf_files = list(pdf_dir.glob("Email_Bank_Statement_*.pdf"))

    if not pdf_files:
        print("No Niyo DCB PDF files found in 'encrypted_pdf' folder.")
        return

    for pdf_file in pdf_files:
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_file.name}")
        print(f"{'='*60}")

        extractor = NiyoDCBExtractor(str(pdf_file))
        df = extractor.extract_transactions()

        if not df.empty:
            extractor.save_results(df)
            print(f"\nProcessing complete for {pdf_file.name}")


if __name__ == "__main__":
    main()
