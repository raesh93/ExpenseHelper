"""
PDF Table Extraction and Consolidation
Extracts tables from ICICI credit card PDFs, merges tables with identical schemas, and sorts by date.
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
import pandas as pd
from typing import List, Dict, Tuple

from utils import open_pdf, categorize_transaction, save_results


class PDFTableExtractor:
    """Extract and process tables from ICICI credit card PDF documents."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.tables: List[pd.DataFrame] = []
        self.table_schemas: List[Tuple[str, ...]] = []

    def extract_tables(self) -> List[pd.DataFrame]:
        """Extract transaction tables from the PDF using both table and text extraction."""
        print(f"Extracting tables from: {self.pdf_path}")

        with open_pdf(self.pdf_path) as pdf:
            print(f"Total pages: {len(pdf.pages)}")

            all_transactions = []

            for page_num, page in enumerate(pdf.pages, 1):
                page_transactions = []

                # Try table extraction first (works best for page 2)
                # Use default settings - text strategy causes column misalignment
                tables = page.extract_tables()

                if tables:
                    print(f"Page {page_num}: Found {len(tables)} table(s)")

                    for table_idx, table in enumerate(tables):
                        if not table or len(table) < 2:
                            continue

                        # Try to parse this table as a transaction table
                        df = self._parse_transaction_table(table)
                        if df is not None and not df.empty:
                            page_transactions.append(df)
                            print(f"  Table {table_idx}: Extracted {len(df)} transactions")

                # Always use text extraction - it's more reliable for ICICI statements
                # Table extraction often misses rows due to PDF structure
                text = page.extract_text()
                if text:
                    df_text = self._extract_from_text(text)
                    if df_text is not None and not df_text.empty:
                        page_transactions.append(df_text)
                        print(f"  Text extraction: Found {len(df_text)} transactions")

                all_transactions.extend(page_transactions)

            # Merge all extracted transactions
            if all_transactions:
                merged_df = pd.concat(all_transactions, ignore_index=True)
                # Remove duplicates based on SerNo (transaction ID)
                # Use keep='last' to prefer text-extracted rows (more reliable) over table-extracted
                merged_df = merged_df.drop_duplicates(subset=['SerNo.'], keep='last')

                self.tables.append(merged_df)
                self.table_schemas.append(tuple(merged_df.columns))
                print(f"\nTotal unique transactions extracted: {len(merged_df)}")

        return self.tables

    def _extract_from_text(self, text: str) -> pd.DataFrame:
        """Extract transactions from raw text using flexible regex."""
        lines = text.split('\n')
        transactions = []

        for line in lines:
            line_stripped = line.strip()

            # Skip header lines
            if not line_stripped or 'Date' in line_stripped or 'SerNo' in line_stripped:
                continue

            # Pattern 1: Line starts with date (no prefix)
            # Format: DD/MM/YYYY SerNo11 Description Points Amount
            match1 = re.match(r'^(\d{2}/\d{2}/\d{4})\s+(\d{11})\s+(.+)$', line_stripped)

            # Pattern 2: Line has prefix before date
            # Format: Prefix DD/MM/YYYY SerNo11 Description Points Amount
            match2 = re.match(r'^(.+?)(\d{2}/\d{2}/\d{4})\s+(\d{11})\s+(.+)$', line_stripped)

            match = match1 or match2
            if not match:
                continue

            # Extract components based on which pattern matched
            if match1:
                date_str = match1.group(1)
                serno = match1.group(2)
                rest_of_line = match1.group(3).strip()
            else:  # match2
                date_str = match2.group(2)
                serno = match2.group(3)
                rest_of_line = match2.group(4).strip()

            # Validate date format
            if not re.match(r'^\d{2}/\d{2}/\d{4}$', date_str):
                continue

            # Validate SerNo is 11 digits
            if not re.match(r'^\d{11}$', serno):
                continue

            # From rest_of_line, extract description, points, and amount
            # The rest contains: Description + "IN/CR" + Points + Amount [CR]

            # Check if this is a credit transaction (ends with CR)
            is_credit = rest_of_line.strip().endswith('CR')
            if is_credit:
                rest_of_line = rest_of_line.strip()[:-2].strip()  # Remove trailing CR

            # Find the last numeric value with decimals (amount)
            amount_match = None
            for match_obj in re.finditer(r'([\d,]+\.?\d*)', rest_of_line):
                amount_match = match_obj

            if not amount_match:
                continue

            amount = amount_match.group(1)
            # Add CR suffix to amount if it's a credit
            if is_credit:
                amount = amount + ' CR'

            before_amount = rest_of_line[:amount_match.start()].strip()

            # Try to extract points (last number in before_amount)
            points_match = re.search(r'\s(-?\d+)\s*$', before_amount)
            if points_match:
                points = points_match.group(1)
                description = before_amount[:points_match.start()].strip()
            else:
                points = ""
                description = before_amount

            # Clean description - remove IN/CR flags from middle of description
            description = re.sub(r'\s+(IN|CR)\s*$', '', description).strip()
            description = " ".join(description.split())

            # Validate we have required fields
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
        """Parse a transaction table from the PDF with proper column reconstruction."""
        if not table or len(table) < 2:
            return None

        parsed_rows = []

        # Start from row 1 (skip header)
        for row in table[1:]:
            if not row or all(not cell.strip() for cell in row):
                # Skip empty rows
                continue

            if len(row) >= 3:
                try:
                    date_str = row[0].strip()
                    serno = row[1].strip()

                    # Validate SerNo is exactly 11 digits - skip if not
                    if not re.match(r'^-?\d{11}$', serno):
                        continue

                    # Transaction details might span multiple cells
                    details_parts = [row[2].strip()]
                    if len(row) > 3 and row[3].strip():
                        details_parts.append(row[3].strip())
                    if len(row) > 4 and row[4].strip():
                        details_parts.append(row[4].strip())
                    details = " ".join(details_parts)

                    # Points - try to extract from cells 5 onwards
                    points = ""
                    amount = ""
                    intl_amount = ""

                    # Look for numeric values in the remaining cells
                    for cell in row[5:]:
                        cell = cell.strip()
                        if not cell:
                            continue
                        # Check if it's a decimal number (amount), possibly with CR suffix
                        # Match: 123.45, 1,234.56, 123.45 CR
                        amount_match = re.match(r'^([\d,]+\.?\d*)\s*(CR)?$', cell, re.IGNORECASE)
                        if amount_match:
                            num_part = amount_match.group(1)
                            is_credit = amount_match.group(2) is not None
                            # Could be points or amount
                            if '.' in num_part or ',' in num_part:
                                amount = num_part + (' CR' if is_credit else '')  # Has decimal, it's amount
                            elif not points and not amount:
                                points = num_part  # First number without decimals is points
                            elif not amount:
                                amount = num_part + (' CR' if is_credit else '')

                    # Validate we have the essential fields
                    if serno and details and amount:
                        # Date is optional for table extraction (text extraction handles it better)
                        parsed_rows.append({
                            'Date': date_str if re.match(r'^\d{2}/\d{2}/\d{4}$', date_str) else '',
                            'SerNo.': serno,
                            'Transaction Details': details,
                            'Reward Points': points,
                            'Intl.# amount': intl_amount,
                            'Amount (in`)': amount
                        })
                except Exception:
                    # Skip rows that can't be parsed
                    pass

        if parsed_rows:
            df = pd.DataFrame(parsed_rows)
            cols = ['Date', 'SerNo.', 'Transaction Details', 'Reward Points', 'Intl.# amount', 'Amount (in`)']
            return df[cols]

        return None

    def get_schema_groups(self) -> Dict[Tuple[str, ...], List[int]]:
        """Group tables by their schema (column names)."""
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

        print(f"\n{'='*60}")
        print("Merging tables by schema...")
        print(f"{'='*60}")

        for schema, indices in schema_groups.items():
            if len(indices) > 1:
                print(f"\nSchema: {schema}")
                print(f"  Tables to merge: {len(indices)}")

                # Concatenate all tables with same schema
                tables_to_merge = [self.tables[i] for i in indices]
                merged_df = pd.concat(tables_to_merge, ignore_index=True)

                # Remove duplicates
                merged_df = merged_df.drop_duplicates()

                print(f"  Merged result: {len(merged_df)} rows")

                # Create a safe schema key handling None values
                schema_key = "_".join(str(col) if col else "unnamed" for col in schema)
                merged_tables[schema_key] = merged_df
            else:
                # Create a safe schema key handling None values
                schema_key = "_".join(str(col) if col else "unnamed" for col in schema)
                merged_tables[schema_key] = self.tables[indices[0]].drop_duplicates()

        return merged_tables

    def find_date_column(self, df: pd.DataFrame) -> str:
        """Identify the date column in a DataFrame."""
        date_keywords = ['date', 'posted date', 'transaction date', 'posting date', 'value date']

        for col in df.columns:
            if col is None:  # Skip None columns
                continue
            if any(keyword in col.lower() for keyword in date_keywords):
                return col

        # If no date column found, return None
        return None

    def sort_by_date(self, merged_tables: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Sort each merged table by date if a date column exists."""
        print(f"\n{'='*60}")
        print("Sorting tables by date...")
        print(f"{'='*60}")

        sorted_tables = {}

        for schema_key, df in merged_tables.items():
            date_col = self.find_date_column(df)

            if date_col:
                print(f"\nSchema: {schema_key}")
                print(f"  Date column found: {date_col}")

                # Try to parse dates
                try:
                    # First try DD/MM/YYYY format, then YYYY-MM-DD
                    df[date_col] = pd.to_datetime(df[date_col], format='%d/%m/%Y', errors='coerce')

                    # For any remaining NaT values, try YYYY-MM-DD
                    nat_mask = df[date_col].isna()
                    if nat_mask.any():
                        df.loc[nat_mask, date_col] = pd.to_datetime(
                            df.loc[nat_mask, date_col],
                            format='%Y-%m-%d',
                            errors='coerce'
                        )

                    df_sorted = df.sort_values(by=date_col)
                    sorted_tables[schema_key] = df_sorted
                    print(f"  Sorted by {date_col}")
                except Exception as e:
                    print(f"  Error sorting by {date_col}: {e}")
                    sorted_tables[schema_key] = df
            else:
                print(f"\nSchema: {schema_key}")
                print(f"  No date column found - skipping sort")
                sorted_tables[schema_key] = df

        return sorted_tables

    def save_results(self, sorted_tables: Dict[str, pd.DataFrame], output_dir: str = "output"):
        """Save the processed tables to files."""
        os.makedirs(output_dir, exist_ok=True)

        print(f"\n{'='*60}")
        print("Saving results...")
        print(f"{'='*60}")

        def sanitize_filename(name: str) -> str:
            """Sanitize a filename by removing/replacing problematic characters."""
            # Replace newlines and tabs with underscores
            name = name.replace('\n', '_').replace('\t', '_')
            # Limit length to 50 chars
            name = name[:50]
            # Remove any remaining problematic characters
            name = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)
            return name

        for schema_key, df in sorted_tables.items():
            safe_key = sanitize_filename(schema_key)

            # Save to CSV
            csv_path = os.path.join(output_dir, f"{safe_key}.csv")
            df.to_csv(csv_path, index=False)
            print(f"Saved to {csv_path}")

            # Save to Excel
            excel_path = os.path.join(output_dir, f"{safe_key}.xlsx")
            df.to_excel(excel_path, index=False)
            print(f"Saved to {excel_path}")

        # Save summary
        summary = {
            "extraction_timestamp": datetime.now().isoformat(),
            "source_pdf": self.pdf_path,
            "total_tables_extracted": len(self.tables),
            "merged_tables": len(sorted_tables),
            "schemas": [
                {
                    "name": key,
                    "rows": len(df),
                    "columns": list(df.columns)
                }
                for key, df in sorted_tables.items()
            ]
        }

        summary_path = os.path.join(output_dir, "summary.json")
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"Saved summary to {summary_path}")


def main():
    """Main execution."""
    # Find PDF files in encrypted_pdf folder
    pdf_dir = Path("encrypted_pdf")
    pdf_files = list(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found in 'encrypted_pdf' folder.")
        return

    # Process each PDF
    for pdf_file in pdf_files:
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_file.name}")
        print(f"{'='*60}")

        extractor = PDFTableExtractor(str(pdf_file))

        # Extract tables
        tables = extractor.extract_tables()

        if not tables:
            print("No tables found in PDF.")
            continue

        # Merge tables by schema
        merged = extractor.merge_tables_by_schema()

        # Sort by date
        sorted_tables = extractor.sort_by_date(merged)

        # Save results
        extractor.save_results(sorted_tables)

        print(f"\nProcessing complete for {pdf_file.name}\n")


if __name__ == "__main__":
    main()
