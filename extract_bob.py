"""
Bank of Baroda (BOB) Account Statement Extraction
Extracts transactions from BOB savings account PDF statements.
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
import pdfplumber
import pandas as pd
from typing import List


class BOBExtractor:
    """Extract transactions from BOB savings account statements."""

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
        """Parse transactions from text.

        BOB format: narration line comes BEFORE the date line:
        Line N:   ACHCR/COMPANY_NAME (narration)
        Line N+1: DD-MM-YYYY amount balance Cr (date, amount, balance)
        Line N+2: REFERENCE_NUMBER (optional continuation)
        """
        transactions = []
        lines = text.split('\n')

        # Date pattern: DD-MM-YYYY followed by amounts
        date_pattern = r'^(\d{2}-\d{2}-\d{4})\s+'
        # Amount pattern: number with optional commas and decimal
        amount_pattern = r'([\d,]+\.\d{2})'

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check if line starts with a date
            date_match = re.match(date_pattern, line)
            if not date_match:
                i += 1
                continue

            date_str = date_match.group(1)
            rest = line[date_match.end():].strip()

            # Skip Opening/Closing Balance lines
            if 'Opening Balance' in rest or 'Closing Balance' in rest:
                i += 1
                continue

            # Get amounts from this line
            amounts = re.findall(amount_pattern, rest)
            if not amounts:
                i += 1
                continue

            # Check if this is a credit transaction (has "Cr" suffix)
            is_credit = 'Cr' in line

            # Narration comes from the PREVIOUS line(s)
            narration_parts = []

            # Look backwards for narration (lines before the date line)
            j = i - 1
            while j >= 0:
                prev_line = lines[j].strip()
                # Stop if we hit another date line or empty/header lines
                if re.match(date_pattern, prev_line):
                    break
                if not prev_line or 'Page' in prev_line or 'DATE' in prev_line or 'NARRATION' in prev_line:
                    break
                if 'Opening Balance' in prev_line or 'Closing Balance' in prev_line:
                    break
                if 'SAVINGS ACCOUNT' in prev_line:
                    break
                # This is part of the narration
                narration_parts.insert(0, prev_line)
                j -= 1
                # Don't go too far back
                if len(narration_parts) >= 2:
                    break

            # Also check the next line for reference number continuation
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and not re.match(date_pattern, next_line):
                    if not any(x in next_line for x in ['Page', 'Balance', 'DATE', 'NARRATION', 'SAVINGS ACCOUNT']):
                        # Check if it's a reference number (no amounts)
                        if not re.search(amount_pattern, next_line):
                            narration_parts.append(next_line)

            narration = ' '.join(narration_parts).strip()
            if not narration:
                i += 1
                continue

            # Take first amount as the transaction amount
            amount = amounts[0]
            txn_type = 'Credit' if is_credit else 'Debit'

            # Convert date format
            date_formatted = self._convert_date(date_str)
            category = self._categorize(narration)

            transactions.append({
                'Date': date_formatted,
                'Description': narration,
                'Amount': amount,
                'Type': txn_type,
                'Category': category
            })

            i += 1

        return transactions

    def _convert_date(self, date_str: str) -> str:
        """Convert 'DD-MM-YYYY' to 'DD/MM/YYYY'."""
        return date_str.replace('-', '/')

    def _categorize(self, description: str) -> str:
        """Categorize transaction based on description."""
        desc_upper = description.upper()

        if 'INT.PD' in desc_upper or 'INTEREST' in desc_upper:
            return 'Interest'
        elif 'DIVIDEND' in desc_upper:
            return 'Dividend'
        elif 'NEFT' in desc_upper:
            return 'NEFT Transfer'
        elif 'ACHCR' in desc_upper:
            return 'Dividend/Credit'
        elif 'UPI' in desc_upper:
            return 'UPI'
        elif 'ATM' in desc_upper:
            return 'ATM'
        elif 'IMPS' in desc_upper:
            return 'IMPS'

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

        # Calculate totals
        df_copy = df.copy()
        df_copy['_amount'] = df_copy['Amount'].str.replace(',', '').astype(float)
        total_credit = df_copy[df_copy['Type'] == 'Credit']['_amount'].sum()
        total_debit = df_copy[df_copy['Type'] == 'Debit']['_amount'].sum()
        print(f"  Total Credits: {total_credit:.2f}")
        print(f"  Total Debits: {total_debit:.2f}")

        # Save summary JSON
        summary = {
            "extraction_timestamp": datetime.now().isoformat(),
            "source_pdf": self.pdf_path,
            "total_transactions": len(df),
            "debits": len(df[df['Type'] == 'Debit']),
            "credits": len(df[df['Type'] == 'Credit']),
            "total_credit_amount": total_credit,
            "total_debit_amount": total_debit,
            "columns": list(df.columns)
        }
        summary_path = os.path.join(output_folder, "summary.json")
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"Saved summary to {summary_path}")


def main():
    """Main execution."""
    pdf_dir = Path("encrypted_pdf")

    # BOB pattern: 5879*
    pdf_files = list(pdf_dir.glob("5879*.pdf"))

    if not pdf_files:
        print("No BOB PDF files found in 'encrypted_pdf' folder.")
        return

    for pdf_file in pdf_files:
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_file.name}")
        print(f"{'='*60}")

        extractor = BOBExtractor(str(pdf_file))
        df = extractor.extract_transactions()

        if not df.empty:
            extractor.save_results(df)
            print(f"\nProcessing complete for {pdf_file.name}")


if __name__ == "__main__":
    main()
