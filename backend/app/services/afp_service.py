"""AFPAgent 抗冻蛋白智能设计服务层"""

from __future__ import annotations
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional
from logging import getLogger

from app.core.config import get_settings
from app.afp_agent import AFPAgent, AFPAgentConfig
from app.afp_agent.knowledge import AFPKnowledgeBase, AFPMotifLibrary, AFPLiteratureKnowledge
from app.afp_agent.simulator import AFPIceBindingSimulator
from app.afp_agent.simulator.structure_predictor import get_structure_predictor
from app.afp_agent.memory import MutationMemory, SkillStore
from app.afp_agent.tools.registry import registry as tool_registry

logger = getLogger(__name__)


class AFPAgentService:
    """AFPAgent 抗冻蛋白设计服务"""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        afp_cfg = self.settings.afp_agent

        # Resolve paths
        self.data_dir = self.settings.resolve_backend_path(afp_cfg.data_dir)
        self.skills_dir = self.settings.resolve_backend_path(afp_cfg.skills_dir)
        self.reports_dir = self.settings.resolve_backend_path(afp_cfg.save_reports_dir)

        for d in [self.data_dir, self.skills_dir, self.reports_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # Initialize knowledge components
        self.motif_library = AFPMotifLibrary()
        self.literature_knowledge = AFPLiteratureKnowledge()
        self.knowledge_base = AFPKnowledgeBase(
            motif_library=self.motif_library,
            literature_knowledge=self.literature_knowledge,
        )

        # Initialize simulator
        self.simulator = AFPIceBindingSimulator()

        # Initialize memory and skills
        memory_path = self.data_dir / "mutation_history.json"
        self.memory = MutationMemory(memory_dir=memory_path)

        skills_path = self.skills_dir / "design_skills.json"
        self.skill_store = SkillStore(skills_dir=skills_path)

        # Build agent config
        self.agent_config = AFPAgentConfig(
            llm_model=afp_cfg.llm_model,
            llm_provider=afp_cfg.llm_provider,
            llm_api_key=afp_cfg.llm_api_key,
            llm_base_url=afp_cfg.llm_base_url,
            llm_temperature=afp_cfg.llm_temperature,
            llm_max_tokens=afp_cfg.llm_max_tokens,
            max_iterations=afp_cfg.max_iterations,
            auto_generate_skills=afp_cfg.auto_generate_skills,
            min_experiments_for_skill=afp_cfg.min_experiments_for_skill,
            data_dir=str(self.data_dir),
            skills_dir=str(self.skills_dir),
        )

        # Seed tool registry with component references
        self._seed_tool_context()

    def _seed_tool_context(self):
        """让工具可以访问知识库和模拟器"""
        import app.afp_agent.tools.knowledge_query_tool as kqt
        import app.afp_agent.tools.evaluation_tool as et
        import app.afp_agent.tools.ice_binding_tool as ibt
        import app.afp_agent.tools.afp_chat_tools  # noqa: registers all AFP chat tools
        import app.afp_agent.tools.mutation_tool  # noqa

        kqt.set_knowledge_base(self.knowledge_base)
        et.set_knowledge_base(self.knowledge_base)

    # ---- Knowledge Query ----
    def query_knowledge(self, sequence: str, intent: str = "full_analysis",
                        scenario: str = "general") -> dict:
        result = self.knowledge_base.analyze_sequence(sequence, application_scenario=scenario)
        reference = self.knowledge_base.get_reference_for_llm(result)
        return {
            "afp_type": result.afp_type_prediction,
            "confidence": result.confidence,
            "matched_motifs": [{"id": m, "name": m} for m in result.matched_motifs],
            "ibs_residues": result.ibs_residues_identified,
            "mutation_candidates": result.mutation_candidates,
            "forbidden_regions": result.forbidden_regions,
            "design_principles": [p.get("title", p.get("principle_id","")) for p in result.design_principles_matched],
            "summary": reference[:3000],
        }

    def get_knowledge_summary(self) -> dict:
        return {
            "total_motifs": len(self.motif_library.get_all_motifs()),
            "total_principles": sum(len(v) for v in self.literature_knowledge.DESIGN_PRINCIPLES.values()),
            "total_mutation_findings": len(self.literature_knowledge.MUTATION_FINDINGS),
            "supported_applications": list(self.literature_knowledge.APPLICATION_REQUIREMENTS.keys()),
            "afp_types_covered": sorted(set(m.afp_type.value for m in self.motif_library.get_all_motifs())),
        }

    def list_motifs(self) -> list:
        return [
            {
                "motif_id": m.motif_id,
                "name": m.name,
                "afp_type": m.afp_type.value if hasattr(m.afp_type, 'value') else str(m.afp_type),
                "source_organism": m.source_organism,
                "th_activity": m.th_activity,
                "iri_activity": m.iri_activity,
                "target_ice_plane": m.target_ice_plane.value if hasattr(m.target_ice_plane, 'value') else str(m.target_ice_plane),
                "design_rules": m.design_rules[:3],
            }
            for m in self.motif_library.get_all_motifs()
        ]

    # ---- Sequence Mutation ----
    def mutate_sequence(self, original: str, mutations: list, rationale: str = "") -> dict:
        seq = list(original)
        mutation_desc_parts = []
        for mut in mutations:
            pos = mut["position"] - 1
            if pos < 0 or pos >= len(seq):
                raise ValueError(f"Position {mut['position']} out of range")
            if seq[pos] != mut["from_aa"]:
                raise ValueError(f"Expected {mut['from_aa']} at position {mut['position']}, found {seq[pos]}")
            seq[pos] = mut["to_aa"]
            mutation_desc_parts.append(f"{mut['from_aa']}{mut['position']}{mut['to_aa']}")

        mutated = "".join(seq)
        return {
            "original_sequence": original,
            "mutated_sequence": mutated,
            "mutations": mutations,
            "mutation_description": ", ".join(mutation_desc_parts),
        }

    # ---- Mutation Evaluation ----
    def evaluate_mutation(self, original: str, mutated: str, mutations: list, scenario: str = "general") -> dict:
        analysis = self.knowledge_base.analyze_sequence(original, application_scenario=scenario)
        forbidden_positions = {f["position"] for f in analysis.forbidden_regions}

        warnings = []
        errors = []
        suggestions = []

        for mut in mutations:
            pos = mut["position"]
            if pos in forbidden_positions:
                errors.append(f"⛔ Position {pos} ({mut['from_aa']}{pos}{mut['to_aa']}) is in a FORBIDDEN region — mutation will destroy ice-binding activity")

            # Check IBS quality
            if mut["to_aa"] in ['F', 'W', 'Y', 'R', 'K']:
                warnings.append(f"⚠️ {mut['to_aa']} at position {pos} may disrupt IBS flatness (bulky residue)")
            if mut["to_aa"] in ['D', 'E'] and mut["from_aa"] in ['T', 'N', 'Q', 'A']:
                warnings.append(f"⚠️ Introducing negative charge ({mut['to_aa']}) at position {pos} may repel ice surface")
            if mut["from_aa"] == 'C' and original.count('C') % 2 == 0:
                warnings.append(f"⚠️ C{pos}→{mut['to_aa']} may break a disulfide bond pair — structural stability at risk")

        # Verdict
        if errors:
            verdict = "REJECTED"
        elif len(warnings) >= 2:
            verdict = "WARNING"
        elif warnings:
            verdict = "CAUTION"
        else:
            verdict = "PASS"
            suggestions.append("Mutation appears safe for ice-binding function")

        return {
            "verdict": verdict,
            "overall_assessment": " | ".join(errors + warnings) if (errors or warnings) else "Mutation passes all checks",
            "warnings": warnings,
            "errors": errors,
            "suggestions": suggestions,
        }

    # ---- Ice Binding Simulation ----
    def simulate_ice_binding(self, sequence: str, original: Optional[str] = None,
                             ibs_positions: Optional[list] = None,
                             target_plane: str = "auto") -> dict:
        from app.afp_agent.simulator.ice_binding import IcePlane
        plane = IcePlane.PRISM
        if target_plane != "auto":
            plane_map = {"basal": IcePlane.BASAL, "prism": IcePlane.PRISM,
                         "pyramidal_201": IcePlane.PYRAMIDAL_201, "pyramidal_110": IcePlane.PYRAMIDAL_110}
            plane = plane_map.get(target_plane, IcePlane.PRISM)

        result = self.simulator.simulate(sequence, ibs_positions, plane)
        output = result.to_dict()

        if original:
            comp = self.simulator.compare(original, sequence, ibs_positions)
            output["comparison"] = {
                "th_change_pct": comp.th_change_pct,
                "iri_change_pct": comp.iri_change_pct,
                "geometry_change": comp.geometry_change,
                "assessment": comp.assessment,
                "recommendation": comp.recommendation,
            }

        return output

    # ---- Design Run ----
    def run_design(self, sequence: str, target: str, scenario: str = "general",
                   max_iterations: int = 10) -> dict:
        """Execute AFP design run using LLM-driven agent"""
        agent = AFPAgent(
            config=self.agent_config,
            knowledge_base=self.knowledge_base,
            motif_library=self.motif_library,
            literature_knowledge=self.literature_knowledge,
            simulator=self.simulator,
            memory=self.memory,
            skill_store=self.skill_store,
        )

        result = agent.run(
            sequence=sequence,
            design_target=target,
            application_scenario=scenario,
            max_iterations=max_iterations,
        )

        return result.to_dict() if hasattr(result, 'to_dict') else result

    # ---- Streaming AFP Chat (uses app/ai/features/APF-agent directly) ----
    def run_design_stream(self, message: str, sequence: Optional[str] = None,
                          design_target: str = "improve TH activity",
                          scenario: str = "general",
                          max_iterations: int = 15,
                          conversation_history: list | None = None):
        """
        Run AFP design using app/ai/features/APF-agent's AIAgent directly.
        Captures CLI output and streams as SSE events in real-time.
        """
        import sys
        import io
        import threading
        import queue
        import contextlib
        from pathlib import Path

        # Ensure APF-agent dir is on sys.path
        agent_dir = str(Path(__file__).resolve().parents[1] / "ai" / "features" / "APF-agent")
        if agent_dir not in sys.path:
            sys.path.insert(0, agent_dir)

        # Load AIAgent module (filename contains hyphen, use importlib)
        import importlib.util as _iu
        _spec = _iu.spec_from_file_location("afp_agent_module", str(Path(agent_dir) / "AFP-agent.py"))
        _mod = _iu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        AIAgent = _mod.AIAgent

        # Build the full AFP system prompt
        system_prompt = self._build_apf_agent_system_prompt()

        # Build the design task message
        if sequence:
            design_task = (
                f"请设计一个抗冻蛋白。\n\n"
                f"输入序列: {sequence}\n"
                f"序列长度: {len(sequence)} aa\n"
                f"设计目标: {design_target}\n"
                f"应用场景: {scenario}\n\n"
                f"请严格按照AFP设计工作流程:\n"
                f"1. 首先调用afp_knowledge_query分析序列\n"
                f"2. 然后调用afp_design_strategy获取策略\n"
                f"3. 接着开始突变→评估→模拟的迭代循环\n"
                f"4. 最后用afp_design_summary总结设计结果"
            )
        else:
            design_task = message

        # Pre-save sequence analysis if sequence provided
        if sequence:
            # Pre-analyze and save to design_record BEFORE agent runs
            analysis = self.knowledge_base.analyze_sequence(sequence, scenario)
            analysis_result = {
                "sequence": sequence,
                "length": len(sequence),
                "query_intent": "full_analysis",
                "application_scenario": scenario,
                "afp_type_prediction": analysis.afp_type_prediction,
                "type_confidence": analysis.confidence,
                "type_scores": getattr(analysis, 'type_scores', {}),
                "predicted_ibs": {"positions": analysis.ibs_residues_identified},
                "physicochemical_summary": {
                    "ala_content": sequence.count('A') / len(sequence),
                    "thr_content": sequence.count('T') / len(sequence),
                    "cys_content": sequence.count('C') / len(sequence),
                },
                "forbidden_positions": [f["position"] for f in analysis.forbidden_regions],
                "mutation_hotspots": analysis.mutation_candidates[:8],
                "design_potential_score": getattr(analysis, 'design_potential_score', 0.5),
                "activity_prediction": {"estimated_th_C": 0.1, "estimated_iri_IC50_uM": 1.56, "expression_score": 0.45, "stability_score": 0.6},
                "relevant_design_principles": [],
                "relevant_mutations": [],
                "top_motif_matches": analysis.matched_motifs[:5] if hasattr(analysis, 'matched_motifs') else [],
            }

        yield {"type": "chunk", "content": "正在初始化 AFP 智能设计引擎...\n\n"}

        # Create agent (creates session dir under design_record/)
        try:
            agent = AIAgent(
                model="deepseek-v4-pro",
                system_prompt=system_prompt,
                max_design_rounds=max_iterations,
            )
        except Exception as e:
            logger.error(f"Failed to create AIAgent: {e}")
            yield {"type": "error", "message": f"引擎初始化失败: {str(e)}"}
            yield {"type": "done"}
            return

        # Save analysis to the agent's session dir
        if sequence:
            agent.design_recorder.design_target = design_target
            agent.design_recorder.application_scenario = scenario
            agent.design_recorder.original_sequence = sequence
            agent.design_recorder.save_input_analysis(analysis_result)

        # Show session info
        sid = agent.design_recorder.get_session_id()
        sdir = agent.design_recorder.get_session_dir()
        if sequence:
            yield {"type": "chunk", "content": f"📁 会话 ID: `{sid}`\n📁 数据目录: `design_record/{sid}/`\n📊 序列 `{sequence[:20]}...` ({len(sequence)} aa) 已保存\n\n---\n"}
        else:
            yield {"type": "chunk", "content": f"📁 会话: `{sid}`\n\n---\n"}

        import builtins
        output_lines = []
        output_lock = threading.Lock()
        error_occurred = False
        _spinner_chars = set('⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏')
        _line_buffer = ""

        _orig_print = builtins.print
        def _capture_print(*args, **kwargs):
            nonlocal _line_buffer
            text = ' '.join(str(a) for a in args)
            end = kwargs.get('end', '\n')

            # Filter spinner lines — emit ZERO status messages
            is_spinner = any(c in text for c in _spinner_chars) and len(text) < 30
            if is_spinner:
                return

            # Accumulate text — flush only on end='\n' (default) to avoid char-by-char splitting
            if end == '\n':
                full_line = _line_buffer + text
                _line_buffer = ""
                stripped = full_line.strip()
                if stripped:
                    with output_lock:
                        output_lines.append(stripped)
            else:
                _line_buffer += text + end

        builtins.print = _capture_print

        def _run():
            nonlocal error_occurred, _line_buffer
            try:
                agent.chat(design_task)
            except Exception as e:
                error_occurred = True
                with output_lock:
                    output_lines.append(f"ERROR: {str(e)}")
            finally:
                builtins.print = _orig_print
                # Flush remaining buffer
                if _line_buffer.strip():
                    with output_lock:
                        output_lines.append(_line_buffer.strip())

        t = threading.Thread(target=_run, daemon=True)
        t.start()

        # Stream captured output lines in real-time
        last_idx = 0
        while t.is_alive() or last_idx < len(output_lines):
            with output_lock:
                new_lines = output_lines[last_idx:]
                last_idx = len(output_lines)
            for line in new_lines:
                if line.startswith("ERROR:"):
                    yield {"type": "error", "message": line[7:]}
                else:
                    yield {"type": "chunk", "content": line + "\n"}
            if new_lines:
                continue
            t.join(timeout=0.3)

        t.join(timeout=2)

        if error_occurred:
            yield {"type": "error", "message": "设计过程遇到错误"}
        yield {"type": "chunk", "content": f"\n📁 数据已保存至: `{sdir}`\n"}

        # Send trajectory chart image if it exists, and append to chat log
        import base64 as _b64
        img_md = ""
        img_path = Path(sdir) / "images" / "trajectory.png"
        if img_path.exists():
            try:
                with open(img_path, "rb") as f:
                    img_data = _b64.b64encode(f.read()).decode()
                img_md = f"\n### 📊 性能变化轨迹图\n\n![trajectory](data:image/png;base64,{img_data})\n"
                yield {"type": "chunk", "content": img_md}
            except Exception:
                pass

        # Save chat log (including image markdown) for later restoration
        try:
            chat_log_path = Path(sdir) / "chat_log.txt"
            with open(chat_log_path, "w", encoding="utf-8") as log_f:
                log_f.write("\n".join(output_lines) + img_md)
        except Exception:
            pass

        yield {"type": "done"}

    @staticmethod
    def _build_apf_agent_system_prompt() -> str:
        """Build the full AFP system prompt — identical to APF-agent CLI's main.py."""
        return """你是一个抗冻蛋白（AFP）智能设计专家。用户给你序列和设计目标，你调用工具完成设计。

## ⚠️ 关键行为规则（必须遵守）

1. **用户已给出序列和目标 → 直接进入设计流程，不要反问用户！**
   如果用户未指定应用场景，默认使用 cell_cryopreservation（细胞冻存）。

2. **一次性分析**: afp_knowledge_query(query_intent="full_analysis") 已经包含完整分析，
   **不要重复调用 afp_sequence_analyze**——后者是前者的子集，重复调用浪费 token。

3. **突变前必须查看序列**: afp_knowledge_query 结果中的 sequence 字段包含完整序列。
   设计突变时，**人工数一下位置确认 from_aa 正确**。

4. **只关注相对变化**: 工具返回的 TH/IRI 绝对值是简化模型估算，可能偏低。
   你应该关注突变前后的**变化趋势**和**变化百分比**，而非绝对值。

5. **迭代至少3轮，默认最多30轮**: 不要一轮就放弃。每轮 1-3 个突变，评估→模拟→调整。
   系统会自动追踪设计轮次。达到目标时提前结束，未达到目标则持续迭代。
   如果你认为已达成设计目标，调用 afp_design_summary 输出最终报告。

## 设计流程

```
afp_knowledge_query (分析序列)
    ↓
afp_design_strategy (获取策略)
    ↓
循环 {
    afp_mutate_sequence (突变，避开禁区)
    afp_evaluate_mutation (评估)
    afp_ice_bind_simulate (虚拟实验，对比突变前后)
}
    ↓
afp_design_summary (最终报告)
```

## 设计原则速查

**Type I AFP (α-螺旋, 鱼源) 的关键知识:**
- IBS 核心 Thr: T2/T13/T24/T35 — **绝对不可突变**（间距16.5Å匹配金字塔面{20-21}）
- 盐桥: K18-D1/D5 和 E22 — 维持α-螺旋帽化，不可破坏
- 高 Ala 含量(>50%): 维持α-螺旋稳定性
- **安全突变方向**: 非IBS面 Ala→Ser (提高溶解度/表达)、非IBS面 Lys→Ala (去电荷)
- **激进策略** (高风险高回报): IBS面 Thr→Glu (2025 JACS: Glu结合能是Thr的4倍)
- **禁区**: 不在IBS引入大体积(F/W/Y)或带电(D/E/K/R)残基

**Type III AFP (β-三明治) 关键知识:**
- 冰锚定核心: N14/T18/Q44 — 任一突变完全丧失活性
- A16必须保持小体积(G/A/S)，否则破坏IBS平坦性
- 非IBS β-折叠面可耐受大量突变

**通用原则:**
- Thr间距: 4.5Å(棱面) / 7.4Å(基面) / 16.5Å(金字塔面)，偏差>10%降低活性
- IBS必须平坦(RMSD<1Å)
- 几何互补可独立驱动IRI活性(2025 de novo iTHR证明)

## 应用场景 → 默认场景参数
- cell_cryopreservation → TH优先, application_scenario="cell_cryopreservation"
- ice_cream → IRI优先, application_scenario="ice_cream"
- organ_preservation → TH+IRI双高, application_scenario="organ_preservation"
- anti_ice_coating → 稳定性+TH, application_scenario="anti_ice_coating"

## 最终报告格式
完成设计后用表格输出: 原始/最终序列、每轮突变路径(PASS/WARNING/REJECTED)、TH/IRI变化、有效策略、应避免的突变。

## 迭代提醒
- 默认至少运行 15 轮设计，可用"运行N轮"来调整上限和下限
- 15 轮内即使输出"最终报告"也会被系统推回继续设计
- 达到设计目标 AND 轮次≥15 → 调用 afp_design_summary 输出报告结束
- 未达到目标 → 继续下一轮，系统会自动推动你迭代
- 每轮严格遵循: mutate → evaluate → simulate 三步
"""

    def run_local_design(self, sequence: str, target: str, scenario: str = "general") -> dict:
        """Execute local (non-LLM) design run"""
        analysis = self.knowledge_base.analyze_sequence(sequence, application_scenario=scenario)

        results = []
        for i, candidate in enumerate(analysis.mutation_candidates[:5]):
            mut = [{"position": c["position"], "from_aa": c["from_aa"], "to_aa": c["suggested_aa"]}]
            mutated = self.mutate_sequence(sequence, mut, c.get("rationale", ""))
            eval_result = self.evaluate_mutation(sequence, mutated["mutated_sequence"], mut)

            if eval_result["verdict"] != "REJECTED":
                sim_result = self.simulate_ice_binding(mutated["mutated_sequence"], original=sequence)
                results.append({
                    "rank": i + 1,
                    "mutations": mut,
                    "mutated_sequence": mutated["mutated_sequence"],
                    "evaluation": eval_result,
                    "simulation": sim_result,
                })

        # Sort by geometry score
        results.sort(key=lambda r: r["simulation"].get("overall_geometry_score", 0), reverse=True)
        for i, r in enumerate(results):
            r["rank"] = i + 1

        return {
            "original_sequence": sequence,
            "analysis_summary": analysis.summary if hasattr(analysis, 'summary') else "",
            "candidates": results,
            "best": results[0] if results else None,
        }

    # ---- Memory & Skills ----
    def get_memory_stats(self) -> dict:
        return self.memory.get_stats()

    def get_forbidden_zones(self) -> list:
        return self.memory.get_forbidden_zones()

    def get_skills(self) -> list:
        return [
            {"name": s.name, "description": s.description, "category": s.category,
             "confidence": s.confidence, "evidence_count": s.evidence_count,
             "rules": s.rules}
            for s in self.skill_store.get_all_skills()
        ]

    # ---- Structure Prediction ----
    def predict_structure(self, sequence: str) -> dict:
        predictor = get_structure_predictor()
        result = predictor.predict(sequence)
        pdb_result = self.generate_pdb(sequence)
        return {
            "sequence": result.sequence,
            "sequence_length": result.sequence_length,
            "residues": [
                {
                    "position": r.position,
                    "amino_acid": r.amino_acid,
                    "ss_type": r.ss_type,
                    "ss_confidence": r.ss_confidence,
                    "ibs_candidate": r.ibs_candidate,
                    "ibs_confidence": r.ibs_confidence,
                    "solvent_accessibility": r.solvent_accessibility,
                }
                for r in result.residues
            ],
            "ss_consensus": result.ss_consensus,
            "ss_composition": result.ss_composition,
            "predicted_fold": result.predicted_fold,
            "fold_confidence": result.fold_confidence,
            "matching_afp_type": result.matching_afp_type,
            "ibs_positions": result.ibs_positions,
            "ibs_flatness_score": result.ibs_flatness_score,
            "ibs_thr_spacing": result.ibs_thr_spacing,
            "ala_content": result.ala_content,
            "thr_content": result.thr_content,
            "cys_content": result.cys_content,
            "net_charge": result.net_charge,
            "hydrophobicity": result.hydrophobicity,
            "structural_highlights": result.structural_highlights,
            "design_notes": result.design_notes,
            "pdb_data": pdb_result["pdb"],
            "pdb_source": pdb_result["source"],
        }

    # ---- PDB Structure Generation ----
    def generate_pdb(self, sequence: str) -> dict:
        """
        Generate PDB structure via ESMFold API (free, ~1 sec).
        Falls back to a simple helical backbone if API is unreachable.
        """
        pdb_data = self._fetch_esmfold_pdb(sequence)
        if pdb_data:
            return {"pdb": pdb_data, "source": "ESMFold", "sequence": sequence}

        # Fallback: generate coarse backbone from predicted SS
        predictor = get_structure_predictor()
        pred = predictor.predict(sequence)
        pdb_data = self._build_coarse_pdb(sequence, pred)
        return {"pdb": pdb_data, "source": "Coarse (Chou-Fasman)", "sequence": sequence}

    def _fetch_esmfold_pdb(self, sequence: str) -> Optional[str]:
        """Fetch PDB from ESMFold API."""
        import ssl
        url = "https://api.esmatlas.com/foldSequence/v1/pdbFile/"
        data = sequence.encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "text/plain"})
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:
            logger.warning(f"ESMFold API unavailable: {e}")
            return None

    def _build_coarse_pdb(self, sequence: str, pred) -> str:
        """
        Build full-backbone PDB (N, CA, C, O, CB) with proper peptide geometry.
        φ/ψ angles by SS type (full, unscaled):
          H (α-helix):   φ=-57°, ψ=-47°
          E (β-sheet):   φ=-119°, ψ=113°
          T (turn):      φ=-60°, ψ=-30°
          C (coil):      φ=-75°, ψ=145°
        """
        import math

        CA_C_LEN  = 1.525
        C_N_LEN   = 1.330
        N_CA_LEN  = 1.460
        C_O_LEN   = 1.230
        CA_CB_LEN = 1.530
        CA_CA     = 3.80

        N_CA_C_ANGLE = math.radians(111.0)
        CA_C_N_ANGLE = math.radians(116.0)

        RAMA = {
            'H': (math.radians(-57),  math.radians(-47)),
            'E': (math.radians(-119), math.radians(113)),
            'T': (math.radians(-60),  math.radians(-30)),
            'C': (math.radians(-75),  math.radians(145)),
        }

        def _rot(p, axis, ang):
            x, y, z = p; ux, uy, uz = axis
            n = math.sqrt(ux*ux + uy*uy + uz*uz)
            if n < 1e-10: return p
            ux, uy, uz = ux/n, uy/n, uz/n
            c, s = math.cos(ang), math.sin(ang)
            d = ux*x + uy*y + uz*z
            return (x*c + (uy*z - uz*y)*s + ux*d*(1-c),
                    y*c + (uz*x - ux*z)*s + uy*d*(1-c),
                    z*c + (ux*y - uy*x)*s + uz*d*(1-c))

        def _norm(v):
            n = math.sqrt(v[0]**2+v[1]**2+v[2]**2)
            return (v[0]/n, v[1]/n, v[2]/n) if n > 1e-10 else (1,0,0)

        def _sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
        def _add(a, b): return (a[0]+b[0], a[1]+b[1], a[2]+b[2])
        def _scale(v, s): return (v[0]*s, v[1]*s, v[2]*s)
        def _cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
        def _dist(a, b): return math.sqrt(sum((a[i]-b[i])**2 for i in range(3)))
        def _mid(a, b): return ((a[0]+b[0])/2, (a[1]+b[1])/2, (a[2]+b[2])/2)

        n_res = len(sequence)
        ss_types = [r.ss_type for r in pred.residues]

        # ---- Cα trace using proper dihedral propagation ----
        CA = [(0.0, 0.0, 0.0)]
        CA.append((CA_CA, 0.0, 0.0))
        ang = math.pi - N_CA_C_ANGLE
        CA.append(_add(CA[1], (CA_CA*math.cos(ang), CA_CA*math.sin(ang), 0.0)))

        for i in range(3, n_res):
            a, b, c = CA[i-3], CA[i-2], CA[i-1]
            _, psi = RAMA.get(ss_types[i-2] if i-2 < len(ss_types) else 'C', RAMA['C'])
            # local frame at c
            e1 = _norm(_sub(c, b))
            rm = _cross(_sub(b, a), e1)
            if _dist(rm, (0,0,0)) < 1e-8: rm = (0,0,1)
            e2 = _norm(rm)
            # rotate e1 by (π − bond_angle) around e2, then by ψ around e1
            v = _rot(e1, e2, math.pi - N_CA_C_ANGLE)
            v = _rot(v, e1, psi)
            v = _norm(v)
            CA.append(_add(c, _scale(v, CA_CA)))

        # ---- Place N, C, O, CB atoms ----
        lines = []
        lines.append("HEADER    AFP STRUCTURE MODEL")
        lines.append(f"REMARK    Sequence: {sequence[:50]}")
        lines.append(f"REMARK    SS: {''.join(ss_types)}")
        lines.append("MODEL     1")

        atom_num = 0
        for i in range(n_res):
            ca = CA[i]
            res3 = self._aa3(sequence[i])

            # N
            if i > 0:
                d = _norm(_sub(CA[i-1], ca))
                ni = _add(ca, _scale(d, -N_CA_LEN*0.55))
            else:
                d = _norm(_sub(CA[1], ca))
                ni = _add(ca, _scale(d, -N_CA_LEN*0.55))

            # C
            if i < n_res - 1:
                d = _norm(_sub(CA[i+1], ca))
                ci = _add(ca, _scale(d, CA_C_LEN*0.52))
            else:
                d = _norm(_sub(ca, CA[i-1]))
                ci = _add(ca, _scale(d, CA_C_LEN*0.52))

            # O
            if i < n_res - 1:
                cn = _norm(_sub(CA[i+1], ci))
                perp = (cn[1], -cn[0], 0.3)
                perp = _norm(perp)
            else:
                perp = _norm((0.8, 0.5, 0.3))
            oi = _add(ci, _scale(perp, C_O_LEN))

            # CB
            nd = _norm(_sub(ni, ca))
            cd = _norm(_sub(ci, ca))
            cbd = _norm((-nd[0]-cd[0], -nd[1]-cd[1], -nd[2]-cd[2]))
            cb = _add(ca, _scale(cbd, CA_CB_LEN))

            def _atm(an, el):
                nonlocal atom_num
                atom_num += 1
                return (
                    f'ATOM  {atom_num:5d}  {an:<3s} {res3} A{i+1:4d}    '
                    f'{el[0]:8.3f}{el[1]:8.3f}{el[2]:8.3f}'
                    f'  1.00  0.00           {an.strip()[:1]}  '
                )

            lines.append(_atm('N  ', ni))
            lines.append(_atm('CA ', ca))
            lines.append(_atm('C  ', ci))
            lines.append(_atm('O  ', oi))
            if sequence[i] != 'G':
                lines.append(_atm('CB ', cb))

        lines.append("TER")
        lines.append("ENDMDL")
        lines.append("END")
        return "\n".join(lines)

    @staticmethod
    def _aa3(aa1: str) -> str:
        """Convert 1-letter AA to 3-letter code."""
        mapping = {
            'A': 'ALA', 'C': 'CYS', 'D': 'ASP', 'E': 'GLU', 'F': 'PHE',
            'G': 'GLY', 'H': 'HIS', 'I': 'ILE', 'K': 'LYS', 'L': 'LEU',
            'M': 'MET', 'N': 'ASN', 'P': 'PRO', 'Q': 'GLN', 'R': 'ARG',
            'S': 'SER', 'T': 'THR', 'V': 'VAL', 'W': 'TRP', 'Y': 'TYR',
        }
        return mapping.get(aa1.upper(), 'UNK')
