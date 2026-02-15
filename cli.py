"""
CLI entry point for running all extractors.
"""

import os
import re
from pathlib import Path
import pandas as pd
import pdfplumber

from extractors import (
    EXTRACTOR_REGISTRY,
    ICICICCExtractor,
    BaseExtractor,
)

# Payment categories for classification
PAYMENT_CATEGORIES = ['Payment', 'NEFT Transfer', 'IMPS', 'UPI']


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
    for mapping in EXTRACTOR_REGISTRY:
        pattern = mapping["pattern"]
        regex_pattern = pattern.replace("*", ".*")
        if re.match(regex_pattern, filename):
            return mapping["extractor"], mapping["bank"]
    return None, "Unknown"


def extract_statement_period(pdf_path: str) -> tuple:
    """Try to extract statement period from PDF."""
    from_date = ""
    to_date = ""

    password = BaseExtractor.get_password_from_filename(pdf_path)

    try:
        try:
            pdf = pdfplumber.open(pdf_path)
        except Exception:
            pdf = pdfplumber.open(pdf_path, password=password)

        with pdf:
            text = pdf.pages[0].extract_text() or ""

            patterns = [
                r'Statement Period[:\s]+(?:from\s+)?(\w+\s+\d{1,2},?\s+\d{4})\s+(?:to|-)\s+(\w+\s+\d{1,2},?\s+\d{4})',
                r'(\d{1,2}-\d{1,2}-\d{4})\s+To\s+(\d{1,2}-\d{1,2}-\d{4})',
                r'Billing Period[:\s]+(\d{1,2}\s+\w+,?\s+\d{4})\s*[-–]\s*(\d{1,2}\s+\w+,?\s+\d{4})',
                r'Statement Period[:\s]+(\d{1,2}\s+\w+\s+\d{2,4})\s+to\s+(\d{1,2}\s+\w+\s+\d{2,4})',
            ]

            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    from_date = match.group(1)
                    to_date = match.group(2)
                    break
    except Exception:
        pass

    return from_date, to_date


