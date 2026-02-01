"""
Master script to run all extractors and generate metadata summary.
"""

import os
import re
from pathlib import Path
from datetime import datetime
import pandas as pd
import pdfplumber
from tqdm import tqdm

# Import all extractors
from extract_tables import PDFTableExtractor
from extract_kotak import KotakExtractor
from extract_kotak_cc import KotakCCExtractor
from extract_hdfc_cc import HDFCCCExtractor
from extract_sbi_cc import SBICCExtractor
from extract_bob import BOBExtractor
from extract_niyo_dcb import NiyoDCBExtractor


# Mapping of file patterns to extractors and bank names
EXTRACTOR_MAP = [
    {"pattern": "5241*", "extractor": HDFCCCExtractor, "bank": "HDFC CC"},
    {"pattern": "0992*", "extractor": SBICCExtractor, "bank": "SBI CC"},
    {"pattern": "5879*", "extractor": BOBExtractor, "bank": "BOB Debit"},
    {"pattern": "Email_Bank_Statement_*", "extractor": NiyoDCBExtractor, "bank": "Niyo DCB"},
    {"pattern": "6528*", "extractor": PDFTableExtractor, "bank": "ICICI Coral CC"},
    {"pattern": "4315*", "extractor": PDFTableExtractor, "bank": "Amazon ICICI CC"},
    {"pattern": "00114*", "extractor": KotakCCExtractor, "bank": "Kotak CC"},
    {"pattern": "00116*", "extractor": KotakCCExtractor, "bank": "Kotak CC"},
    {"pattern": "6006*", "extractor": KotakExtractor, "bank": "Kotak Debit"},
    {"pattern": "27065*", "extractor": KotakExtractor, "bank": "Kotak Debit"},
]


def get_password_from_filename(filepath: str) -> str:
    """Extract password from filename (last segment after '_')."""
    filename = Path(filepath).stem
    parts = filename.split('_')
    return parts[-1] if parts else ""


def get_month_from_filename(filepath: str) -> str:
    """Extract month from filename (second-to-last segment after '_')."""
    filename = Path(filepath).stem
    parts = filename.split('_')
    if len(parts) >= 2:
        month = parts[-2].lower()
        if month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                     'jul', 'aug', 'sep', 'oct', 'nov', 'dec']:
            return month.capitalize()
    return ""


def get_extractor_for_file(filename: str):
    """Get the appropriate extractor and bank name for a file."""
    for mapping in EXTRACTOR_MAP:
        pattern = mapping["pattern"]
        # Convert glob pattern to regex
        regex_pattern = pattern.replace("*", ".*")
        if re.match(regex_pattern, filename):
            return mapping["extractor"], mapping["bank"]
    return None, "Unknown"


def extract_statement_period(pdf_path: str) -> tuple:
    """Try to extract statement period from PDF."""
    from_date = ""
    to_date = ""

    password = get_password_from_filename(pdf_path)

    try:
        try:
            pdf = pdfplumber.open(pdf_path)
        except:
            pdf = pdfplumber.open(pdf_path, password=password)

        with pdf:
            # Read first page text
            text = pdf.pages[0].extract_text() or ""

            # Various patterns for statement period
            patterns = [
                # "Statement Period from Nov 01, 2025 to Nov 30, 2025"
                r'Statement Period[:\s]+(?:from\s+)?(\w+\s+\d{1,2},?\s+\d{4})\s+(?:to|-)\s+(\w+\s+\d{1,2},?\s+\d{4})',
                # "01-12-2025 To 31-12-2025"
                r'(\d{1,2}-\d{1,2}-\d{4})\s+To\s+(\d{1,2}-\d{1,2}-\d{4})',
                # "Billing Period 17 Nov, 2025 - 16 Dec, 2025"
                r'Billing Period[:\s]+(\d{1,2}\s+\w+,?\s+\d{4})\s*[-–]\s*(\d{1,2}\s+\w+,?\s+\d{4})',
                # "for Statement Period: 20 Nov 25 to 19 Dec 25"
                r'Statement Period[:\s]+(\d{1,2}\s+\w+\s+\d{2,4})\s+to\s+(\d{1,2}\s+\w+\s+\d{2,4})',
            ]

            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    from_date = match.group(1)
                    to_date = match.group(2)
                    break
    except Exception as e:
        pass

    return from_date, to_date


