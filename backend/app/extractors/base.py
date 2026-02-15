from abc import ABC, abstractmethod
from typing import List
import pandas as pd
from backend.app.models import TransactionBase as Transaction # Alias for compatibility or use TransactionBase directly
# Actually the extractors should return the model that doesn't have ID yet, which is Transaction or TransactionCreate.
# Let's use Transaction which has table=True but id is optional.
from backend.app.models import Transaction

class BankExtractor(ABC):
    def __init__(self, pdf_path: str, password: str = None):
        self.pdf_path = pdf_path
        self.password = password

    @abstractmethod
    def extract(self) -> List[Transaction]:
        """Main method to return standardized transactions."""
        pass
    
    @classmethod
    @abstractmethod
    def can_handle(cls, first_page_text: str) -> bool:
        """Returns True if this extractor can handle the PDF content."""
        pass
