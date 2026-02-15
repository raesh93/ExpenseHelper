import os
import requests
import time
from pathlib import Path

# Configuration
PDF_DIR = "encrypted_pdf"
API_URL = "http://127.0.0.1:8000/upload/"

def get_password_from_filename(filename):
    """Extract password from filename (last segment after underscores, before extension)."""
    # Example: 6528XXXXXXXX6007_774259_Retail_Coral_NORM_dec_raje0609.pdf -> raje0609
    stem = Path(filename).stem
    parts = stem.split('_')
    if parts:
        return parts[-1]
    return None

def batch_upload():
    print(f"Starting batch upload from {PDF_DIR}...")
    
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith('.pdf')]
    print(f"Found {len(pdf_files)} PDF files.")
    
    success_count = 0
    fail_count = 0
    
    for filename in pdf_files:
        file_path = os.path.join(PDF_DIR, filename)
        password = get_password_from_filename(filename)
        
        print(f"\nUploading {filename}...")
        print(f"Detected password: {password}")
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                data = {'password': password} if password else {}
                
                response = requests.post(API_URL, files=files, data=data)
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Success: {result.get('extractor')} - {result.get('transactions_saved')} transactions saved")
                    success_count += 1
                else:
                    print(f"❌ Failed: {response.status_code} - {response.text}")
                    fail_count += 1
                    
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            fail_count += 1
            
    print(f"\nBatch processing complete.")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")

if __name__ == "__main__":
    batch_upload()
