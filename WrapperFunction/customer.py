import sqlite3
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import secrets
import httpx
from dotenv import load_dotenv
import os
import requests

class Customer(BaseModel):
    phone: int
    customerId: int
    customerType: str
    customerDar: str

def init_db():
    conn = sqlite3.connect('local.db')
    c = conn.cursor()

    # Create customers table
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers
        (phone INT, customerId INT, customerType TEXT, customerDar TEXT, timestamp DATETIME)
    ''')

    # Create lookups table
    c.execute('''
        CREATE TABLE IF NOT EXISTS lookups
        (
            nummeroplysning_record_id TEXT PRIMARY KEY,
            dawa_id TEXT,
            telephone_number INT,
            street_name TEXT,
            house_number INT,
            floor TEXT,
            door TEXT,
            zip_code INT,
            nummeroplysning_update_date DATE,
            timestamp DATETIME
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
@router.post("/customer", tags=["Genkendelse"])
async def create_temporary_customer(customer: Customer, username: str = Depends(authenticate_user)):
    conn = sqlite3.connect('local.db')
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
@router.get("/customers/{phone}", tags=["Genkendelse"], status_code=status.HTTP_200_OK)
async def get_temporary_customer(phone: int, username: str = Depends(authenticate_user)):
    conn = sqlite3.connect('local.db')
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
@router.get("/lookup/{phone}", tags=["Genkendelse"], status_code=status.HTTP_200_OK)
async def lookup_phone(phone: int, username: str = Depends(authenticate_user)):
    conn = sqlite3.connect('local.db')
    c = conn.cursor()
    
    # Ensure phone number is 8 digits or less
    phone = str(phone)[-8:]

    try:
        # Check local database for the phone number with timedelta logic
        c.execute('SELECT * FROM lookups WHERE telephone_number = ? AND timestamp >= ?', (phone, datetime.now() - timedelta(days=30)))
        local_data = c.fetchone()
        
        if local_data:
            # If a match is found in the local database, return it
            record = {
                "nummeroplysning_record_id": local_data[0],
                "dawa_id": local_data[1],
                "telephone_number": local_data[2],
                "street_name": local_data[3],
                "house_number": local_data[4],
                "floor": local_data[5],
                "door": local_data[6],
                "zip_code": local_data[7],
                "nummeroplysning_update_date": local_data[8],
                "timestamp": local_data[9]
            }
            return [record]

        # If no match, query the external API
        url = f"https://api.resights.dk/api/v2/teledata/search?telephone_number={phone}"
        headers = {
            "Authorization": os.getenv('AUTHORIZATION'),
            "Cookie": os.getenv('COOKIE')
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="No results from Resights Nummeroplysning API")

        data = response.json()
        result = []

        for item in data:
            subscriber = item.get("subscriber", {})
            if subscriber.get("subscriber_type") == 3:
                record = {
                    "nummeroplysning_record_id": subscriber.get("record_id"),
                    "telephone_number": subscriber.get("telephone_number"),
                    "street_name": subscriber.get("street_name"),
                    "house_number": subscriber.get("house_number"),
                    "floor": subscriber.get("floor"),
                    "zip_code": subscriber.get("zip_code"),
                    "nummeroplysning_update_date": subscriber.get("update_date")
                }

                # Construct address string for DAWA using list comprehension
                address_string = ' '.join(
                    str(value) for key, value in record.items() 
                    if key in ['street_name', 'house_number', 'floor', 'zip_code'] and value
                ).strip()
                
                # Initialize variables
                dawa_id = dawa_vejnavn = dawa_husnr = dawa_postnr = dawa_etage = dawa_dor = None

                # Call the external API
                api_url = f"https://api.dataforsyningen.dk/datavask/adresser?betegnelse={address_string}"
                api_response = requests.get(api_url)
                api_data = api_response.json()

                # Check the "kategori" in the response
                if api_data.get("kategori") == "B":
                    adresse = api_data["resultater"][0].get("adresse", {})
                    dawa_id = adresse.get("id")
                    dawa_vejnavn = adresse.get("vejnavn")
                    dawa_husnr = adresse.get("husnr")
                    dawa_postnr = adresse.get("postnr")
                    dawa_etage = adresse.get("etage")
                    dawa_dor = adresse.get("dør")

                    # Update the existing record with new data
                    record.update({
                        "dawa_id": dawa_id,
                        "street_name": dawa_vejnavn,
                        "house_number": dawa_husnr,
                        "zip_code": dawa_postnr,
                        "floor": dawa_etage,
                        "door": dawa_dor
                    })

                else:
                    # Handle a bad response
                    raise HTTPException(
                        status_code=api_response.status_code,
                        detail=f"No kategori B data {api_url}. Status code: {api_response.status_code}"
                    )
                    
                result.append(record)

                # Insert the record into the lookups table
                c.execute('''
                    INSERT OR REPLACE INTO lookups (nummeroplysning_record_id, dawa_id, telephone_number, street_name, house_number, floor, door, zip_code, nummeroplysning_update_date, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (record["nummeroplysning_record_id"], dawa_id, record["telephone_number"], dawa_vejnavn, dawa_husnr, dawa_etage, dawa_dor, dawa_postnr, record["nummeroplysning_update_date"], datetime.now()))

        conn.commit()

        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching records found in Resights Nummeroplysning API")

        return result
    
    finally:
        # Ensure that the cursor and connection are closed
        c.close()
        conn.close()