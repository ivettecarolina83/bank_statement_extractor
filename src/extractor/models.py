from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class Transaction(BaseModel):
    date: str = Field(..., description="ISO date YYYY-MM-DD")
    description: str
    amount: float = Field(..., description="Signed amount. Negative=outflow, Positive=inflow")
    balance: Optional[float] = None


class Account(BaseModel):
    name: str
    last4: Optional[str] = None
    currency: str = "USD"
    transactions: List[Transaction] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    bank: str
    statement_year: Optional[int] = None
    accounts: List[Account] = Field(default_factory=list)
