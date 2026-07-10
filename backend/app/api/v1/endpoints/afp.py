"""AFPAgent API Endpoints - 抗冻蛋白智能设计"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.schemas.afp import (
    AFPKnowledgeQueryRequest, AFPKnowledgeQueryResponse, AFPKnowledgeSummaryResponse, AFPMotifInfoResponse,
    AFPSequenceMutateRequest, AFPSequenceMutateResponse,
    AFPEvaluateMutationRequest, AFPEvaluateMutationResponse,
    AFPIceBindingSimulateRequest, AFPIceBindingSimulateResponse,
    AFPDesignRequest, AFPDesignResponse,
    AFPBatchTestRequest, AFPBatchTestResponse,
    AFPChatRequest, AFPChatResponse,
    AFPMemoryStatsResponse, AFPSkillListResponse,
    StructurePredictRequest, StructurePredictResponse,
)
from app.core.config import get_settings
from app.services.afp_service import AFPAgentService

router = APIRouter()

# Singleton service
_afp_service: AFPAgentService | None = None

def _get_service() -> AFPAgentService:
    global _afp_service
    if _afp_service is None:
        _afp_service = AFPAgentService()
    return _afp_service


def _sse_json(data: dict) -> str:
    """Serialize dict to JSON string for SSE."""
    return json.dumps(data, ensure_ascii=False)


@router.post("/knowledge/query", response_model=AFPKnowledgeQueryResponse)
async def query_knowledge(req: AFPKnowledgeQueryRequest):
    svc = _get_service()
    result = svc.query_knowledge(req.sequence, req.query_intent, req.application_scenario)
    return AFPKnowledgeQueryResponse(**result)

@router.get("/knowledge/summary", response_model=AFPKnowledgeSummaryResponse)
async def knowledge_summary():
    svc = _get_service()
    return AFPKnowledgeSummaryResponse(**svc.get_knowledge_summary())

@router.get("/knowledge/motifs")
async def list_motifs():
    svc = _get_service()
    return {"motifs": svc.list_motifs()}

@router.post("/tools/mutate", response_model=AFPSequenceMutateResponse)
async def mutate_sequence(req: AFPSequenceMutateRequest):
    svc = _get_service()
    try:
        mutations = [{"position": m.position, "from_aa": m.from_aa, "to_aa": m.to_aa} for m in req.mutations]
        result = svc.mutate_sequence(req.original_sequence, mutations, req.rationale)
        return AFPSequenceMutateResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/tools/evaluate", response_model=AFPEvaluateMutationResponse)
async def evaluate_mutation(req: AFPEvaluateMutationRequest):
    svc = _get_service()
    mutations = [{"position": m.position, "from_aa": m.from_aa, "to_aa": m.to_aa} for m in req.mutations]
    result = svc.evaluate_mutation(req.original_sequence, req.mutated_sequence, mutations, req.application_scenario)
    return AFPEvaluateMutationResponse(**result)

@router.post("/tools/simulate", response_model=AFPIceBindingSimulateResponse)
async def simulate_ice_binding(req: AFPIceBindingSimulateRequest):
    svc = _get_service()
    result = svc.simulate_ice_binding(
        req.sequence, req.original_sequence, req.ibs_positions, req.target_ice_plane
    )
    return AFPIceBindingSimulateResponse(**result)

@router.post("/design", response_model=AFPDesignResponse)
async def run_design(req: AFPDesignRequest):
    svc = _get_service()
    try:
        result = svc.run_design(req.sequence, req.design_target, req.application_scenario, req.max_iterations)
        return AFPDesignResponse(success=True, message="Design completed", report_markdown=result.get("report", ""))
    except Exception as e:
        return AFPDesignResponse(success=False, message=str(e))

@router.post("/design/local", response_model=AFPDesignResponse)
async def run_local_design(req: AFPDesignRequest):
    svc = _get_service()
    try:
        result = svc.run_local_design(req.sequence, req.design_target, req.application_scenario)
        import json
        return AFPDesignResponse(success=True, message="Local design completed", report_markdown=json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        return AFPDesignResponse(success=False, message=str(e))

@router.post("/batch-test", response_model=AFPBatchTestResponse)
async def batch_test(req: AFPBatchTestRequest):
    svc = _get_service()
    results = []
    for seq in req.sequences:
        sim = svc.simulate_ice_binding(seq)
        results.append({
            "sequence": seq, "geometry_score": sim["overall_geometry_score"],
            "estimated_th": sim["estimated_th_activity_C"], "estimated_iri": sim["estimated_iri_activity_uM"],
            "activity_assessment": sim["activity_assessment"], "rank": 0,
        })
    results.sort(key=lambda r: r["geometry_score"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return AFPBatchTestResponse(results=results, best_sequence=results[0]["sequence"] if results else None,
                                 summary=f"Tested {len(results)} sequences. Best geometry score: {results[0]['geometry_score']:.3f}" if results else "No results")

@router.get("/memory/stats", response_model=AFPMemoryStatsResponse)
async def memory_stats():
    svc = _get_service()
    return AFPMemoryStatsResponse(**svc.get_memory_stats())

@router.get("/memory/forbidden-zones")
async def forbidden_zones():
    svc = _get_service()
    return {"forbidden_zones": svc.get_forbidden_zones()}

@router.post("/structure/predict", response_model=StructurePredictResponse)
async def predict_structure(req: StructurePredictRequest):
    svc = _get_service()
    result = svc.predict_structure(req.sequence)
    return StructurePredictResponse(**result)


@router.post("/structure/pdb")
async def generate_pdb(req: StructurePredictRequest):
    """Generate PDB structure file for 3D visualization."""
    svc = _get_service()
    result = svc.generate_pdb(req.sequence)
    return {"pdb": result["pdb"], "source": result["source"]}


@router.get("/skills", response_model=AFPSkillListResponse)
async def list_skills():
    svc = _get_service()
    skills = svc.get_skills()
    return AFPSkillListResponse(skills=skills, total_count=len(skills))


# ============================================================
# Streaming AFP Chat — replaces CLI interactive mode of APF-agent
# ============================================================
@router.post("/chat/stream")
async def afp_chat_stream(req: AFPChatRequest):
    """
    Streaming AFP design chat endpoint.

    Accepts free-form messages and optionally a sequence context.
    Streams SSE events: chunk (text), tool_call, tool_result, done, error.

    This replaces the CLI interactive mode of the standalone APF-agent.
    """
    svc = _get_service()

    def _event_stream():
        try:
            for event in svc.run_design_stream(
                message=req.message,
                sequence=req.sequence,
                conversation_history=None,
            ):
                yield f"data: {_sse_json(event)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {_sse_json({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================
# Session management — list / load past design sessions
# ============================================================
@router.get("/sessions")
async def list_sessions():
    """List all past design sessions from design_record."""
    import sys
    from pathlib import Path
    agent_dir = str(Path(__file__).resolve().parents[3] / "ai" / "features" / "APF-agent")
    if agent_dir not in sys.path:
        sys.path.insert(0, agent_dir)
    from design_recorder import DesignRecorder
    sessions = DesignRecorder.list_sessions(base_dir=str(Path(agent_dir) / "design_record"))
    return {"sessions": sessions}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Load a specific session's data: summary, rounds, and chat messages."""
    import sys
    from pathlib import Path
    agent_dir = str(Path(__file__).resolve().parents[3] / "ai" / "features" / "APF-agent")
    if agent_dir not in sys.path:
        sys.path.insert(0, agent_dir)

    session_dir = Path(agent_dir) / "design_record" / session_id
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    result = {"session_id": session_id}

    # Load summary
    summary_file = session_dir / "summary.json"
    if summary_file.exists():
        import json
        with open(summary_file, "r", encoding="utf-8") as f:
            result["summary"] = json.load(f)

    # Load rounds
    rounds_file = session_dir / "rounds.json"
    if rounds_file.exists():
        import json
        with open(rounds_file, "r", encoding="utf-8") as f:
            result["rounds"] = json.load(f)

    # Load analysis
    analysis_file = session_dir / "input_seq_analysis" / "analysis.json"
    if analysis_file.exists():
        import json
        with open(analysis_file, "r", encoding="utf-8") as f:
            result["analysis"] = json.load(f)

    # Load chat log
    chat_log_file = session_dir / "chat_log.txt"
    if chat_log_file.exists():
        result["chat_log"] = chat_log_file.read_text(encoding="utf-8")

    return result


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a design session directory and remove from index."""
    import shutil
    agent_dir = str(Path(__file__).resolve().parents[3] / "ai" / "features" / "APF-agent")
    if agent_dir not in sys.path:
        sys.path.insert(0, agent_dir)

    session_dir = Path(agent_dir) / "design_record" / session_id
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    shutil.rmtree(session_dir)

    # Update sessions_index.json
    index_file = Path(agent_dir) / "design_record" / "sessions_index.json"
    if index_file.exists():
        import json
        existing = json.loads(index_file.read_text(encoding="utf-8"))
        existing = [s for s in existing if s.get("session_id") != session_id]
        index_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"success": True, "message": f"Session {session_id} deleted"}


# ============================================================
# Skill file management — list / read / edit SKILL.md files
# ============================================================
import yaml as _yaml_lib

def _get_skills_dir() -> Path:
    from pathlib import Path as _P
    return _P(__file__).resolve().parents[3] / "ai" / "features" / "APF-agent" / "skills"

def _parse_skill_md(filepath: Path) -> dict:
    """Parse a SKILL.md file with YAML frontmatter, return {name, description, version, content, path}."""
    text = filepath.read_text(encoding="utf-8")
    result = {"path": str(filepath.parent.name), "content": text}
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = _yaml_lib.safe_load(parts[1])
                if isinstance(fm, dict):
                    result["name"] = fm.get("name", filepath.parent.name)
                    result["description"] = fm.get("description", "")
                    result["version"] = fm.get("version", "1.0.0")
            except Exception:
                result["name"] = filepath.parent.name
    if "name" not in result:
        result["name"] = filepath.parent.name
    return result


@router.get("/skills-files")
async def list_skill_files():
    """List all skill markdown files from the skills/ directory."""
    skills_dir = _get_skills_dir()
    skills = []
    for d in sorted(skills_dir.iterdir()):
        if d.is_dir():
            md_file = d / "SKILL.md"
            if md_file.exists():
                skills.append(_parse_skill_md(md_file))
    return {"skills": skills}


@router.get("/skills-files/{skill_name}")
async def get_skill_file(skill_name: str):
    """Get a specific skill's markdown content."""
    md_file = _get_skills_dir() / skill_name / "SKILL.md"
    if not md_file.exists():
        raise HTTPException(status_code=404, detail=f"Skill {skill_name} not found")
    return _parse_skill_md(md_file)


