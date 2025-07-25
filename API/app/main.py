from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import endpoints

app = FastAPI()

origins = [
    "http://192.168.0.6",
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:8501",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(endpoints.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
