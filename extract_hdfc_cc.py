"""
HDFC Credit Card Statement Extraction
Extracts transactions from HDFC credit card PDF statements.
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
import pdfplumber
import pandas as pd
from typing import List


class HDFCCCExtractor:
    """Extract transactions from HDFC credit card statements."""

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

            for page_num, page in enumerate(pdf.pages, 1):
                tables = page.extract_tables()
                for table in tables:
                    if not table or not table[0]:
                        continue
                    # Find transaction table by header
                    if 'DATE' in str(table[0]) and 'TRANSACTION' in str(table[0]):
                        page_txns = self._parse_table(table[1:])  # Skip header
                        if page_txns:
                            print(f"  Page {page_num}: {len(page_txns)} transactions")
                            self.transactions.extend(page_txns)

        if not self.transactions:
            print("No transactions found.")
            return pd.DataFrame()

        df = pd.DataFrame(self.transactions)
        df = df.drop_duplicates(subset=['Date', 'Description', 'Amount', 'Type'], keep='first')
        print(f"\nTotal unique transactions: {len(df)}")

        return df

    def _parse_table(self, rows: list) -> List[dict]:
        """Parse transactions from table rows."""
        transactions = []

        # Pattern to extract date, amount from messy cell text
        # Format: "Description\nDD/MM/YYYY| HH:MM [+] C amount l\nRef#..."
        date_pattern = r'(\d{2}/\d{2}/\d{4})\|'
        amount_pattern = r'(\+)?\s*C\s*([\d,]+\.?\d*)\s*l'

        for row in rows:
            if not row or not row[0]:
                continue

            cell_text = row[0]
            if not cell_text:
                continue

            # Extract date
            date_match = re.search(date_pattern, cell_text)
            if not date_match:
                continue

            date_str = date_match.group(1)

            # Extract amount and credit indicator
            amount_match = re.search(amount_pattern, cell_text)
            if not amount_match:
                continue

            is_credit = amount_match.group(1) == '+'
            amount = amount_match.group(2)

            # Extract description (first line, cleaned up)
            lines = cell_text.split('\n')
            description = lines[0].strip()

            # Clean up description - remove card holder name if it's at start
            if description.isupper() and len(description.split()) <= 3:
                # Likely a name, use second line
                if len(lines) > 1:
                    description = lines[1].split('(Ref#')[0].strip()
            else:
                description = description.split('(Ref#')[0].strip()

            # Skip if description looks like header
            if 'DATE' in description or 'TRANSACTION' in description:
                continue

            txn_type = 'Credit' if is_credit else 'Debit'
            category = self._categorize(description)

            transactions.append({
                'Date': date_str,
                'Description': description,
                'Amount': amount,
                'Type': txn_type,
                'Category': category
            })

        return transactions

    def _categorize(self, description: str) -> str:
        """Categorize transaction based on description."""
        desc_lower = description.lower()

        if 'emi' in desc_lower:
            if 'prin' in desc_lower:
                return 'EMI Principal'
            elif 'int' in desc_lower:
                return 'EMI Interest'
            return 'EMI'
        elif 'gst' in desc_lower or 'igst' in desc_lower or 'sgst' in desc_lower or 'cgst' in desc_lower:
            return 'Tax'
        elif 'payment' in desc_lower or 'bppy' in desc_lower:
            return 'Payment'
        elif any(x in desc_lower for x in ['youtube', 'netflix', 'spotify', 'prime', 'hotstar']):
            return 'Subscription'
        elif any(x in desc_lower for x in ['swiggy', 'zomato', 'uber eats']):
            return 'Food Delivery'
        elif any(x in desc_lower for x in ['amazon', 'flipkart', 'myntra']):
            return 'Shopping'

        return 'Purchase'

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

    # HDFC CC pattern: 5241XXXXXXXXXX99_*
    pdf_files = list(pdf_dir.glob("5241*.pdf"))

    if not pdf_files:
        print("No HDFC credit card PDF files found in 'encrypted_pdf' folder.")
        return

    for pdf_file in pdf_files:
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_file.name}")
        print(f"{'='*60}")

        extractor = HDFCCCExtractor(str(pdf_file))
        df = extractor.extract_transactions()

        if not df.empty:
            extractor.save_results(df)
            print(f"\nProcessing complete for {pdf_file.name}")


if __name__ == "__main__":
    main()
