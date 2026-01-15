#!/bin/bash
# Quick start script for ExpenseHelper

echo "🏦 ExpenseHelper - PDF Table Extraction Tool"
echo "============================================"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install/upgrade dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Create output directory
mkdir -p output

# Run extraction
echo ""
echo "🔍 Extracting tables from PDFs in encrypted_pdf/ folder..."
echo ""
python extract_tables.py

echo ""
echo "✅ Extraction complete!"
echo ""
echo "📁 Output files saved to: output/"
