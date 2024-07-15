import sqlite3
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import secrets
import httpx
from dotenv import load_dotenv
import os

class Customer(BaseModel):
    phone: int
    customerId: int
    customerType: str
    customerDar: str

def init_db():
    conn = sqlite3.connect('customer.db')
    c = conn.cursor()

    # Create customers table
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers
        (phone INT, customerId INT, customerType TEXT, customerDar TEXT, timestamp TEXT)
    ''')

    # Create lookup table
    c.execute('''
        CREATE TABLE IF NOT EXISTS lookups
        (
            record_id TEXT PRIMARY KEY,
            telephone_number INT,
            street_name TEXT,
            house_number TEXT,
            floor TEXT,
            zip_code TEXT,
            update_date TEXT,
            timestamp TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()   

router = APIRouter()

security = HTTPBasic()

load_dotenv()

def authenticate_user(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, os.getenv('USERNAME2'))
    correct_password = secrets.compare_digest(credentials.password, os.getenv('PASSWORD2'))
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect user or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# Route 1
@router.post("/customer", tags=["Genkendelse af telefonnummer"])
async def create_customer(customer: Customer, username: str = Depends(authenticate_user)):
    conn = sqlite3.connect('customer.db')
    c = conn.cursor()
    c.execute('SELECT phone FROM customers WHERE phone = ?', (customer.phone,))
    existing_customer = c.fetchone()
    if existing_customer:
        c.execute('''
            UPDATE customers SET customerId = ?, customerType = ?, timestamp = ?, customerDar = ? WHERE phone = ?
        ''', (customer.customerId, customer.customerType, datetime.now(), customer.customerDar, customer.phone))
        conn.commit()
        conn.close()
        return {"message": "Updated ok"}
    else:
        c.execute('''
            INSERT INTO customers VALUES (?, ?, ?, ?, ?)
        ''', (customer.phone, customer.customerId, customer.customerType, customer.customerDar, datetime.now()))
        conn.commit()
        conn.close()
        return {"message": "Created ok"}

# Route 2
@router.get("/customers/{phone}", tags=["Genkendelse af telefonnummer"], status_code=status.HTTP_200_OK)
async def get_customer(phone: int, username: str = Depends(authenticate_user)):
    conn = sqlite3.connect('customer.db')
    c = conn.cursor()
    c.execute('SELECT customerId, customerType, customerDar, timestamp FROM customers WHERE phone = ?', (phone,))
    customer = c.fetchone()
    conn.close()
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    else:
        return {"customerId": customer[0], "customerType": customer[1], "customerDar": customer[2], "timestamp": customer[3]}
    
# Route 3
@router.get("/lookup/{phone}", tags=["Genkendelse af telefonnummer"], status_code=status.HTTP_200_OK)
async def lookup_phone(phone: int, username: str = Depends(authenticate_user)):
    url = f"https://api.resights.dk/api/v2/teledata/search?telephone_number={phone}"
    headers = {
        "Authorization": os.getenv('AUTHORIZATION'),
        "Cookie": os.getenv('COOKIE')
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Error fetching data from Resights API")

    data = response.json()
    result = []
    
    conn = sqlite3.connect('customer.db')
    c = conn.cursor()
    for item in data:
        subscriber = item.get("subscriber", {})
        if subscriber.get("subscriber_type") == 3:
            record = {
                "record_id": subscriber.get("record_id"),
                "telephone_number": subscriber.get("telephone_number"),
                "street_name": subscriber.get("street_name"),
                "house_number": subscriber.get("house_number"),
                "floor": subscriber.get("floor"),
                "zip_code": subscriber.get("zip_code"),
                "update_date": subscriber.get("update_date")
            }
            result.append(record)

            # Insert the record into the lookups table
            c.execute('''
                INSERT OR REPLACE INTO lookups (record_id, telephone_number, street_name, house_number, floor, zip_code, update_date, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (record["record_id"], record["telephone_number"], record["street_name"], record["house_number"], record["floor"], record["zip_code"], record["update_date"], datetime.now()))

    conn.commit()
    conn.close()
    
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching records found")

    return result