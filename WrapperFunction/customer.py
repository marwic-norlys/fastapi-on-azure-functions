import sqlite3
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import secrets

class Customer(BaseModel):
    phone: int
    customerId: int
    customerType: str

def init_db():
    conn = sqlite3.connect('customer.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers
        (phone INT, customerId INT, customerType TEXT, timestamp TEXT)
    ''')
    conn.commit()
    conn.close()

init_db()   

router = APIRouter()

security = HTTPBasic()

def authenticate_user(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "norlys_voicebot01")
    correct_password = secrets.compare_digest(credentials.password, "#}7Q1~0]|AZk5R@")
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@router.post("/customer", tags=["Voicebot"])
async def create_customer(customer: Customer, username: str = Depends(authenticate_user)):
    conn = sqlite3.connect('customer.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO customers VALUES (?, ?, ?, ?)
    ''', (customer.phone, customer.customerId, customer.customerType, datetime.now()))
    conn.commit()
    conn.close()
    return {"message": "Phone updated OK"}

@router.get("/customers/{phone}", tags=["Voicebot"])
async def get_customer(phone: int, username: str = Depends(authenticate_user)):
    conn = sqlite3.connect('customer.db')
    c = conn.cursor()
    c.execute('SELECT customerId, customerType FROM customers WHERE phone = ?', (phone,))
    customer = c.fetchone()
    conn.close()
    if customer is None:
        return {"customerId": None, "customerType": None}
    else:
        return {"customerId": customer[0], "customerType": customer[1]}
    
## Martin consider
## Timestamp in GET, so we only return data if less than 7 day old
## Add HTTP status codes