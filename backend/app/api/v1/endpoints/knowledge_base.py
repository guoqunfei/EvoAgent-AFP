"""Knowledge Base API - 11 knowledge categories with FAISS literature search."""

from __future__ import annotations
import json
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter()

KB_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "local_data" / "knowledge_base"

CATEGORIES = [
    {"key": "experimental", "label": "1. Experimental Literature", "format": "markdown", "file": "README.md"},
    {"key": "motifs", "label": "2. Motif Pattern Knowledge", "format": "json", "file": "motifs.json"},
    {"key": "phylogeny", "label": "3. Phylogeny & Evolution", "format": "json", "file": "phylogeny.json"},
    {"key": "sar", "label": "4. Sequence-Performance (SAR)", "format": "json", "file": "sar.json"},
    {"key": "expression", "label": "5. Expression & Host Systems", "format": "json", "file": "expression.json"},
    {"key": "simulation", "label": "6. Computational Simulation", "format": "json", "file": "simulation.json"},
    {"key": "negative_design", "label": "7. Negative Design (Avoid)", "format": "json", "file": "rules.json"},
    {"key": "positive_design", "label": "8. Positive Design (Pursue)", "format": "json", "file": "rules.json"},
    {"key": "literature", "label": "9. Literature (Vector Search)", "format": "faiss", "file": "documents.jsonl"},
]

_faiss_index = None
_faiss_docs = []


def _get_faiss_index():
    global _faiss_index, _faiss_docs
    if _faiss_index is not None:
        return _faiss_index, _faiss_docs
    try:
        import faiss, numpy as np

        docs_path = KB_ROOT / "literature" / "documents.jsonl"
        if not docs_path.exists():
            return None, []
        docs = []
        with open(docs_path) as f:
            for line in f:
                line = line.strip()
                if line: docs.append(json.loads(line))

        # Simple TF-IDF-like embedding without heavy ML deps
        from collections import Counter
        import math
        vocab = set()
        for d in docs:
            vocab.update(re.findall(r'\w+', d["content"].lower()))
        vocab = sorted(vocab)[:2000]
        w2i = {w: i for i, w in enumerate(vocab)}

        embeddings = np.zeros((len(docs), len(vocab)), dtype=np.float32)
        for i, d in enumerate(docs):
            words = re.findall(r'\w+', d["content"].lower())
            counts = Counter(words)
            for w, c in counts.items():
                if w in w2i:
                    embeddings[i, w2i[w]] = c * math.log(len(docs) / (sum(1 for dd in docs if w in dd["content"].lower()) + 1))

        dim = len(vocab)
        idx = faiss.IndexFlatIP(dim)
        faiss.normalize_L2(embeddings)
        idx.add(embeddings)
        _faiss_index = idx
        _faiss_docs = docs
        return _faiss_index, _faiss_docs
    except ImportError:
        return None, []


class CategoryInfo(BaseModel):
    key: str
    label: str
    format: str


class KnowledgeResult(BaseModel):
    category: str
    content: Optional[Dict[str, Any]] = None
    literature_results: Optional[List[dict]] = None


@router.get("/categories", response_model=List[CategoryInfo])
def list_categories():
    return [CategoryInfo(key=c["key"], label=c["label"], format=c["format"]) for c in CATEGORIES]


@router.get("/{category_key}")
def get_knowledge(category_key: str, query: str = Query(default="")):
    cat = next((c for c in CATEGORIES if c["key"] == category_key), None)
    if not cat:
        raise HTTPException(404, f"Category '{category_key}' not found")

    if cat["key"] == "literature":
        return _search_literature(query)

    file_path = KB_ROOT / cat["key"] / cat["file"]
    if not file_path.exists():
        return {"category": cat["label"], "content": None}

    if cat["format"] == "json":
        content = json.loads(file_path.read_text())
    else:
        content = file_path.read_text()

    return {"category": cat["label"], "content": content}