def classify_transactions(df: pd.DataFrame) -> dict:
    """Classify transactions into payments, refunds, and spends."""
    result = {
        "Payment_Count": 0,
        "Payment_Amount": 0.0,
        "Refund_Count": 0,
        "Refund_Amount": 0.0,
        "Spend_Count": 0,
        "Spend_Amount": 0.0,
        "Net_Spend": 0.0,
    }

    if df is None or df.empty:
        return result

    if 'Amount' in df.columns:
        df = df.copy()
        df['_amount'] = pd.to_numeric(
            df['Amount'].astype(str).str.replace(',', '', regex=False),
            errors='coerce'
        ).fillna(0)

    if 'Type' not in df.columns:
        return result

    if 'Category' in df.columns:
        df['_is_payment'] = (df['Type'] == 'Credit') & df['Category'].isin(PAYMENT_CATEGORIES)

        emi_conversion_cats = ['EMI Conversion']
        df['_is_emi_conv'] = df['Category'].isin(emi_conversion_cats)

        if 'Description' in df.columns:
            df['_is_emi_purchase'] = df['Description'].str.contains(
                r'Convert.*EMI|ConverttoEMI', case=False, regex=True, na=False
            )
        else:
            df['_is_emi_purchase'] = False

        result["Payment_Count"] = int(df['_is_payment'].sum())
        result["Payment_Amount"] = float(df[df['_is_payment']]['_amount'].sum())

        refund_mask = (df['Type'] == 'Credit') & ~df['_is_payment'] & ~df['_is_emi_conv']
        result["Refund_Count"] = int(refund_mask.sum())
        result["Refund_Amount"] = float(df[refund_mask]['_amount'].sum())

        spend_mask = (df['Type'] == 'Debit') & ~df['_is_emi_conv'] & ~df['_is_emi_purchase']
        result["Spend_Count"] = int(spend_mask.sum())
        result["Spend_Amount"] = float(df[spend_mask]['_amount'].sum())
    else:
        result["Spend_Count"] = len(df[df['Type'] == 'Debit'])
        result["Spend_Amount"] = float(df[df['Type'] == 'Debit']['_amount'].sum())
        result["Refund_Count"] = len(df[df['Type'] == 'Credit'])
        result["Refund_Amount"] = float(df[df['Type'] == 'Credit']['_amount'].sum())

    result["Net_Spend"] = result["Spend_Amount"] - result["Refund_Amount"]

    return result


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

        if extractor_class == ICICICCExtractor:
            tables = extractor.extract_tables()
            if tables and len(tables) > 0:
                df = tables[0]
                result["Total_Transactions"] = len(df)

                if 'Amount (in`)' in df.columns:
                    df = df.copy()
                    df['_amount_str'] = df['Amount (in`)'].astype(str)
                    df['_is_credit'] = df['_amount_str'].str.contains('CR', case=False, na=False)
                    df['Amount'] = df['_amount_str'].str.replace('CR', '', case=False).str.replace(',', '').str.strip()
                    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
                    df['Type'] = df['_is_credit'].map({True: 'Credit', False: 'Debit'})

                    if 'Transaction Details' in df.columns:
                        payment_keywords = ['payment', 'bbps', 'neft', 'imps', 'upi.*received', 'paid']
                        df['_is_payment'] = (
                            df['Transaction Details'].str.lower().str.contains(
                                '|'.join(payment_keywords), regex=True, na=False
                            ) & df['_is_credit']
                        )
                    else:
                        df['_is_payment'] = False

                    result["Payment_Count"] = int(df['_is_payment'].sum())
                    result["Payment_Amount"] = float(df[df['_is_payment']]['Amount'].sum())

                    refund_mask = df['_is_credit'] & ~df['_is_payment']
                    result["Refund_Count"] = int(refund_mask.sum())
                    result["Refund_Amount"] = float(df[refund_mask]['Amount'].sum())

                    result["Spend_Count"] = int((~df['_is_credit']).sum())
                    result["Spend_Amount"] = float(df[~df['_is_credit']]['Amount'].sum())

                    result["Net_Spend"] = result["Spend_Amount"] - result["Refund_Amount"]

                result["Status"] = "Success"

                pdf_name = Path(pdf_path).stem
                output_folder = Path("output") / pdf_name
                output_folder.mkdir(parents=True, exist_ok=True)

                df_save = df.copy()
                if 'Transaction Details' in df_save.columns:
                    df_save = df_save.rename(columns={'Transaction Details': 'Description'})

                save_cols = ['Date', 'Description', 'Reward Points', 'Amount', 'Type']
                save_cols = [c for c in save_cols if c in df_save.columns]
                df_save = df_save[save_cols]
                df_save.to_csv(output_folder / "transactions.csv", index=False)
                df_save.to_excel(output_folder / "transactions.xlsx", index=False)
        else:
            df = extractor.extract_transactions()
            if df is not None and not df.empty:
                result["Total_Transactions"] = len(df)

                classification = classify_transactions(df)
                result.update(classification)

                result["Status"] = "Success"

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
    print("=" * 80)

    metadata_rows = []

    for pdf_file in sorted(pdf_files):
        print(f"\nProcessing: {pdf_file.name}")

        extractor_class, bank_name = get_extractor_for_file(pdf_file.name)

        if extractor_class is None:
            print(f"  No extractor found for this file pattern")
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

    metadata_df = pd.DataFrame(metadata_rows)

    columns = [
        "Filename", "Month", "Bank/CC", "Period_From", "Period_To",
        "Total_Transactions", "Payment_Count", "Payment_Amount",
        "Refund_Count", "Refund_Amount", "Spend_Count", "Spend_Amount",
        "Net_Spend", "Status"
    ]
    metadata_df = metadata_df[columns]

    output_path = "output/extraction_metadata.xlsx"
    os.makedirs("output", exist_ok=True)
    metadata_df.to_excel(output_path, index=False, sheet_name="Metadata")

    csv_path = "output/extraction_metadata.csv"
    metadata_df.to_csv(csv_path, index=False)

    print("\n" + "=" * 80)
    print(f"\nMetadata saved to:")
    print(f"  - {output_path}")
    print(f"  - {csv_path}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(metadata_df.to_string(index=False))

    success_count = len(metadata_df[metadata_df['Status'] == 'Success'])
    print(f"\n\nTotal files processed: {len(metadata_df)}")
    print(f"Successful extractions: {success_count}")
    print(f"Failed extractions: {len(metadata_df) - success_count}")


if __name__ == "__main__":
    main()
