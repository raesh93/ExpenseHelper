"""
Streamlit app for PDF statement extraction experimentation.
Upload a PDF, view side-by-side with extracted transactions, and tag issues.
"""

import streamlit as st
import pandas as pd
import tempfile
import os
from pathlib import Path
from datetime import datetime
from pdf2image import convert_from_path
import pdfplumber

# Import extractors
from extract_tables import PDFTableExtractor
from extract_kotak import KotakExtractor
from extract_kotak_cc import KotakCCExtractor
from extract_hdfc_cc import HDFCCCExtractor
from extract_sbi_cc import SBICCExtractor
from extract_bob import BOBExtractor
from extract_niyo_dcb import NiyoDCBExtractor
from run_all_extractors import get_extractor_for_file, get_password_from_filename

# Bank to extractor mapping
BANK_EXTRACTOR_MAP = {
    "HDFC CC": HDFCCCExtractor,
    "SBI CC": SBICCExtractor,
    "BOB Debit": BOBExtractor,
    "Niyo DCB": NiyoDCBExtractor,
    "ICICI Coral CC": PDFTableExtractor,
    "Amazon ICICI CC": PDFTableExtractor,
    "Kotak CC": KotakCCExtractor,
    "Kotak Debit": KotakExtractor,
}

ISSUE_TAGS = [
    "",
    "Wrong Amount",
    "Wrong Date",
    "Missing Transaction",
    "Duplicate",
    "Wrong Description",
    "Wrong Type (Debit/Credit)",
    "Other"
]