@router.put("/skills-files/{skill_name}")
async def update_skill_file(skill_name: str, body: dict):
    """Update a skill's markdown content."""
    md_file = _get_skills_dir() / skill_name / "SKILL.md"
    if not md_file.exists():
        raise HTTPException(status_code=404, detail=f"Skill {skill_name} not found")
    content = body.get("content", "")
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    md_file.write_text(content, encoding="utf-8")
    return {"success": True, "message": f"Skill {skill_name} updated"}


@router.delete("/skills-files/{skill_name}")
async def delete_skill_file(skill_name: str):
    """Delete a skill directory and its SKILL.md file."""
    import shutil
    skill_dir = _get_skills_dir() / skill_name
    if not skill_dir.exists():
        raise HTTPException(status_code=404, detail=f"Skill {skill_name} not found")
    shutil.rmtree(skill_dir)
    return {"success": True, "message": f"Skill {skill_name} deleted"}


# ============================================================
# Knowledge entries — editable JSON store for custom knowledge
# ============================================================
_KB_FILE: Path | None = None

def _get_kb_file() -> Path:
    global _KB_FILE
    if _KB_FILE is None:
        from pathlib import Path as _P
        kb_dir = _P(__file__).resolve().parents[3] / "app" / "local_data" / "afp_agent"
        kb_dir.mkdir(parents=True, exist_ok=True)
        _KB_FILE = kb_dir / "knowledge_entries.json"
        if not _KB_FILE.exists():
            import json
            _KB_FILE.write_text("[]", encoding="utf-8")
    return _KB_FILE

