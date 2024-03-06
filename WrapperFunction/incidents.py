from enum import Enum
from fastapi import APIRouter, HTTPException, Path
import httpx

router = APIRouter()

# Define an Enum class for the incident types
class IncidentType(str, Enum):
    uvarslet = "Uvarslet"
    varslet = "Varslet"

async def fetch_incidents():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.elnet.danskenergi.dk/api/incidents")
        response.raise_for_status()
        return response.json()
    
# Route 1
@router.get("/incidents/{incident_type}", tags=["Strømafbrydelser"])
async def get_incidents(incident_type: IncidentType = Path(..., description="Angiv hvilken type strømafbrydelse du vil hente.")):
    try:
        all_incidents = await fetch_incidents()
        filtered_incidents = [incident for incident in all_incidents if incident.get('incidentType') == incident_type.value]
        return filtered_incidents
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=f"Error fetching incidents from external API")
    

# Route 2
@router.get("/incidents/uvarslede/aktive", tags=["Strømafbrydelser"])
async def get_uvarslede():
    try:
        all_incidents = await fetch_incidents()
        filtered_incidents = [incident for incident in all_incidents
                              if    incident.get('incidentType') == "Uvarslet" and
                                    incident.get('endDate') is None and
                                    incident.get('cause') != "Test"
                            ]
        
        # Further reduce the data to only include 'title' and 'zipcodes'
        reduced_incidents = [{'created': incident['created'],
                              'title': incident['title'],
                              'comment': incident['comment'],
                              'cause': incident['cause'],
                              'supplierWeb': incident['supplierWeb'],
                              'zipcodes': incident['zipcodes'],
                              'centerLat': incident['centerLat'],
                              'centerLng': incident['centerLng'],
                              'radius': incident['radius'],
                              'effectedCustomers': incident['effectedCustomers']
                              } for incident in filtered_incidents]
        return reduced_incidents  # Return the reduced incidents

    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=f"Error fetching incidents from external API")