def run_extractor(pdf_path: str, extractor_class, bank_name: str) -> dict:
    """Run an extractor and return metadata."""
    filename = Path(pdf_path).name
    month = get_month_from_filename(pdf_path)
    from_date, to_date = extract_statement_period(pdf_path)

    result = {
        "Filename": filename,
        "Month": month,
        "Bank/CC": bank_name,
        "Period_From": from_date,
        "Period_To": to_date,
        "Total_Transactions": 0,
        "Payment_Count": 0,
        "Payment_Amount": 0.0,
        "Refund_Count": 0,
        "Refund_Amount": 0.0,
        "Spend_Count": 0,
        "Spend_Amount": 0.0,
        "Net_Spend": 0.0,
        "Status": "Failed"
    }

    try:
        extractor = extractor_class(pdf_path)

        # Different extractors have different methods
        if extractor_class == PDFTableExtractor:
            tables = extractor.extract_tables()
            if tables and len(tables) > 0:
                df = tables[0]
                result["Total_Transactions"] = len(df)

                # Check for CR in amount column and categorize
                if 'Amount (in`)' in df.columns:
                    df['_amount_str'] = df['Amount (in`)'].astype(str)
                    df['_is_credit'] = df['_amount_str'].str.contains('CR', case=False, na=False)
                    df['_amount'] = df['_amount_str'].str.replace('CR', '', case=False).str.replace(',', '').str.strip()
                    df['_amount'] = pd.to_numeric(df['_amount'], errors='coerce').fillna(0)

                    # Check Transaction Details for payment indicators
                    if 'Transaction Details' in df.columns:
                        payment_keywords = ['payment', 'bbps', 'neft', 'imps', 'upi.*received', 'paid']
                        df['_is_payment'] = df['Transaction Details'].str.lower().str.contains('|'.join(payment_keywords), regex=True, na=False) & df['_is_credit']
                    else:
                        df['_is_payment'] = False

                    # Payments (credits that are bill payments)
                    result["Payment_Count"] = int(df['_is_payment'].sum())
                    result["Payment_Amount"] = float(df[df['_is_payment']]['_amount'].sum())

                    # Refunds (other credits - not payments)
                    refund_mask = df['_is_credit'] & ~df['_is_payment']
                    result["Refund_Count"] = int(refund_mask.sum())
                    result["Refund_Amount"] = float(df[refund_mask]['_amount'].sum())

                    # Spends (debits)
                    result["Spend_Count"] = int((~df['_is_credit']).sum())
                    result["Spend_Amount"] = float(df[~df['_is_credit']]['_amount'].sum())

                    # Net Spend = Spends - Refunds (excluding payments)
                    result["Net_Spend"] = result["Spend_Amount"] - result["Refund_Amount"]

                result["Status"] = "Success"

                # Save results for ICICI
                pdf_name = Path(pdf_path).stem
                output_folder = Path("output") / pdf_name
                output_folder.mkdir(parents=True, exist_ok=True)

                # Normalize column names and structure like other extractors
                if 'Transaction Details' in df.columns:
                    df = df.rename(columns={'Transaction Details': 'Description'})
                if 'Amount (in`)' in df.columns:
                    df['Type'] = df['_is_credit'].map({True: 'Credit', False: 'Debit'})
                    df = df.rename(columns={'Amount (in`)': 'Amount_Orig'})
                    df['Amount'] = df['_amount']

                # Select and save relevant columns (including Reward Points)
                save_cols = ['Date', 'Description', 'Reward Points', 'Amount', 'Type']
                save_cols = [c for c in save_cols if c in df.columns]
                df_save = df[save_cols].copy()
                df_save.to_csv(output_folder / "transactions.csv", index=False)
                df_save.to_excel(output_folder / "transactions.xlsx", index=False)
        else:
            df = extractor.extract_transactions()
            if df is not None and not df.empty:
                result["Total_Transactions"] = len(df)

                if 'Amount' in df.columns:
                    df['_amount'] = df['Amount'].astype(str).str.replace(',', '')
                    df['_amount'] = pd.to_numeric(df['_amount'], errors='coerce').fillna(0)

                if 'Type' in df.columns and 'Category' in df.columns:
                    # Payment categories
                    payment_categories = ['Payment', 'NEFT Transfer', 'IMPS', 'UPI']
                    df['_is_payment'] = (df['Type'] == 'Credit') & df['Category'].isin(payment_categories)

                    # EMI Conversion is not actual spend/refund (it's accounting adjustment)
                    emi_conversion_cats = ['EMI Conversion']
                    df['_is_emi_conv'] = df['Category'].isin(emi_conversion_cats)

                    # EMI-converted purchases should also be excluded (they're offset by EMI Conversion credit)
                    # These have "ConverttoEMI" or "*Convert" in description
                    if 'Description' in df.columns:
                        df['_is_emi_purchase'] = df['Description'].str.contains(r'Convert.*EMI|ConverttoEMI', case=False, regex=True, na=False)
                    else:
                        df['_is_emi_purchase'] = False

                    # Payments
                    result["Payment_Count"] = int(df['_is_payment'].sum())
                    result["Payment_Amount"] = float(df[df['_is_payment']]['_amount'].sum())

                    # Refunds (credits that are not payments or EMI conversions)
                    refund_mask = (df['Type'] == 'Credit') & ~df['_is_payment'] & ~df['_is_emi_conv']
                    result["Refund_Count"] = int(refund_mask.sum())
                    result["Refund_Amount"] = float(df[refund_mask]['_amount'].sum())

                    # Spends (debits, excluding EMI conversions and EMI-converted purchases)
                    spend_mask = (df['Type'] == 'Debit') & ~df['_is_emi_conv'] & ~df['_is_emi_purchase']
                    result["Spend_Count"] = int(spend_mask.sum())
                    result["Spend_Amount"] = float(df[spend_mask]['_amount'].sum())

                    # Net Spend = Spends - Refunds
                    result["Net_Spend"] = result["Spend_Amount"] - result["Refund_Amount"]

                elif 'Type' in df.columns:
                    # Fallback if no Category column
                    result["Spend_Count"] = len(df[df['Type'] == 'Debit'])
                    result["Spend_Amount"] = float(df[df['Type'] == 'Debit']['_amount'].sum())
                    result["Refund_Count"] = len(df[df['Type'] == 'Credit'])
                    result["Refund_Amount"] = float(df[df['Type'] == 'Credit']['_amount'].sum())
                    result["Net_Spend"] = result["Spend_Amount"] - result["Refund_Amount"]

                result["Status"] = "Success"

                # Save the results
                extractor.save_results(df)
    except Exception as e:
        result["Status"] = f"Error: {str(e)[:50]}"

    return result


