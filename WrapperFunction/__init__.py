import azure.functions as func
import fastapi
from .incidents import router as incidents_router
from .prices import router as prices_router  # Import the prices router

app = fastapi.FastAPI(
    title="Chatbot Wrapper API",
    description="Dette API fungerer som en wrapper for forskellige services der kan anvendes af en bot."
)

# Include the incidents router
app.include_router(incidents_router)

# Include the prices router
app.include_router(prices_router)


# @app.get("/sample")
# async def index():
#     return {
#         "info": "Try /hello/Shivani for parameterized route.",
#     }


# @app.get("/hello/{name}")
# async def get_name(name: str):
#     return {
#         "name": name,
#     }
