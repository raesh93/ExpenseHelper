import os
import sys
from pathlib import Path

# Add the project root to sys.path so we can import backend
sys.path.append(os.getcwd())

from backend.app.extractors.factory import get_extractor
from backend.app.models import Transaction

def main():
    pdf_dir = Path("encrypted_pdf")
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in 'encrypted_pdf'")
        return

    total_txns = 0
    
    for pdf_file in pdf_files:
        print(f"\nProcessing: {pdf_file.name}")
        
        # Get password from filename if present (simple check)
        # Assuming filename format: name_password.pdf or similar logic from utils
        password = None
        if "_" in pdf_file.stem:
            password = pdf_file.stem.split("_")[-1]

        extractor = get_extractor(str(pdf_file), password)
        
        if extractor:
            txns = extractor.extract()
            print(f"Extracted {len(txns)} transactions")
            
            if txns:
                print("Sample transactions:")
                for t in txns[:3]:
                    print(f"  {t.date} | {t.amount} | {t.type} | {t.description[:50]}...")
                
                total_txns += len(txns)
        else:
            print("Skipping - No suitable extractor found.")

    print(f"\nTotal transactions extracted across all files: {total_txns}")

if __name__ == "__main__":
    main()