st.set_page_config(
    page_title="ExpenseHelper - PDF Extractor",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("ExpenseHelper - PDF Extraction Lab")


def get_pdf_page_count(pdf_path: str, password: str = None) -> int:
    """Get the number of pages in a PDF."""
    try:
        if password:
            with pdfplumber.open(pdf_path, password=password) as pdf:
                return len(pdf.pages)
        else:
            with pdfplumber.open(pdf_path) as pdf:
                return len(pdf.pages)
    except:
        try:
            with pdfplumber.open(pdf_path, password=password) as pdf:
                return len(pdf.pages)
        except:
            return 0


def render_pdf_page(pdf_path: str, page_num: int, password: str = None):
    """Render a specific page of the PDF as an image."""
    try:
        # Try without password first (for unencrypted PDFs)
        try:
            images = convert_from_path(
                pdf_path,
                first_page=page_num,
                last_page=page_num,
                dpi=150
            )
            if images:
                return images[0]
        except:
            pass

        # Try with user password
        if password:
            try:
                images = convert_from_path(
                    pdf_path,
                    first_page=page_num,
                    last_page=page_num,
                    userpw=password,
                    dpi=150
                )
                if images:
                    return images[0]
            except:
                pass

            # Try with owner password (some PDFs use this instead)
            try:
                images = convert_from_path(
                    pdf_path,
                    first_page=page_num,
                    last_page=page_num,
                    ownerpw=password,
                    dpi=150
                )
                if images:
                    return images[0]
            except:
                pass

            # Try with both user and owner password
            images = convert_from_path(
                pdf_path,
                first_page=page_num,
                last_page=page_num,
                userpw=password,
                ownerpw=password,
                dpi=150
            )
            if images:
                return images[0]
    except Exception as e:
        st.error(f"Error rendering PDF (password: {password}): {e}")
    return None


def run_extraction(extractor) -> pd.DataFrame:
    """Run extraction and return normalized DataFrame."""
    try:
        if hasattr(extractor, 'extract_transactions'):
            df = extractor.extract_transactions()
            print(f"[DEBUG] extract_transactions returned {len(df) if df is not None else 'None'} rows")
        else:
            tables = extractor.extract_tables()
            df = tables[0] if tables else pd.DataFrame()
            print(f"[DEBUG] extract_tables returned {len(tables) if tables else 0} tables")

        if df is None or df.empty:
            return pd.DataFrame()

        # Normalize column names (handle None values)
        df.columns = [str(col).strip() if col is not None else f'col_{i}' for i, col in enumerate(df.columns)]

        # Rename common columns to standard names
        rename_map = {
            'Transaction Details': 'Description',
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        # Handle ICICI-style Amount with CR suffix
        if 'Amount (in`)' in df.columns:
            amount_col = df['Amount (in`)'].fillna('').astype(str)
            # Detect Credit transactions (ends with CR)
            is_credit = amount_col.str.strip().str.endswith('CR')
            # Clean amount - remove CR and commas
            clean_amount = amount_col.str.replace('CR', '', case=False, regex=False).str.replace(',', '', regex=False).str.strip()
            df['Amount'] = pd.to_numeric(clean_amount, errors='coerce').fillna(0)
            # Set Type based on CR suffix
            df['Type'] = is_credit.map({True: 'Credit', False: 'Debit'})
        elif 'Amount' in df.columns and ('Type' not in df.columns or df['Type'].isna().all() or (df['Type'] == '').all()):
            # Check if Amount has CR suffix
            amount_col = df['Amount'].fillna('').astype(str)
            if amount_col.str.contains('CR', case=False, na=False).any():
                is_credit = amount_col.str.strip().str.endswith('CR')
                clean_amount = amount_col.str.replace('CR', '', case=False, regex=False).str.replace(',', '', regex=False).str.strip()
                df['Amount'] = pd.to_numeric(clean_amount, errors='coerce').fillna(0)
                df['Type'] = is_credit.map({True: 'Credit', False: 'Debit'})

        # Ensure standard columns exist
        standard_cols = ['Date', 'Description', 'Amount', 'Type']
        for col in standard_cols:
            if col not in df.columns:
                df[col] = ''

        return df

    except Exception as e:
        st.error(f"Extraction error: {e}")
        return pd.DataFrame()


def save_feedback(df: pd.DataFrame, pdf_name: str):
    """Save tagged transactions to feedback folder."""
    feedback_dir = Path("feedback")
    feedback_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    feedback_file = feedback_dir / f"{Path(pdf_name).stem}_feedback_{timestamp}.csv"

    df.to_csv(feedback_file, index=False)
    return feedback_file


# Sidebar for file upload and settings
with st.sidebar:
    st.header("Upload PDF")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

    if uploaded_file:
        # Save to temp directory but keep original filename for password extraction
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_path, 'wb') as f:
            f.write(uploaded_file.getvalue())

        # Store in session state
        st.session_state['temp_path'] = temp_path
        st.session_state['filename'] = uploaded_file.name

        # Extract password from original filename
        password = get_password_from_filename(uploaded_file.name)
        st.session_state['password'] = password

        # Auto-detect bank type
        detected_class, detected_bank = get_extractor_for_file(uploaded_file.name)

        st.success(f"Uploaded: {uploaded_file.name}")
        st.info(f"Detected: **{detected_bank}**")
        st.text(f"Password: {password}")

        # Bank type override
        st.header("Bank Type")
        bank_options = list(BANK_EXTRACTOR_MAP.keys())
        default_idx = bank_options.index(detected_bank) if detected_bank in bank_options else 0
        selected_bank = st.selectbox(
            "Override if needed:",
            bank_options,
            index=default_idx,
            key="bank_select"
        )
        st.session_state['selected_bank'] = selected_bank

        # Extract button
        if st.button("Extract Transactions", type="primary"):
            st.session_state['run_extraction'] = True


# Main content area
if 'temp_path' in st.session_state and st.session_state.get('run_extraction'):
    temp_path = st.session_state['temp_path']
    password = st.session_state['password']
    selected_bank = st.session_state['selected_bank']

    # Get page count
    page_count = get_pdf_page_count(temp_path, password)

    # Run extraction
    with st.spinner("Extracting transactions..."):
        extractor_class = BANK_EXTRACTOR_MAP[selected_bank]
        extractor = extractor_class(temp_path)
        df = run_extraction(extractor)

    if df.empty:
        st.warning("No transactions extracted. Try a different bank type.")
    else:
        # Add issue columns
        if 'Issue Tag' not in df.columns:
            df['Issue Tag'] = ''
        if 'Notes' not in df.columns:
            df['Notes'] = ''

        # Store in session state
        st.session_state['transactions_df'] = df
        st.session_state['page_count'] = page_count

        st.success(f"Extracted {len(df)} transactions")

# Display side-by-side view
if 'transactions_df' in st.session_state:
    df = st.session_state['transactions_df']
    temp_path = st.session_state['temp_path']
    password = st.session_state['password']
    page_count = st.session_state.get('page_count', 1)

    # Create two columns
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("PDF Viewer")

        # Page navigation
        nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])

        with nav_col1:
            if st.button("< Prev"):
                if 'current_page' not in st.session_state:
                    st.session_state['current_page'] = 1
                if st.session_state['current_page'] > 1:
                    st.session_state['current_page'] -= 1

        with nav_col2:
            current_page = st.number_input(
                "Page",
                min_value=1,
                max_value=page_count,
                value=st.session_state.get('current_page', 1),
                key="page_input"
            )
            st.session_state['current_page'] = current_page
            st.caption(f"of {page_count}")

        with nav_col3:
            if st.button("Next >"):
                if 'current_page' not in st.session_state:
                    st.session_state['current_page'] = 1
                if st.session_state['current_page'] < page_count:
                    st.session_state['current_page'] += 1

        # Render PDF page
        page_num = st.session_state.get('current_page', 1)
        img = render_pdf_page(temp_path, page_num, password)
        if img:
            st.image(img, use_container_width=True)
        else:
            st.error("Could not render PDF page")

    with col2:
        st.subheader("Extracted Transactions")

        # Configure column settings for data editor
        column_config = {
            "Issue Tag": st.column_config.SelectboxColumn(
                "Issue Tag",
                help="Tag any issues with this transaction",
                options=ISSUE_TAGS,
                required=False
            ),
            "Notes": st.column_config.TextColumn(
                "Notes",
                help="Add notes about the issue",
                max_chars=200
            ),
            "Amount": st.column_config.NumberColumn(
                "Amount",
                format="%.2f"
            )
        }

        # Display editable table
        edited_df = st.data_editor(
            df,
            column_config=column_config,
            use_container_width=True,
            height=600,
            num_rows="fixed"
        )

        # Update session state with edits
        st.session_state['transactions_df'] = edited_df

    # Feedback section
    st.divider()
    st.subheader("Feedback & Export")

    # Show tagged issues count
    tagged_count = len(edited_df[edited_df['Issue Tag'] != ''])
    st.metric("Tagged Issues", tagged_count)

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        if st.button("Save Feedback", disabled=tagged_count == 0):
            tagged_df = edited_df[edited_df['Issue Tag'] != ''].copy()
            feedback_file = save_feedback(tagged_df, st.session_state['filename'])
            st.success(f"Saved {len(tagged_df)} tagged transactions to {feedback_file}")

    with col_b:
        if st.button("Export All to CSV"):
            export_path = Path("output") / f"{Path(st.session_state['filename']).stem}_export.csv"
            export_path.parent.mkdir(exist_ok=True)
            edited_df.to_csv(export_path, index=False)
            st.success(f"Exported to {export_path}")

    with col_c:
        if st.button("Clear & Start Over"):
            for key in ['temp_path', 'filename', 'password', 'selected_bank',
                       'run_extraction', 'transactions_df', 'page_count', 'current_page']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

else:
    # Welcome message
    st.info("Upload a PDF statement from the sidebar to get started.")

    st.markdown("""
    ### Supported Banks
    - HDFC Credit Card
    - SBI Credit Card
    - Bank of Baroda (Debit)
    - Niyo DCB
    - ICICI Coral Credit Card
    - Amazon ICICI Credit Card
    - Kotak Credit Card
    - Kotak Bank (Debit)

    ### How it works
    1. Upload a PDF statement
    2. The app auto-detects the bank type from filename
    3. Click "Extract Transactions" to process
    4. View PDF and transactions side-by-side
    5. Tag any issues you find in the "Issue Tag" column
    6. Save feedback for improving extraction accuracy
    """)
