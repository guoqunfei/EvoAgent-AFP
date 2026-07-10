from __future__ import annotations

from fastapi import Request


def get_container(request: Request):
    return request.app.state.container



def get_knowledge_base_service(request: Request):
    return request.app.state.container.knowledge_base_service


def get_rag_service(request: Request):
    return request.app.state.container.rag_service


def get_chat_service(request: Request):
    return request.app.state.container.chat_service


def get_job_runner(request: Request):
    return request.app.state.container.job_runner


def get_research_service(request: Request):
    return request.app.state.container.research_service