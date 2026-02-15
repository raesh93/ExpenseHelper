import requests
import os
import time

BASE_URL = "http://127.0.0.1:8000"

def test_api():
    print("Waiting for server to start...")
    time.sleep(2)
    print("Testing API...")
    
    # 1. Check Root
    try:
        r = requests.get(f"{BASE_URL}/")
        print(f"Root: {r.status_code} - {r.json()}")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # 2. Upload PDF
    # We need a sample PDF. Let's look for one in encrypted_pdf
    pdf_files = [f for f in os.listdir("encrypted_pdf") if f.endswith(".pdf")]
    if not pdf_files:
        print("No PDFs found to test upload.")
        return

    sample_pdf = os.path.join("encrypted_pdf", pdf_files[0])
    print(f"Uploading {sample_pdf}...")
    
    password = None
    if "_" in sample_pdf:
        # Simple extraction logic as used before
        password = os.path.splitext(os.path.basename(sample_pdf))[0].split("_")[-1]

    with open(sample_pdf, "rb") as f:
        files = {"file": f}
        data = {"password": password} if password else {}
        r = requests.post(f"{BASE_URL}/upload/", files=files, data=data)
        print(f"Upload: {r.status_code}")
        if r.status_code == 200:
            print(r.json())
        else:
            print(r.text)

    # 3. List Transactions
    print("\nListing Transactions...")
    r = requests.get(f"{BASE_URL}/transactions/")
    print(f"Transactions: {r.status_code}")
    if r.status_code == 200:
        txns = r.json()
        print(f"Found {len(txns)} transactions")
        if txns:
            # 4. Update Transaction
            first_id = txns[0]['id']
            print(f"Updating transaction {first_id}...")
            r = requests.patch(f"{BASE_URL}/transactions/{first_id}", json={"category": "Food"})
            print(f"Update: {r.status_code} - {r.json()}")

    # 5. Stats
    print("\nFetching Stats...")
    r = requests.get(f"{BASE_URL}/stats/category")
    print(f"Category Stats: {r.status_code}")
    print(r.json())

if __name__ == "__main__":
    test_api()
