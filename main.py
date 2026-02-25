from fastapi import FastAPI
import uvicorn
from api.routes import router as api_router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="LangChain Runner Service",
    description="Microservice to execute dynamic LangGraph multi-agent systems.",
    version="1.0.0"
)

# Include the modular routing
app.include_router(api_router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