def _search_literature(query: str):
    idx, docs = _get_faiss_index()
    import numpy as np

    if idx is None or not docs:
        if query:
            docs_path = KB_ROOT / "literature" / "documents.jsonl"
            if docs_path.exists():
                results = []
                q = query.lower()
                with open(docs_path) as f:
                    for line in f:
                        doc = json.loads(line.strip())
                        if q in doc["content"].lower() or q in doc["title"].lower():
                            results.append({"id": doc["id"], "title": doc["title"], "content": doc["content"][:300]})
                return {"category": "9. Literature", "literature_results": results[:5]}
        return {"category": "9. Literature", "literature_results": []}

    words = re.findall(r'\w+', query.lower())
    vocab = sorted(set(w for d in _faiss_docs for w in re.findall(r'\w+', d["content"].lower())))[:2000]
    w2i = {w: i for i, w in enumerate(vocab)}
    from collections import Counter
    import math
    q_vec = np.zeros(len(vocab), dtype=np.float32)
    counts = Counter(words)
    for w, c in counts.items():
        if w in w2i:
            q_vec[w2i[w]] = c * math.log(len(_faiss_docs) / (sum(1 for dd in _faiss_docs if w in dd["content"].lower()) + 1))
    q_vec = q_vec.reshape(1, -1)
    faiss.normalize_L2(q_vec)
    scores, indices = idx.search(q_vec, 5)
    results = []
    for score, i in zip(scores[0], indices[0]):
        if score > 0.1 and i < len(_faiss_docs):
            doc = _faiss_docs[i]
            results.append({"id": doc["id"], "title": doc["title"], "content": doc["content"][:300], "score": float(score)})
    return {"category": "9. Literature", "literature_results": results}


@router.post("/add")
def add_knowledge(data: dict):
    """Add a new knowledge entry"""
    key = (data.get("key") or "").strip().lower().replace(" ", "_")
    if not key: raise HTTPException(400, "Key is required")
    title = data.get("title", key)
    ktype = data.get("type", "markdown")
    content = data.get("content", "")

    cat_dir = KB_ROOT / key
    if cat_dir.exists() and ktype != "vector":
        raise HTTPException(409, f"Knowledge key '{key}' already exists")

    cat_dir.mkdir(parents=True, exist_ok=True)

    if ktype == "markdown":
        (cat_dir / "README.md").write_text(content or f"# {title}\n\n", encoding="utf-8")
        CATEGORIES.append({"key": key, "label": title, "format": "markdown", "file": "README.md"})
    elif ktype == "json":
        try: json.loads(content) if content else {}
        except json.JSONDecodeError: raise HTTPException(400, "Invalid JSON content")
        (cat_dir / "data.json").write_text(content or "{}", encoding="utf-8")
        CATEGORIES.append({"key": key, "label": title, "format": "json", "file": "data.json"})
    elif ktype == "vector":
        cat_id = data.get("category_id", "LIT")
        docs_path = KB_ROOT / "literature" / "documents.jsonl"
        docs_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {"id": f"{cat_id}{abs(hash(content)) % 100000:05d}", "title": title, "content": content}
        with open(docs_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        global _faiss_index; _faiss_index = None  # invalidate cache
    return {"status": "added", "key": key, "type": ktype}


@router.post("/{category_key}")
def save_knowledge(category_key: str, data: dict):
    """Save/update knowledge content for a category"""
    cat = next((c for c in CATEGORIES if c["key"] == category_key), None)
    if not cat:
        raise HTTPException(404, f"Category not found")
    file_path = KB_ROOT / cat["key"] / cat["file"]
    file_path.parent.mkdir(parents=True, exist_ok=True)
    raw = data.get("content")
    if raw is not None:
        file_path.write_text(str(raw), encoding="utf-8")
    else:
        file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) if cat["format"] == "json" else str(data))
    return {"status": "saved", "category": cat["label"]}
