import re
import pandas as pd
from typing import List
from datetime import datetime
import pdfplumber

from backend.app.models import Transaction
from backend.app.extractors.base import BankExtractor

class ICICICreditExtractor(BankExtractor):
    def extract(self) -> List[Transaction]:
        """Extract tables from ICICI credit card PDF documents."""
        transactions: List[Transaction] = []
        
        try:
            # We use pdfplumber directly here. 
            # In a real app we might want a shared wrapper for pdfplumber if we have specific configs.
            # For now, we reuse the logic from the original script but adapted.
            with pdfplumber.open(self.pdf_path, password=self.password) as pdf:
                all_raw_txns = []

                for page in pdf.pages:
                    # 1. Try table extraction
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            df = self._parse_transaction_table(table)
                            if df is not None and not df.empty:
                                all_raw_txns.append(df)

                    # 2. Try text extraction (fallback/complementary)
                    text = page.extract_text()
                    if text:
                        df_text = self._extract_from_text(text)
                        if df_text is not None and not df_text.empty:
                            all_raw_txns.append(df_text)

                # Merge and Deduplicate
                if all_raw_txns:
                    merged_df = pd.concat(all_raw_txns, ignore_index=True)
                    # Deduplicate based on SerNo
                    # Preference: keep='last' usually keeps the text-extracted one if both exist and 
                    # text extraction is often more reliable for full descriptions.
                    # However, table extraction might be better structured. 
                    # The original script used keep='last'.
                    if 'SerNo.' in merged_df.columns:
                        merged_df = merged_df.drop_duplicates(subset=['SerNo.'], keep='last')
                    
                    # Convert to Transaction objects
                    for _, row in merged_df.iterrows():
                        # Parse date
                        date_str = row.get('Date', '')
                        try:
                            dt = datetime.strptime(date_str, '%d/%m/%Y').date()
                        except (ValueError, TypeError):
                             # Try fallback if table extraction failed to get a clean date
                             continue 

                        # Parse Amount
                        amount_str = str(row.get('Amount (in`)', '0'))
                        is_credit = False
                        if amount_str.strip().endswith('CR'):
                            is_credit = True
                            amount_str = amount_str.replace('CR', '').strip()
                        
                        try:
                            amount_val = float(amount_str.replace(',', ''))
                        except ValueError:
                            amount_val = 0.0
                        
                        # In the standard model -> Debit is negative, Credit is positive?
                        # Or we use the type field. 
                        # The original script output 'Amount (in`)' as just the number string with 'CR' suffix sometimes.
                        # Let's standardize: Amount is always positive float, Type determines direction.
                        
                        txn_type = "Credit" if is_credit else "Debit"
                        
                        tx = Transaction(
                            date=dt,
                            description=row.get('Transaction Details', ''),
                            amount=amount_val,
                            type=txn_type,
                            reference_number=row.get('SerNo.', ''),
                            source_file=self.pdf_path
                        )
                        transactions.append(tx)

        except Exception as e:
            print(f"Error extracting {self.pdf_path}: {e}")
            # we might want to raise or log
        
        return transactions

    @classmethod
    def can_handle(cls, first_page_text: str) -> bool:
        return "icici bank" in first_page_text.lower() and "credit card" in first_page_text.lower()

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
            match1 = re.match(r'^(\d{2}/\d{2}/\d{4})\s+(\d{11})\s+(.+)$', line_stripped)

            # Pattern 2: Line has prefix before date
            match2 = re.match(r'^(.+?)(\d{2}/\d{2}/\d{4})\s+(\d{11})\s+(.+)$', line_stripped)

            match = match1 or match2
            if not match:
                continue

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
            
            # Validate SerNo
            if not re.match(r'^\d{11}$', serno):
                continue

            # Check for Credit
            is_credit = rest_of_line.strip().replace(" ", "").endswith('CR')
            # remove CR if present
            if is_credit:
                # remove the last CR
                 rest_of_line = re.sub(r'\s*CR$', '', rest_of_line)


            # Find amount (last numeric)
            amount_match = None
            # Regex for amount: 12,345.00
            for match_obj in re.finditer(r'([\d,]+\.?\d*)', rest_of_line):
                amount_match = match_obj
            
            if not amount_match:
                continue

            amount = amount_match.group(1)
            
            # Description is everything before the amount
            # points usually come before amount, we ignore points for the core transaction model for now
            # or we could try to strip them like the original script
            before_amount = rest_of_line[:amount_match.start()].strip()
            
            # Try to strip points (last number)
            points_match = re.search(r'\s(-?\d+)\s*$', before_amount)
            if points_match:
                description = before_amount[:points_match.start()].strip()
            else:
                description = before_amount

            # Clean description
            description = re.sub(r'\s+(IN|CR)\s*$', '', description).strip()
            description = " ".join(description.split())

            if len(description) > 0 and len(amount) > 0:
                # Add suffix to amount for internal processing compatibility
                amount_final = amount + (' CR' if is_credit else '')
                transactions.append({
                    'Date': date_str,
                    'SerNo.': serno,
                    'Transaction Details': description,
                    'Amount (in`)': amount_final
                })

        if transactions:
            return pd.DataFrame(transactions)
        return None

    def _parse_transaction_table(self, table: List[List[str]]) -> pd.DataFrame:
        if not table or len(table) < 2:
            return None
        
        parsed_rows = []
        for row in table[1:]:
             if not row or all(not cell.strip() for cell in row if cell):
                 continue
             
             # Basic structure check for ICICI table
             # Date, SerNo, Details...
             if len(row) >= 3:
                 try:
                     date_str = row[0].strip() if row[0] else ""
                     serno = row[1].strip() if row[1] else ""
                     
                     if not re.match(r'^-?\d{11}$', serno):
                         continue

                     details = (row[2].strip() if row[2] else "") + " " + \
                               (row[3].strip() if len(row)>3 and row[3] else "")
                     details = details.strip()

                     # Extract amount from remaining columns
                     amount = ""
                     for cell in row[5:]:
                         cell = str(cell).strip()
                         if not cell: continue
                         if re.match(r'^([\d,]+\.?\d*)\s*(CR)?$', cell, re.IGNORECASE):
                             amount = cell
                             break
                    
                     if serno and details and amount:
                         parsed_rows.append({
                             'Date': date_str,
                             'SerNo.': serno,
                             'Transaction Details': details,
                             'Amount (in`)': amount
                         })
                 except Exception:
                     pass
        
        if parsed_rows:
            return pd.DataFrame(parsed_rows)
        return None
