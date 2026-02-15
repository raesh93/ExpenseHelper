from typing import List, Type, Optional
import pdfplumber
from backend.app.extractors.base import BankExtractor
from backend.app.extractors.icici_credit import ICICICreditExtractor
from backend.app.extractors.kotak_debit import KotakDebitExtractor
from backend.app.extractors.hdfc_credit import HDFCCreditExtractor
from backend.app.extractors.sbi_credit import SBICreditExtractor
from backend.app.extractors.bob_debit import BobDebitExtractor
from backend.app.extractors.niyo import NiyoExtractor
from backend.app.extractors.kotak_credit import KotakCreditExtractor

# Registry of available extractors
EXTRACTORS: List[Type[BankExtractor]] = [
    ICICICreditExtractor,
    KotakDebitExtractor,
    HDFCCreditExtractor,
    SBICreditExtractor,
    BobDebitExtractor,
    NiyoExtractor,
    KotakCreditExtractor,
]

def get_extractor(pdf_path: str, password: str = None) -> Optional[BankExtractor]:
    """
    Identifies and returns the appropriate extractor for the given PDF.
    """
    print(f"DEBUG: get_extractor called for {pdf_path} with password='{password}'")
    try:
        # Open PDF to read the first page text for identification
        with pdfplumber.open(pdf_path, password=password) as pdf:
            if not pdf.pages:
                print("DEBUG: No pages found in PDF")
                return None
            
            first_page_text = pdf.pages[0].extract_text() or ""
            print(f"DEBUG: First page text len: {len(first_page_text)}")
            print(f"DEBUG: First 100 chars: {first_page_text[:100]}")

            for extractor_cls in EXTRACTORS:
                if extractor_cls.can_handle(first_page_text):
                    print(f"Identified extractor: {extractor_cls.__name__} for {pdf_path}")
                    return extractor_cls(pdf_path, password)
            
            print(f"No suitable extractor found for {pdf_path}")
            return None
            
    except Exception as e:
        print(f"Error identifying PDF {pdf_path}: {repr(e)}")
        import traceback
        traceback.print_exc()
        return None
