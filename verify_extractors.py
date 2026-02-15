from backend.app.extractors.factory import EXTRACTORS
from backend.app.extractors.base import BankExtractor
import sys

def verify_extractors():
    print(f"Verifying Extractors...")
    print(f"Total registered: {len(EXTRACTORS)}")
    
    expected = [
        "ICICICreditExtractor",
        "KotakDebitExtractor",
        "HDFCCreditExtractor",
        "SBICreditExtractor",
        "BobDebitExtractor",
        "NiyoExtractor",
        "KotakCreditExtractor"
    ]
    
    registered = [cls.__name__ for cls in EXTRACTORS]
    print(f"Registered classes: {registered}")
    
    missing = set(expected) - set(registered)
    if missing:
        print(f"ERROR: Missing extractors: {missing}")
        sys.exit(1)
        
    print("SUCCESS: All extractors registered correctly.")

if __name__ == "__main__":
    verify_extractors()
