import os
import sys
from backend.app.extractors.factory import get_extractor

UPLOAD_DIR = "uploads"

def main():
    if not os.path.exists(UPLOAD_DIR):
        print(f"Directory {UPLOAD_DIR} does not exist.")
        return

    files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith('.pdf')]
    print(f"Found {len(files)} PDFs in {UPLOAD_DIR}")

    success_count = 0
    fail_count = 0

    for filename in files:
        file_path = os.path.join(UPLOAD_DIR, filename)
        print(f"\nProcessing: {filename}")
        
        # Extract password from filename
        # Format: uuid_original_name_password.pdf OR just original_name.pdf
        # The user's code in Upload.jsx does: file_password.pdf -> password
        # But backend saves as: uuid_filename.
        # So we look for the last part after underscore.
        
        password = None
        # Try to infer password from filename parts
        # e.g. ..._dec_RAJE0609.pdf -> RAJE0609
        name_without_ext = filename.rsplit('.', 1)[0]
        parts = name_without_ext.split('_')
        
        # Heuristic: the last part might be the password if it's alphanumeric
        if len(parts) > 1:
            potential_password = parts[-1]
            # Some specific known passwords from previous logs/context if needed
            # But let's try the potential one.
            password = potential_password
            print(f"  Inferred password: {password}")
        
        try:
            extractor = get_extractor(file_path, password)
            
            if not extractor:
                print("  [FAIL] No extractor identified.")
                fail_count += 1
                continue
            
            print(f"  [OK] Identified: {extractor.__class__.__name__}")
            
            transactions = extractor.extract()
            if len(transactions) == 0:
                 print(f"  [WARNING] Extracted 0 transactions! This might be a parsing issue.")
                 fail_count += 1
            else:
                 print(f"  [OK] Extracted {len(transactions)} transactions.")
                 print(f"  Sample: {transactions[0]}")
                 success_count += 1

        except Exception as e:
            print(f"  [ERROR] {e}")
            fail_count += 1

    print(f"\nSummary: {success_count} succeeded, {fail_count} failed out of {len(files)} files.")

if __name__ == "__main__":
    # Add project root to path so we can import backend modules
    sys.path.append(os.getcwd())
    main()
