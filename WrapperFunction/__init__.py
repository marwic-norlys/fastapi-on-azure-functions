import azure.functions as func
import fastapi
from .incidents import router as incidents_router # Import the prices router
from .prices import router as prices_router 
from .customer import router as customer_router  

app = fastapi.FastAPI(
    title="Chatbot Wrapper API",
    description="Dette API fungerer som en wrapper for forskellige services der kan anvendes af en bot."
)

# Include the incidents router
app.include_router(incidents_router)

# Include the prices router
app.include_router(prices_router)

# Include the prices router
app.include_router(customer_router)