def _read_kb() -> list:
    import json
    return json.loads(_get_kb_file().read_text(encoding="utf-8"))

def _write_kb(entries: list):
    import json
    _get_kb_file().write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("/knowledge/entries")
async def list_knowledge_entries():
    """List all editable knowledge entries (custom + built-in merged)."""
    svc = _get_service()
    # Built-in motifs
    builtin = svc.list_motifs()
    # Custom entries
    custom = _read_kb()
    return {"entries": builtin + custom, "custom_count": len(custom)}


@router.post("/knowledge/entries")
async def create_knowledge_entry(body: dict):
    """Add a custom knowledge entry."""
    entry = {
        "motif_id": body.get("motif_id", f"custom-{len(_read_kb())}"),
        "name": body.get("name", ""),
        "afp_type": body.get("afp_type", ""),
        "source_organism": body.get("source_organism", ""),
        "th_activity": float(body.get("th_activity", 0)),
        "iri_activity": float(body.get("iri_activity", 0)),
        "target_ice_plane": body.get("target_ice_plane", ""),
        "design_rules": body.get("design_rules", []),
    }
    entries = _read_kb()
    entries.append(entry)
    _write_kb(entries)
    return {"success": True, "entry": entry}


@router.put("/knowledge/entries/{motif_id}")
async def update_knowledge_entry(motif_id: str, body: dict):
    """Update a custom knowledge entry."""
    entries = _read_kb()
    for e in entries:
        if e["motif_id"] == motif_id:
            e["name"] = body.get("name", e["name"])
            e["afp_type"] = body.get("afp_type", e["afp_type"])
            e["source_organism"] = body.get("source_organism", e["source_organism"])
            e["th_activity"] = float(body.get("th_activity", e["th_activity"]))
            e["iri_activity"] = float(body.get("iri_activity", e["iri_activity"]))
            e["target_ice_plane"] = body.get("target_ice_plane", e["target_ice_plane"])
            e["design_rules"] = body.get("design_rules", e["design_rules"])
            _write_kb(entries)
            return {"success": True, "entry": e}
    raise HTTPException(status_code=404, detail=f"Entry {motif_id} not found")


@router.delete("/knowledge/entries/{motif_id}")
async def delete_knowledge_entry(motif_id: str):
    """Delete a custom knowledge entry."""
    entries = _read_kb()
    new_entries = [e for e in entries if e["motif_id"] != motif_id]
    if len(new_entries) == len(entries):
        raise HTTPException(status_code=404, detail=f"Entry {motif_id} not found")
    _write_kb(new_entries)
    return {"success": True}
