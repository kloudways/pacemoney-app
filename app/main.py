from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from .database import engine, Base, get_db
from . import models


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Pace Money", version="2.0.0", lifespan=lifespan)

Instrumentator().instrument(app).expose(app)


class TransactionIn(BaseModel):
    amount: float
    description: str
    category: str


class TransactionOut(TransactionIn):
    id: int

    model_config = {"from_attributes": True}


class SummaryOut(BaseModel):
    total: float
    by_category: dict[str, float]


@app.get("/health")
def health():
    return {"status": "ok", "app": "pacemoney", "version": app.version}


@app.get("/transactions", response_model=list[TransactionOut])
def list_transactions(db: Session = Depends(get_db)):
    return db.query(models.Transaction).all()


@app.get("/transactions/summary", response_model=SummaryOut)
def transaction_summary(db: Session = Depends(get_db)):
    rows = (
        db.query(
            models.Transaction.category,
            sa_func.sum(models.Transaction.amount).label("total"),
        )
        .group_by(models.Transaction.category)
        .all()
    )
    by_category = {row.category: round(row.total, 2) for row in rows}
    return SummaryOut(total=round(sum(by_category.values()), 2), by_category=by_category)


@app.get("/transactions/{tx_id}", response_model=TransactionOut)
def get_transaction(tx_id: int, db: Session = Depends(get_db)):
    db_tx = db.query(models.Transaction).filter(models.Transaction.id == tx_id).first()
    if not db_tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return db_tx


@app.post("/transactions", response_model=TransactionOut, status_code=201)
def create_transaction(tx: TransactionIn, db: Session = Depends(get_db)):
    db_tx = models.Transaction(**tx.model_dump())
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx


@app.delete("/transactions/{tx_id}", status_code=204)
def delete_transaction(tx_id: int, db: Session = Depends(get_db)):
    db_tx = db.query(models.Transaction).filter(models.Transaction.id == tx_id).first()
    if not db_tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(db_tx)
    db.commit()
