"""
Project file-system API - manages project folders on disk under local_data/projects/
"""

from __future__ import annotations
import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import io, zipfile
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()

PROJECTS_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "local_data" / "projects"
PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)


class ProjectInfo(BaseModel):
    name: str
    path: str
    created_at: str
    round_count: int
    file_count: int


class FileEntry(BaseModel):
    name: str
    type: str  # "file" | "directory"
    path: str
    size: int
    modified_at: str


class BrowseResult(BaseModel):
    current_path: str
    parent_path: Optional[str] = None
    breadcrumbs: List[dict]
    entries: List[FileEntry]


class FileContent(BaseModel):
    path: str
    name: str
    content: str
    size: int


class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""


def _get_project_dir(name: str) -> Path:
    return PROJECTS_ROOT / name


def _scan_directory(dir_path: Path, base_path: Path) -> List[FileEntry]:
    entries = []
    try:
        for item in sorted(dir_path.iterdir()):
            rel = str(item.relative_to(PROJECTS_ROOT))
            stat = item.stat()
            entries.append(FileEntry(
                name=item.name,
                type="directory" if item.is_dir() else "file",
                path=rel,
                size=stat.st_size if item.is_file() else 0,
                modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat()
            ))
    except PermissionError:
        pass
    return entries


def _count_rounds(project_dir: Path) -> int:
    count = 0
    rounds_dir = project_dir / "rounds"
    if rounds_dir.exists():
        for item in rounds_dir.iterdir():
            if item.is_dir() or item.suffix == ".json":
                count += 1
    return count


def _build_breadcrumbs(project_name: str, rel_path: str) -> List[dict]:
    parts = rel_path.strip("/").split("/") if rel_path.strip("/") else []
    crumbs = [{"name": "projects", "path": "__root__"}]
    crumbs.append({"name": project_name, "path": ""})
    accumulated = ""
    for part in parts:
        accumulated = f"{accumulated}/{part}" if accumulated else part
        crumbs.append({"name": part, "path": accumulated})
    return crumbs


# ===== Endpoints =====

@router.post("", response_model=ProjectInfo)
def create_project(req: CreateProjectRequest):
    """Create a new project folder on disk"""
    name = req.name.strip()
    if not name:
        raise HTTPException(400, "Project name is required")
    safe_name = "".join(c for c in name if c.isalnum() or c in "_- ")
    proj_dir = _get_project_dir(safe_name)
    if proj_dir.exists():
        raise HTTPException(409, f"Project '{safe_name}' already exists")
    proj_dir.mkdir(parents=True)
    (proj_dir / "rounds").mkdir()
    (proj_dir / "results").mkdir()
    info_path = proj_dir / "project.json"
    info_path.write_text(json.dumps({
        "name": safe_name, "description": req.description,
        "created_at": datetime.now().isoformat(), "version": "0.1.0"
    }, indent=2, ensure_ascii=False))
    return ProjectInfo(name=safe_name, path=str(proj_dir),
                       created_at=datetime.now().isoformat(), round_count=0, file_count=0)


@router.get("", response_model=List[ProjectInfo])
def list_projects():
    """List all projects on disk"""
    projects = []
    if PROJECTS_ROOT.exists():
        for d in sorted(PROJECTS_ROOT.iterdir(), key=lambda x: x.name):
            if d.is_dir() and not d.name.startswith("."):
                projects.append(ProjectInfo(
                    name=d.name, path=str(d),
                    created_at=datetime.fromtimestamp(d.stat().st_ctime).isoformat(),
                    round_count=_count_rounds(d),
                    file_count=sum(1 for _ in d.rglob("*") if _.is_file())
                ))
    return projects


@router.get("/{project_name}/browse", response_model=BrowseResult)
def browse_project(project_name: str, subpath: str = Query(default="")):
    """Browse a project's folder contents like a file explorer"""
    proj_dir = _get_project_dir(project_name)
    if not proj_dir.exists():
        raise HTTPException(404, f"Project '{project_name}' not found")
    target = (proj_dir / subpath).resolve() if subpath else proj_dir
    try:
        target.relative_to(PROJECTS_ROOT)
    except ValueError:
        raise HTTPException(403, "Path traversal denied")
    if not target.exists():
        raise HTTPException(404, f"Path '{subpath}' not found")
    rel_path = str(target.relative_to(proj_dir)) if target != proj_dir else ""
    if rel_path == ".":
        rel_path = ""
    try:
        parent = str(target.parent.relative_to(proj_dir)) if target.parent != proj_dir else None
        if parent == ".":
            parent = None
    except ValueError:
        parent = None
    return BrowseResult(
        current_path=rel_path,
        parent_path=parent,
        breadcrumbs=_build_breadcrumbs(project_name, rel_path),
        entries=_scan_directory(target, PROJECTS_ROOT)
    )


@router.get("/{project_name}/file", response_model=FileContent)
def read_file(project_name: str, filepath: str = Query(...)):
    """Read a file's content within a project"""
    proj_dir = _get_project_dir(project_name)
    target = (proj_dir / filepath).resolve()
    try:
        target.relative_to(PROJECTS_ROOT)
    except ValueError:
        raise HTTPException(403, "Path traversal denied")
    if not target.exists() or not target.is_file():
        raise HTTPException(404, f"File not found: {filepath}")
    content = target.read_text(encoding="utf-8", errors="replace")
    return FileContent(path=str(target.relative_to(PROJECTS_ROOT)), name=target.name,
                       content=content, size=target.stat().st_size)


@router.get("/download")
def download_all_projects():
    """Download all projects as a ZIP file"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for proj_dir in sorted(PROJECTS_ROOT.iterdir()):
            if not proj_dir.is_dir() or proj_dir.name.startswith("."):
                continue
            for file_path in proj_dir.rglob("*"):
                if file_path.is_file():
                    arcname = str(file_path.relative_to(PROJECTS_ROOT))
                    zf.write(file_path, arcname)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": "attachment; filename=afp_projects.zip"})


@router.delete("/{project_name}")
def delete_project(project_name: str):
    """Delete a project folder"""
    proj_dir = _get_project_dir(project_name)
    if not proj_dir.exists():
        raise HTTPException(404, f"Project '{project_name}' not found")
    shutil.rmtree(proj_dir)
    return {"status": "deleted", "name": project_name}
