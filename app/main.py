from fastapi import FastAPI
from app.database import models
from app.database.database import Base, engine
from app.routers import users,services,queues,auth
Base.metadata.create_all(bind=engine)
app = FastAPI(title="Queue Management System")
app.include_router(users.router)
app.include_router(services.router)
app.include_router(queues.router)
app.include_router(auth.router)
@app.get("/")
def run():
    return {
        "message": "Queue Management System is running!"
    }