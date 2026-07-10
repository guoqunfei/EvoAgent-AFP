from fastapi import APIRouter

from app.api.v1.endpoints import system, chat, jobs, knowledge_base, rag, research, afp, projects

api_router = APIRouter()
api_router.include_router(system.router, tags=["system"])
api_router.include_router(knowledge_base.router, prefix="/knowledge-bases", tags=["knowledge-bases"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(research.router, prefix="/research", tags=["research"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(afp.router, prefix="/afp", tags=["afp-agent"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])