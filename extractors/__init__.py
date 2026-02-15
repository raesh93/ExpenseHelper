"""
Extractors package for PDF statement extraction.
"""

from .base import BaseExtractor, CreditCardExtractor, DebitAccountExtractor
from .icici_cc import ICICICCExtractor, PDFTableExtractor
from .hdfc_cc import HDFCCCExtractor
from .sbi_cc import SBICCExtractor
from .kotak_cc import KotakCCExtractor
from .kotak_debit import KotakDebitExtractor, KotakExtractor
from .bob_debit import BOBDebitExtractor, BOBExtractor
from .niyo_dcb import NiyoDCBExtractor

# Registry: maps file patterns to extractor classes and bank names
EXTRACTOR_REGISTRY = [
    {"pattern": "5241*", "extractor": HDFCCCExtractor, "bank": "HDFC CC"},
    {"pattern": "0992*", "extractor": SBICCExtractor, "bank": "SBI CC"},
    {"pattern": "5879*", "extractor": BOBDebitExtractor, "bank": "BOB Debit"},
    {"pattern": "Email_Bank_Statement_*", "extractor": NiyoDCBExtractor, "bank": "Niyo DCB"},
    {"pattern": "6528*", "extractor": ICICICCExtractor, "bank": "ICICI Coral CC"},
    {"pattern": "4315*", "extractor": ICICICCExtractor, "bank": "Amazon ICICI CC"},
    {"pattern": "00114*", "extractor": KotakCCExtractor, "bank": "Kotak CC"},
    {"pattern": "00116*", "extractor": KotakCCExtractor, "bank": "Kotak CC"},
    {"pattern": "6006*", "extractor": KotakDebitExtractor, "bank": "Kotak Debit"},
    {"pattern": "27065*", "extractor": KotakDebitExtractor, "bank": "Kotak Debit"},
]

# Bank name to extractor class mapping (for UI)
BANK_EXTRACTOR_MAP = {
    "HDFC CC": HDFCCCExtractor,
    "SBI CC": SBICCExtractor,
    "BOB Debit": BOBDebitExtractor,
    "Niyo DCB": NiyoDCBExtractor,
    "ICICI Coral CC": ICICICCExtractor,
    "Amazon ICICI CC": ICICICCExtractor,
    "Kotak CC": KotakCCExtractor,
    "Kotak Debit": KotakDebitExtractor,
}

__all__ = [
    # Base classes
    "BaseExtractor",
    "CreditCardExtractor",
    "DebitAccountExtractor",
    # Extractors
    "ICICICCExtractor",
    "PDFTableExtractor",  # Alias
    "HDFCCCExtractor",
    "SBICCExtractor",
    "KotakCCExtractor",
    "KotakDebitExtractor",
    "KotakExtractor",  # Alias
    "BOBDebitExtractor",
    "BOBExtractor",  # Alias
    "NiyoDCBExtractor",
    # Registry
    "EXTRACTOR_REGISTRY",
    "BANK_EXTRACTOR_MAP",
]
