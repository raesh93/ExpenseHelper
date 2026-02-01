"""
SBI Credit Card Statement Extraction
Extracts transactions from SBI credit card PDF statements.
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
import pdfplumber
import pandas as pd
from typing import List


class SBICCExtractor:
    """Extract transactions from SBI credit card statements."""

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
                    if not table or len(table) < 2:
                        continue
                    # Check for transaction table header
                    header = str(table[0])
                    if 'Date' in header and 'Transaction' in header and 'Amount' in header:
                        page_txns = self._parse_table(table)
                        if page_txns:
                            print(f"  Page {page_num}: {len(page_txns)} transactions")
                            self.transactions.extend(page_txns)

        if not self.transactions:
            print("No transactions found.")
            return pd.DataFrame()

        df = pd.DataFrame(self.transactions)
        # Don't deduplicate - duplicate fees on same date are legitimate
        print(f"\nTotal transactions: {len(df)}")

        return df

    def _parse_table(self, table: list) -> List[dict]:
        """Parse transactions from SBI table format."""
        transactions = []

        # SBI format: dates in col 0, descriptions in col 1, amounts in col 2
        # All values are newline-separated within each cell
        for row in table[1:]:  # Skip header
            if not row or len(row) < 3:
                continue

            dates_str = row[0] or ""
            descs_str = row[1] or ""
            amounts_str = row[2] or ""

            dates = [d.strip() for d in dates_str.split('\n') if d.strip()]
            descs = [d.strip() for d in descs_str.split('\n') if d.strip()]
            amounts = [a.strip() for a in amounts_str.split('\n') if a.strip()]

            # Filter out section headers (like "TRANSACTIONS FOR RAJESH")
            filtered_descs = []
            for desc in descs:
                if desc.startswith('TRANSACTIONS FOR'):
                    continue
                filtered_descs.append(desc)

            # Match dates with descriptions and amounts
            # Sometimes there are fewer dates than descriptions (dates apply to multiple items)
            date_idx = 0
            current_date = dates[0] if dates else ""

            for i, desc in enumerate(filtered_descs):
                if i < len(amounts):
                    amount_str = amounts[i]

                    # Update date if we have more dates
                    if date_idx < len(dates):
                        current_date = dates[date_idx]
                        # Move to next date if this description seems to have its own date
                        if date_idx + 1 < len(dates) and i + 1 < len(filtered_descs):
                            date_idx += 1

                    # Parse amount and type
                    amount_match = re.match(r'([\d,]+\.?\d*)\s*([DC])', amount_str)
                    if not amount_match:
                        continue

                    amount = amount_match.group(1)
                    txn_type = 'Credit' if amount_match.group(2) == 'C' else 'Debit'

                    # Convert date format "DD MMM YY" to "DD/MM/YYYY"
                    date_formatted = self._convert_date(current_date)

                    category = self._categorize(desc)

                    transactions.append({
                        'Date': date_formatted,
                        'Description': desc,
                        'Amount': amount,
                        'Type': txn_type,
                        'Category': category
                    })

        return transactions

    def _convert_date(self, date_str: str) -> str:
        """Convert 'DD MMM YY' to 'DD/MM/YYYY'."""
        try:
            dt = datetime.strptime(date_str, '%d %b %y')
            return dt.strftime('%d/%m/%Y')
        except ValueError:
            return date_str

    def _categorize(self, description: str) -> str:
        """Categorize transaction based on description."""
        desc_lower = description.lower()

        if 'annual fee' in desc_lower or 'membership fee' in desc_lower:
            return 'Annual Fee'
        elif 'replacement fee' in desc_lower:
            return 'Fee'
        elif 'gst' in desc_lower or 'igst' in desc_lower or 'sgst' in desc_lower or 'cgst' in desc_lower:
            return 'Tax'
        elif 'emi' in desc_lower:
            if 'prin' in desc_lower:
                return 'EMI Principal'
            elif 'int' in desc_lower:
                return 'EMI Interest'
            return 'EMI'
        elif 'payment' in desc_lower or 'credit' in desc_lower:
            return 'Payment'
        elif 'fuel' in desc_lower or 'petrol' in desc_lower:
            return 'Fuel'
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

    # SBI CC pattern: 0992*
    pdf_files = list(pdf_dir.glob("0992*.pdf"))

    if not pdf_files:
        print("No SBI credit card PDF files found in 'encrypted_pdf' folder.")
        return

    for pdf_file in pdf_files:
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_file.name}")
        print(f"{'='*60}")

        extractor = SBICCExtractor(str(pdf_file))
        df = extractor.extract_transactions()

        if not df.empty:
            extractor.save_results(df)
            print(f"\nProcessing complete for {pdf_file.name}")


if __name__ == "__main__":
    main()
