from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.app.core.db import create_db_and_tables
from backend.app.api.routes import upload, transactions, stats, files

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
app.include_router(stats.router, prefix="/stats", tags=["Stats"])
app.include_router(files.router, prefix="/files", tags=["Files"])

@app.get("/")
def read_root():
    return {"message": "Welcome to ExpenseHelper API"}
