from fastapi import FastAPI

from app.core.lifecycle import create_application


app: FastAPI = create_application()