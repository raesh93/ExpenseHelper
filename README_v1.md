# ExpenseHelper - PDF Table Extraction & Analysis

A Python-based tool to extract tables from PDFs (particularly bank statements), consolidate tables with identical schemas, and organize transactions by date.

## Features

✅ **PDF Table Extraction**
- Uses `pdfplumber` for reliable table detection
- Fallback text-based extraction for structured data
- Handles both traditional table layouts and line-formatted data

✅ **Schema-based Consolidation**
- Automatically identifies tables with matching column structures
- Merges tables with identical schemas
- Removes duplicate rows

✅ **Date-based Sorting**
- Automatically detects date columns
- Parses various date formats
- Sorts consolidated data chronologically

✅ **Multiple Output Formats**
- CSV (comma-separated values)
- XLSX (Excel workbooks)
- JSON (summary metadata)

## Project Structure

```
ExpenseHelper/
├── extract_tables.py          # Main extraction script
├── verify_output.py           # Verification and analysis script
├── requirements.txt           # Python dependencies
├── encrypted_pdf/             # Input PDF files (your bank statements)
├── output/                    # Extracted and processed data
│   ├── *.csv                  # CSV exports
│   ├── *.xlsx                 # Excel exports
│   └── summary.json           # Extraction metadata
└── venv/                      # Python virtual environment
```

## Installation

### Prerequisites
- Python 3.9+
- macOS, Linux, or Windows

### Setup

1. Navigate to the project directory:
```bash
cd /Users/babumoshai/Documents/projects/ExpenseHelper
```

2. Create and activate virtual environment (if not already done):
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Extraction

Place your PDF files in the `encrypted_pdf/` folder, then run:

```bash
python extract_tables.py
```

This will:
1. Extract all tables from each PDF in `encrypted_pdf/`
2. Consolidate tables with matching schemas
3. Sort by date column (if found)
4. Save results in `output/` directory

### Verify Extraction Results

After running the extraction, verify the results:

```bash
python verify_output.py
```

This will display:
- Number of transactions extracted
- Date range covered
- Sample transactions
- Summary statistics (total spent, average, highest transaction)

## Output Files

For each PDF processed, you'll get:

- **CSV Files**: Easy to import into spreadsheets or databases
- **XLSX Files**: Excel workbooks with formatted data
- **summary.json**: Metadata about extraction including:
  - Extraction timestamp
  - Source PDF
  - Number of tables extracted
  - Schema information for each table

## Example Output

For the ICICI bank statement example:

```
✅ FINAL EXTRACTION RESULTS

Total transactions extracted: 54
Transactions with complete dates: 21
Source: Both text extraction (page 1) and table extraction (page 2)

Data Structure:
- Date, SerNo., Transaction Details, Reward Points, Intl.# amount, Amount (in`)
- Intl.# amount column is consistently blank (as per bank statement)
- Data properly sorted by date

Sample transactions captured:
  ✓ UPI-based payments (Swiggy, Medplus, Blinkit, etc.)
  ✓ Retail purchases (Levi Strauss, Malabar Crystals)
  ✓ Healthcare (Sagar Hospitals, Orange Health)
  ✓ Food & Delivery services
  
Total transaction amounts captured and sortable
Reward points properly extracted
```

## How It Works

### 1. PDF Table Extraction
- Uses `pdfplumber`'s table detection algorithm
- Handles complex layouts with multiple tables per page

### 2. Text-based Fallback
- For structured data not detected as tables
- Parses line-based transaction records
- Identifies patterns (dates, amounts, descriptions)

### 3. Schema Matching
- Groups tables by column structure
- Identifies tables with identical column names
- Merges matching tables while preserving data

### 4. Date-based Sorting
- Detects common date column patterns
- Parses dates in standard formats (DD/MM/YYYY, DD-MM-YYYY, etc.)
- Sorts consolidated data chronologically

## Dependencies

- **pdfplumber** (0.10.3): PDF text and table extraction
- **pandas** (2.1.3): Data manipulation and analysis
- **openpyxl** (3.2.0b1): Excel file writing
- **python-dateutil** (2.8.2): Date parsing utilities
- **Pillow**: Image processing for PDF rendering
- **pypdfium2**: PDF document handling

## Limitations & Known Issues

1. **PDF Quality**: Works best with clearly formatted PDFs
2. **Text Encoding**: Some PDFs may have encoding issues causing character artifacts
3. **Multi-line Data**: Text-based extraction may incorrectly split multi-line transaction descriptions
4. **Date Parsing**: Non-standard date formats may not be automatically detected

## Future Enhancements

- [ ] Support for password-protected PDFs
- [ ] OCR support for scanned documents
- [ ] Database export (SQLite, PostgreSQL)
- [ ] GUI interface
- [ ] Categorization of transactions
- [ ] Integration with accounting software
- [ ] Duplicate transaction detection across multiple statements

## Troubleshooting

### No tables extracted
- Check PDF format and quality
- Verify PDF contains actual table structures
- Try viewing PDF in different readers to ensure tables are visible

### Incorrect date parsing
- Check date format in source PDF
- Update `find_date_column()` method for custom date patterns
- Manually inspect extracted CSV for date consistency

### Memory issues with large PDFs
- Process PDFs individually
- Consider splitting large PDFs into smaller sections

## License

This project is for personal use. Modify and extend as needed.

## Author

Created for ExpenseHelper project - Bank statement analysis and consolidation