def main():
    """Main execution."""
    pdf_dir = Path("encrypted_pdf")
    pdf_files = list(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found in 'encrypted_pdf' folder.")
        return

    print(f"Found {len(pdf_files)} PDF files to process\n")
    print("="*80)

    metadata_rows = []

    for pdf_file in sorted(pdf_files):
        print(f"\nProcessing: {pdf_file.name}")

        extractor_class, bank_name = get_extractor_for_file(pdf_file.name)

        if extractor_class is None:
            print(f"  ⚠ No extractor found for this file pattern")
            metadata_rows.append({
                "Filename": pdf_file.name,
                "Month": get_month_from_filename(str(pdf_file)),
                "Bank/CC": "Unknown",
                "Period_From": "",
                "Period_To": "",
                "Total_Transactions": 0,
                "Payment_Count": 0,
                "Payment_Amount": 0.0,
                "Refund_Count": 0,
                "Refund_Amount": 0.0,
                "Spend_Count": 0,
                "Spend_Amount": 0.0,
                "Net_Spend": 0.0,
                "Status": "No extractor"
            })
            continue

        print(f"  Bank/CC: {bank_name}")
        print(f"  Extractor: {extractor_class.__name__}")

        result = run_extractor(str(pdf_file), extractor_class, bank_name)
        metadata_rows.append(result)

        print(f"  Status: {result['Status']}")
        print(f"  Transactions: {result['Total_Transactions']} (Spends: {result['Spend_Count']}, Refunds: {result['Refund_Count']}, Payments: {result['Payment_Count']})")

    # Create metadata DataFrame
    metadata_df = pd.DataFrame(metadata_rows)

    # Reorder columns
    columns = [
        "Filename", "Month", "Bank/CC", "Period_From", "Period_To",
        "Total_Transactions", "Payment_Count", "Payment_Amount",
        "Refund_Count", "Refund_Amount", "Spend_Count", "Spend_Amount",
        "Net_Spend", "Status"
    ]
    metadata_df = metadata_df[columns]

    # Save to Excel
    output_path = "output/extraction_metadata.xlsx"
    os.makedirs("output", exist_ok=True)
    metadata_df.to_excel(output_path, index=False, sheet_name="Metadata")

    # Also save CSV
    csv_path = "output/extraction_metadata.csv"
    metadata_df.to_csv(csv_path, index=False)

    print("\n" + "="*80)
    print(f"\nMetadata saved to:")
    print(f"  - {output_path}")
    print(f"  - {csv_path}")

    # Print summary table
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(metadata_df.to_string(index=False))

    # Statistics
    success_count = len(metadata_df[metadata_df['Status'] == 'Success'])
    print(f"\n\nTotal files processed: {len(metadata_df)}")
    print(f"Successful extractions: {success_count}")
    print(f"Failed extractions: {len(metadata_df) - success_count}")


if __name__ == "__main__":
    main()
