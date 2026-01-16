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
        """Parse transactions from text."""
        transactions = []
        lines = text.split('\n')

        # Date pattern: DD-MM-YYYY
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

            # Collect narration (may span multiple lines)
            narration_parts = []
            amounts = []

            # Parse the first line
            # Find amounts at the end
            all_amounts = re.findall(amount_pattern, rest)
            if all_amounts:
                # Get the position of first amount to extract narration
                first_amount_pos = rest.find(all_amounts[0])
                narration_parts.append(rest[:first_amount_pos].strip())
                amounts = all_amounts
            else:
                narration_parts.append(rest)

            # Check next lines for continuation of narration or amounts
            i += 1
            while i < len(lines):
                next_line = lines[i].strip()
                # If next line starts with date, we're done with this transaction
                if re.match(date_pattern, next_line):
                    break
                # If it's a page header/footer or empty, skip
                if not next_line or 'Page' in next_line or 'Balance' in next_line:
                    i += 1
                    continue
                # If it contains amounts, extract them
                line_amounts = re.findall(amount_pattern, next_line)
                if line_amounts and not amounts:
                    amounts = line_amounts
                    # Get narration before amounts
                    first_amount_pos = next_line.find(line_amounts[0])
                    if first_amount_pos > 0:
                        narration_parts.append(next_line[:first_amount_pos].strip())
                elif not line_amounts and not any(x in next_line for x in ['Cr', 'Dr', 'DATE', 'NARRATION']):
                    # This is narration continuation
                    narration_parts.append(next_line)
                i += 1
                # Don't go too far
                if len(narration_parts) > 3:
                    break

            if not amounts:
                continue

            narration = ' '.join(narration_parts).strip()
            if not narration:
                continue

            # Determine if it's a debit or credit based on position/count of amounts
            # In BOB format: WITHDRAWAL (DR) | DEPOSIT (CR) | BALANCE
            # If there are 3 amounts: withdrawal, deposit, balance (one of first two is the transaction)
            # If there are 2 amounts: one is transaction, one is balance
            # The balance always has "Cr" suffix in original text

            # Simple heuristic: if narration suggests credit (NEFT, Int.Pd, ACHCR, dividend)
            is_credit = any(x in narration.upper() for x in ['NEFT', 'INT.PD', 'ACHCR', 'DIVIDEND', 'CREDIT'])

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
