from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

from .database import engine, Base, get_db
from . import models


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Pace Money", version="1.0.0", lifespan=lifespan)

REQUEST_COUNT = Counter(
    "pacemoney_requests_total",
    "Total HTTP requests",
    ["method", "path"],
)


class TransactionIn(BaseModel):
    amount: float
    description: str
    category: str


class TransactionOut(TransactionIn):
    id: int

    model_config = {"from_attributes": True}


@app.get("/health")
def health():
    return {"status": "ok", "app": "pacemoney"}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/transactions", response_model=list[TransactionOut])
def list_transactions(db: Session = Depends(get_db)):
    REQUEST_COUNT.labels(method="GET", path="/transactions").inc()
    return db.query(models.Transaction).all()


@app.post("/transactions", response_model=TransactionOut, status_code=201)
def create_transaction(tx: TransactionIn, db: Session = Depends(get_db)):
    REQUEST_COUNT.labels(method="POST", path="/transactions").inc()
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
