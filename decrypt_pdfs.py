"""
Decrypt PDFs from encrypted_pdf/ and save to decrypted/ folder.
Password is extracted from filename (last segment after '_').
"""

import os
from pathlib import Path
import pikepdf


def get_password_from_filename(filepath: str) -> str:
    """Extract password from filename (last segment after '_')."""
    filename = Path(filepath).stem
    parts = filename.split('_')
    return parts[-1] if parts else ""


def decrypt_pdf(src_path: str, dest_path: str, password: str) -> bool:
    """Decrypt a PDF and save to destination."""
    try:
        # Try opening without password first
        try:
            with pikepdf.open(src_path) as pdf:
                pdf.save(dest_path)
                return True
        except pikepdf.PasswordError:
            pass

        # Try with password
        if password:
            with pikepdf.open(src_path, password=password) as pdf:
                pdf.save(dest_path)
                return True

        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def main():
    src_dir = Path("encrypted_pdf")
    dest_dir = Path("decrypted")
    dest_dir.mkdir(exist_ok=True)

    pdf_files = list(src_dir.glob("*.pdf"))
    if not pdf_files:
        print("No PDF files found in encrypted_pdf/")
        return

    print(f"Found {len(pdf_files)} PDF(s) to decrypt\n")

    for pdf_file in pdf_files:
        print(f"Processing: {pdf_file.name}")
        password = get_password_from_filename(str(pdf_file))
        dest_path = dest_dir / pdf_file.name

        if dest_path.exists():
            print(f"  Skipped (already exists)")
            continue

        if decrypt_pdf(str(pdf_file), str(dest_path), password):
            print(f"  Saved to: {dest_path}")
        else:
            print(f"  Failed to decrypt")

    print("\nDone!")


if __name__ == "__main__":
    main()
