# ExpenseHelper

A full-stack application for managing and analyzing personal expenses from bank statements.

## 🚀 Features

- **Automated PDF Parsing**: Extract transactions from bank statements (HDFC, Kotak, SBI, etc.).
- **Interactive Dashboard**: Visualize spending trends and categorize transactions.
- **Secure Handling**: Encrypted PDF support with local processing.
- **Modern UI**: Clean, responsive interface built with React and Tailwind CSS.

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React + Vite
- **Database**: SQLite (local)
- **PDF Engine**: `pdfplumber`

## 🏃‍♂️ Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+

### 1. Setup Backend
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Setup Frontend
```bash
cd frontend
npm install
```

### 3. Run Application
Use the helper script to start both servers:
```bash
./run_app.sh
```
Access the app at `http://localhost:5173`.

## 📂 Project Structure
- `backend/`: FastAPI application and extractors.
- `frontend/`: React application.
- `uploads/`: Temporary storage for uploaded PDFs.
