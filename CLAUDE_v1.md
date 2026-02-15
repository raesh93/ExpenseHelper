# ExpenseHelper

PDF table extraction tool for bank and credit card statements.

## Scripts

- `extract_tables.py` - ICICI credit card statement extraction
- `extract_kotak.py` - Kotak Bank statement extraction

## Running

Always activate venv first:
```bash
source venv/bin/activate && python extract_tables.py
source venv/bin/activate && python extract_kotak.py
```

## How it works

1. PDFs go in `encrypted_pdf/` folder
2. Password is extracted from filename (last segment after `_`)
3. Transactions are extracted and saved to `output/<pdf_name>/`

## Output formats

- CSV and Excel files
- JSON summary with metadata

## Adding new banks

Each bank has different PDF formats. Create a new `extract_<bank>.py` script following the pattern of existing extractors.
