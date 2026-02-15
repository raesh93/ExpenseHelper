"""
ICICI Credit Card Statement Extraction (Coral, Amazon Pay)
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
import pandas as pd
from typing import List, Dict, Tuple

from .base import CreditCardExtractor


class ICICICCExtractor(CreditCardExtractor):
    """Extract transactions from ICICI credit card statements."""

    FILE_PATTERNS = ["6528*", "4315*"]
    BANK_NAME = "ICICI CC"

    def __init__(self, pdf_path: str):
        super().__init__(pdf_path)
        self.tables: List[pd.DataFrame] = []
        self.table_schemas: List[Tuple[str, ...]] = []

    def extract_transactions(self) -> pd.DataFrame:
        """Extract transactions - wrapper for compatibility."""
        tables = self.extract_tables()
        if tables:
            return tables[0]
        return pd.DataFrame()

    def extract_tables(self) -> List[pd.DataFrame]:
        """Extract transaction tables from the PDF."""
        print(f"Extracting tables from: {self.pdf_path}")

        with self.open_pdf() as pdf:
            print(f"Total pages: {len(pdf.pages)}")

            all_transactions = []

            for page_num, page in enumerate(pdf.pages, 1):
                page_transactions = []

                tables = page.extract_tables()
                if tables:
                    print(f"Page {page_num}: Found {len(tables)} table(s)")

                    for table_idx, table in enumerate(tables):
                        if not table or len(table) < 2:
                            continue

                        df = self._parse_transaction_table(table)
                        if df is not None and not df.empty:
                            page_transactions.append(df)
                            print(f"  Table {table_idx}: Extracted {len(df)} transactions")

                text = page.extract_text()
                if text:
                    df_text = self._extract_from_text(text)
                    if df_text is not None and not df_text.empty:
                        page_transactions.append(df_text)
                        print(f"  Text extraction: Found {len(df_text)} transactions")

                all_transactions.extend(page_transactions)

            if all_transactions:
                merged_df = pd.concat(all_transactions, ignore_index=True)
                merged_df = merged_df.drop_duplicates(subset=['SerNo.'], keep='last')

                self.tables.append(merged_df)
                self.table_schemas.append(tuple(merged_df.columns))
                print(f"\nTotal unique transactions extracted: {len(merged_df)}")

        return self.tables

    def _extract_from_text(self, text: str) -> pd.DataFrame:
        """Extract transactions from raw text."""
        lines = text.split('\n')
        transactions = []

        for line in lines:
            line_stripped = line.strip()

            if not line_stripped or 'Date' in line_stripped or 'SerNo' in line_stripped:
                continue

            match1 = re.match(r'^(\d{2}/\d{2}/\d{4})\s+(\d{11})\s+(.+)$', line_stripped)
            match2 = re.match(r'^(.+?)(\d{2}/\d{2}/\d{4})\s+(\d{11})\s+(.+)$', line_stripped)

            match = match1 or match2
            if not match:
                continue

            if match1:
                date_str = match1.group(1)
                serno = match1.group(2)
                rest_of_line = match1.group(3).strip()
            else:
                date_str = match2.group(2)
                serno = match2.group(3)
                rest_of_line = match2.group(4).strip()

            if not re.match(r'^\d{2}/\d{2}/\d{4}$', date_str):
                continue
            if not re.match(r'^\d{11}$', serno):
                continue

            is_credit = rest_of_line.strip().endswith('CR')
            if is_credit:
                rest_of_line = rest_of_line.strip()[:-2].strip()

            amount_match = None
            for match_obj in re.finditer(r'([\d,]+\.?\d*)', rest_of_line):
                amount_match = match_obj

            if not amount_match:
                continue

            amount = amount_match.group(1)
            if is_credit:
                amount = amount + ' CR'

            before_amount = rest_of_line[:amount_match.start()].strip()

            points_match = re.search(r'\s(-?\d+)\s*$', before_amount)
            if points_match:
                points = points_match.group(1)
                description = before_amount[:points_match.start()].strip()
            else:
                points = ""
                description = before_amount

            description = re.sub(r'\s+(IN|CR)\s*$', '', description).strip()
            description = " ".join(description.split())

            if len(description) > 0 and len(amount) > 0:
                transactions.append({
                    'Date': date_str,
                    'SerNo.': serno,
                    'Transaction Details': description,
                    'Reward Points': points,
                    'Intl.# amount': '',
                    'Amount (in`)': amount
                })

        if transactions:
            df = pd.DataFrame(transactions)
            return df[['Date', 'SerNo.', 'Transaction Details', 'Reward Points', 'Intl.# amount', 'Amount (in`)']]

        return None

    def _parse_transaction_table(self, table: List[List[str]]) -> pd.DataFrame:
        """Parse a transaction table from the PDF."""
        if not table or len(table) < 2:
            return None

        parsed_rows = []

        for row in table[1:]:
            if not row or all(not cell.strip() for cell in row):
                continue

            if len(row) >= 3:
                try:
                    date_str = row[0].strip()
                    serno = row[1].strip()

                    if not re.match(r'^-?\d{11}$', serno):
                        continue

                    details_parts = [row[2].strip()]
                    if len(row) > 3 and row[3].strip():
                        details_parts.append(row[3].strip())
                    if len(row) > 4 and row[4].strip():
                        details_parts.append(row[4].strip())
                    details = " ".join(details_parts)

                    points = ""
                    amount = ""
                    intl_amount = ""

                    for cell in row[5:]:
                        cell = cell.strip()
                        if not cell:
                            continue
                        amount_match = re.match(r'^([\d,]+\.?\d*)\s*(CR)?$', cell, re.IGNORECASE)
                        if amount_match:
                            num_part = amount_match.group(1)
                            is_credit = amount_match.group(2) is not None
                            if '.' in num_part or ',' in num_part:
                                amount = num_part + (' CR' if is_credit else '')
                            elif not points and not amount:
                                points = num_part
                            elif not amount:
                                amount = num_part + (' CR' if is_credit else '')

                    if serno and details and amount:
                        parsed_rows.append({
                            'Date': date_str if re.match(r'^\d{2}/\d{2}/\d{4}$', date_str) else '',
                            'SerNo.': serno,
                            'Transaction Details': details,
                            'Reward Points': points,
                            'Intl.# amount': intl_amount,
                            'Amount (in`)': amount
                        })
                except Exception:
                    pass

        if parsed_rows:
            df = pd.DataFrame(parsed_rows)
            return df[['Date', 'SerNo.', 'Transaction Details', 'Reward Points', 'Intl.# amount', 'Amount (in`)']]

        return None

    def get_schema_groups(self) -> Dict[Tuple[str, ...], List[int]]:
        """Group tables by their schema."""
        schema_map = {}
        for idx, schema in enumerate(self.table_schemas):
            if schema not in schema_map:
                schema_map[schema] = []
            schema_map[schema].append(idx)
        return schema_map

    def merge_tables_by_schema(self) -> Dict[str, pd.DataFrame]:
        """Merge tables with identical schemas."""
        schema_groups = self.get_schema_groups()
        merged_tables = {}

        for schema, indices in schema_groups.items():
            schema_key = "_".join(str(col) if col else "unnamed" for col in schema)
            if len(indices) > 1:
                tables_to_merge = [self.tables[i] for i in indices]
                merged_df = pd.concat(tables_to_merge, ignore_index=True).drop_duplicates()
                merged_tables[schema_key] = merged_df
            else:
                merged_tables[schema_key] = self.tables[indices[0]].drop_duplicates()

        return merged_tables

    def save_results(self, df=None, output_dir: str = "output"):
        """Save results - handles both single df and merged tables."""
        if df is not None:
            super().save_results(df, output_dir)
            return

        # Handle legacy table-based saving
        merged = self.merge_tables_by_schema()
        os.makedirs(output_dir, exist_ok=True)

        def sanitize_filename(name: str) -> str:
            name = name.replace('\n', '_').replace('\t', '_')[:50]
            return "".join(c if c.isalnum() or c in "_-" else "_" for c in name)

        for schema_key, table_df in merged.items():
            safe_key = sanitize_filename(schema_key)
            table_df.to_csv(os.path.join(output_dir, f"{safe_key}.csv"), index=False)
            table_df.to_excel(os.path.join(output_dir, f"{safe_key}.xlsx"), index=False)

        summary = {
            "extraction_timestamp": datetime.now().isoformat(),
            "source_pdf": self.pdf_path,
            "total_tables_extracted": len(self.tables),
            "merged_tables": len(merged),
        }
        with open(os.path.join(output_dir, "summary.json"), 'w') as f:
            json.dump(summary, f, indent=2)


# Alias for backwards compatibility
PDFTableExtractor = ICICICCExtractor


def main():
    """Main execution."""
    pdf_dir = Path("encrypted_pdf")
    pdf_files = list(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found.")
        return

    for pdf_file in pdf_files:
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_file.name}")
        print(f"{'='*60}")

        extractor = ICICICCExtractor(str(pdf_file))
        tables = extractor.extract_tables()

        if tables:
            extractor.save_results()


if __name__ == "__main__":
    main()
