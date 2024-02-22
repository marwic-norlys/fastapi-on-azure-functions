from enum import Enum
from fastapi import APIRouter, HTTPException, Path
import httpx

router = APIRouter()

# Define an Enum class for the incident types
class IncidentType(str, Enum):
    uvarslet = "Uvarslet"
    varslet = "Varslet"

# Update the route to use the Enum
@router.get("/incidents/{incident_type}", tags=["Strømafbrydelser"])
async def get_incidents(incident_type: IncidentType = Path(..., description="Angiv hvilken type strømafbrydelse du vil hente.")):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.elnet.danskenergi.dk/api/incidents")
            response.raise_for_status()  # This will raise an exception for HTTP error responses
            all_incidents = response.json()  # Parse the JSON response

            # Filter the incidents based on the incident_type path parameter
            filtered_incidents = [incident for incident in all_incidents if incident.get('incidentType') == incident_type.value]

            return filtered_incidents  # Return the filtered incidents

    except httpx.HTTPStatusError as exc:
        # You can customize the error message and HTTP status code as needed
        raise HTTPException(status_code=exc.response.status_code, detail=f"Error fetching incidents from external API")