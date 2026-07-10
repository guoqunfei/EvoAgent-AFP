"""AFPAgent - 抗冻蛋白智能设计核心代理"""

from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from logging import getLogger
from typing import Optional, List
try:
    from openai import OpenAI  # openai >= 1.0
except ImportError:
    import openai  # openai < 1.0
    OpenAI = None

from .knowledge.knowledge_base import AFPKnowledgeBase
from .knowledge.motifs import AFPMotifLibrary
from .knowledge.literature import AFPLiteratureKnowledge
from .simulator.ice_binding import AFPIceBindingSimulator
from .memory.mutation_memory import MutationMemory
from .memory.skill_store import SkillStore
from .tools.registry import registry as tool_registry

logger = getLogger(__name__)


@dataclass
class AFPAgentConfig:
    llm_model: str = "gpt-4o"
    llm_provider: str = "openai"
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_temperature: float = 0.3
    llm_max_tokens: int = 4096
    max_iterations: int = 20
    auto_generate_skills: bool = True
    min_experiments_for_skill: int = 3
    data_dir: str = ""
    skills_dir: str = ""


@dataclass
class DesignRunResult:
    original_sequence: str
    best_sequence: str
    best_score: float
    total_rounds: int
    total_experiments: int
    mutation_history: list = field(default_factory=list)
    learned_skills: list = field(default_factory=list)
    report: str = ""
    recommendations: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "original_sequence": self.original_sequence,
            "best_sequence": self.best_sequence,
            "best_score": self.best_score,
            "total_rounds": self.total_rounds,
            "total_experiments": self.total_experiments,
            "mutation_history": self.mutation_history,
            "learned_skills": self.learned_skills,
            "report": self.report,
            "recommendations": self.recommendations,
        }


class AFPAgent:
    """抗冻蛋白智能设计代理 — 基于LLM的多轮迭代优化"""

    def __init__(self, config: AFPAgentConfig, knowledge_base: AFPKnowledgeBase,
                 motif_library: AFPMotifLibrary, literature_knowledge: AFPLiteratureKnowledge,
                 simulator: AFPIceBindingSimulator, memory: MutationMemory,
                 skill_store: SkillStore):
        self.config = config
        self.knowledge_base = knowledge_base
        self.motif_library = motif_library
        self.literature_knowledge = literature_knowledge
        self.simulator = simulator
        self.memory = memory
        self.skill_store = skill_store
        self.llm_client = self._init_llm_client()

        # Ensure tools are registered
        self._ensure_tools_registered()

    def _init_llm_client(self):
        cfg = self.config
        # Support both old and new OpenAI API
        if OpenAI is not None:
            # New API (openai >= 1.0)
            kwargs = {"api_key": cfg.llm_api_key or "not-set"}
            if cfg.llm_base_url:
                kwargs["base_url"] = cfg.llm_base_url
            return OpenAI(**kwargs)
        else:
            # Old API (openai < 1.0) - just return the module for compatibility
            import openai
            if cfg.llm_api_key:
                openai.api_key = cfg.llm_api_key
            if cfg.llm_base_url:
                openai.base_url = cfg.llm_base_url
            return openai

    def _ensure_tools_registered(self):
        """Ensure AFP tools are imported, registered, and seeded with knowledge base"""
        try:
            import app.afp_agent.tools.knowledge_query_tool as kqt
            import app.afp_agent.tools.mutation_tool  # noqa
            import app.afp_agent.tools.evaluation_tool as et
            import app.afp_agent.tools.ice_binding_tool  # noqa

            kqt.set_knowledge_base(self.knowledge_base)
            et.set_knowledge_base(self.knowledge_base)
        except ImportError:
            pass

    def run(self, sequence: str, design_target: str, application_scenario: str = "general",
            max_iterations: int = None) -> DesignRunResult:
        """LLM驱动的多轮迭代设计"""
        max_iter = max_iterations or self.config.max_iterations

        # Pre-analyze sequence
        analysis = self.knowledge_base.analyze_sequence(sequence, application_scenario)
        analysis_text = self.knowledge_base.get_reference_for_llm(analysis)

        # Build system prompt
        system_prompt = self._build_system_prompt()

        # Initial message
        initial_message = self._build_initial_message(sequence, design_target, application_scenario, analysis_text)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": initial_message},
        ]

        best_sequence = sequence
        best_score = 0.0
        history = []
        tools = tool_registry.get_definitions()

        for iteration in range(max_iter):
            logger.info(f"AFPAgent iteration {iteration + 1}/{max_iter}")

            try:
                # Support both old and new OpenAI API
                if hasattr(self.llm_client, 'chat'):
                    # New API (openai >= 1.0)
                    response = self.llm_client.chat.completions.create(
                        model=self.config.llm_model,
                        messages=messages,
                        tools=tools if tools else None,
                        tool_choice="auto" if tools else None,
                        temperature=self.config.llm_temperature,
                        max_tokens=self.config.llm_max_tokens,
                    )
                else:
                    # Old API (openai < 1.0)
                    kwargs = {
                        "model": self.config.llm_model,
                        "messages": messages,
                        "temperature": self.config.llm_temperature,
                        "max_tokens": self.config.llm_max_tokens,
                    }
                    if tools:
                        kwargs["functions"] = [t.get("function", t) for t in tools]
                        kwargs["function_call"] = "auto"
                    response = self.llm_client.ChatCompletion.create(**kwargs)
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                break

            # Handle response based on API version
            if hasattr(response, 'choices'):
                # New API (openai >= 1.0)
                assistant_msg = response.choices[0].message
                messages.append({"role": "assistant", "content": assistant_msg.content or "",
                               "tool_calls": [
                                   {"id": tc.id, "type": "function",
                                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                                   for tc in (assistant_msg.tool_calls or [])
                               ] if assistant_msg.tool_calls else None})
            else:
                # Old API (openai < 1.0)
                choice = response['choices'][0]
                assistant_msg = choice.get('message', {})
                messages.append({"role": "assistant", "content": assistant_msg.get('content', '')})

            # Check for completion
            if assistant_msg.get('content') and self._is_design_complete(assistant_msg['content']):
                logger.info("Design completion detected")
                break

            # Handle tool calls - support both API versions
            tool_calls = None
            if hasattr(response, 'choices'):
                # New API (openai >= 1.0)
                tool_calls = response.choices[0].message.tool_calls
            elif isinstance(response, dict):
                # Old API (openai < 1.0)
                choice = response.get('choices', [{}])[0]
                message = choice.get('message', {})
                tool_calls = message.get('function_call')

            if tool_calls:
                # Normalize to list format
                if not isinstance(tool_calls, list):
                    tool_calls = [tool_calls]
                
                for tc in tool_calls:
                    # Handle both object and dict formats
                    if isinstance(tc, dict):
                        tool_name = tc.get('name', tc.get('function', {}).get('name', ''))
                        tool_args_str = tc.get('arguments', tc.get('function', {}).get('arguments', '{}'))
                        tc_id = tc.get('id', f'tc_{len(history)}')
                    else:
                        tool_name = tc.function.name
                        tool_args_str = tc.function.arguments
                        tc_id = tc.id
                    
                    try:
                        tool_args = json.loads(tool_args_str) if tool_args_str else {}
                    except json.JSONDecodeError:
                        tool_args = {}

                    result = tool_registry.dispatch(tool_name, tool_args)

                    if isinstance(result, dict):
                        result_text = json.dumps(result, ensure_ascii=False, indent=2)
                    else:
                        result_text = str(result)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": result_text,
                    })

                    # Record ice binding simulation results
                    if tool_name == "afp_ice_bind_simulate" and isinstance(result, dict):
                        if result.get("comparison"):
                            score = self._evaluate_result_score(result["comparison"], design_target)
                            if score > best_score:
                                best_score = score
                                if "mutated" in str(tool_args):
                                    best_sequence = tool_args.get("sequence", best_sequence)

                            history.append({
                                "iteration": iteration + 1,
                                "tool": tool_name,
                                "score": round(score, 3),
                                "result_summary": result.get("activity_assessment", ""),
                            })
            else:
                # No tool calls — LLM has concluded
                break

        # Auto-generate skills from memory
        if self.config.auto_generate_skills:
            new_skills = self.skill_store.generate_skill_from_memory(self.memory)
            logger.info(f"Generated {len(new_skills)} new skills from memory")

        # Generate final report
        report = self._generate_final_report(sequence, best_sequence, history, design_target)
        recommendations = self._generate_recommendations(best_sequence, design_target)

        return DesignRunResult(
            original_sequence=sequence,
            best_sequence=best_sequence,
            best_score=best_score,
            total_rounds=iteration + 1,
            total_experiments=len(history),
            mutation_history=history,
            learned_skills=[s.name for s in self.skill_store.get_high_confidence_skills()],
            report=report,
            recommendations=recommendations,
        )

    def _build_system_prompt(self) -> str:
        tools_desc = tool_registry.get_tool_descriptions()
        memory_context = self.memory.get_memory_context_for_llm()
        skill_context = self.skill_store.get_skill_context_for_llm()

        return f"""You are an Antifreeze Protein (AFP) design expert AI agent.

## Your Knowledge Domains
- Five structural AFP types: Type I (α-helical), Type II (C-type lectin), Type III (β-sandwich), Type IV (4-helix bundle), Insect hyperactive (β-helical)
- Antifreeze glycoproteins (AFGPs), plant AFPs, bacterial IBPs, fungal AFPs
- Ice-binding surface (IBS) atomic-precision design: geometric complementarity, H-bond matching, hydrophobic complementarity
- Two core activity metrics: Thermal Hysteresis (TH) and Ice Recrystallization Inhibition (IRI)
- Ice plane specificity: Basal {{0001}} (7.4Å spacing), Prism {{10-10}} (4.5Å), Pyramidal {{20-21}} (16.5Å), {{11-20}} (7.85Å)
- 2025 breakthroughs: de novo iTHR design, non-canonical Thr-free IBS (MaIBP), synthetic AFP peptide commercialization

## Available Tools
{tools_desc}

## Design Workflow
1. **afp_knowledge_query** — Deep sequence analysis (AFP type, IBS residues, forbidden regions, design principles)
2. **mutate_sequence** — Execute precise mutations (1-3 positions at a time)
3. **afp_evaluate_mutation** — Assess structural and functional impact
4. **afp_ice_bind_simulate** — Simulate ice binding (geometry scoring + TH/IRI prediction)

## Core Design Principles
- **Thr Spacing Rule**: Prism plane → 4.5Å, Basal → 7.4Å, Pyramidal → 16.5Å
- **Flatness Rule**: IBS must be flat (RMSD < 1Å). No bulky residues (F/W/Y/R/K) on IBS.
- **TXT Motif**: Insect AFP gold standard — Thr-X-Thr at precise ice lattice spacing.
- **Exception**: 2025 MaIBP discovery showed Thr-free IBS can work via geometric complementarity.
- **Forbidden**: NEVER mutate IBS core residues, disulfide Cys pairs, or critical salt bridges.
- **Safe zones**: Non-IBS face mutations can tune solubility, stability, and expression.

{memory_context}
{skill_context}

When design is complete, state "DESIGN_COMPLETE" and provide final recommendations."""

    def _build_initial_message(self, sequence: str, target: str, scenario: str, analysis_text: str) -> str:
        return f"""## Design Task
- **Input Sequence**: {sequence}
- **Design Target**: {target}
- **Application Scenario**: {scenario}

## Knowledge Base Pre-Analysis
{analysis_text}

Please analyze this sequence and propose the first round of mutations to achieve the design target.
Start by calling afp_knowledge_query to get detailed sequence analysis."""

    def _is_design_complete(self, content: str) -> bool:
        markers = ["DESIGN_COMPLETE", "FINAL_REPORT", "设计完成", "最终报告", "最优序列已确定"]
        return any(m in content for m in markers)

    def _evaluate_result_score(self, comparison: dict, target: str) -> float:
        """Score mutation result (-1 to 1) based on design target"""
        th_change = comparison.get("th_change_pct", 0)
        iri_change = comparison.get("iri_change_pct", 0)
        # For IRI, negative change = improvement (lower IC50 is better)
        iri_improvement = -iri_change

        target_lower = target.lower()
        score = 0.0

        if "th" in target_lower or "hysteresis" in target_lower or "freeze" in target_lower:
            score = 0.6 * th_change + 0.3 * iri_improvement
        elif "iri" in target_lower or "recrystallization" in target_lower or "ice cream" in target_lower:
            score = 0.3 * th_change + 0.6 * iri_improvement
        else:
            score = 0.4 * th_change + 0.4 * iri_improvement

        # Normalize to [-1, 1]
        return max(-1.0, min(1.0, score / 50.0))

    def _generate_final_report(self, original: str, best: str, history: list, target: str) -> str:
        lines = [
            "# AFP Design Report",
            "",
            f"## Design Target\n{target}",
            "",
            f"## Original Sequence\n`{original}`",
            "",
            f"## Best Sequence\n`{best}`",
            "",
            "## Design History",
        ]
        for h in history:
            lines.append(f"- Round {h['iteration']}: Score {h['score']} — {h.get('result_summary', '')}")

        lines.extend([
            "",
            "## Recommendations",
            "1. Validate predicted TH and IRI activity experimentally",
            "2. Test expression in E. coli or P. pastoris",
            "3. Assess stability via CD spectroscopy",
        ])

        return "\n".join(lines)

    def _generate_recommendations(self, sequence: str, target: str) -> list:
        return [
            "Synthesize the designed AFP sequence",
            "Measure TH activity via nanoliter osmometry",
            "Measure IRI activity via sucrose sandwich assay",
            "Test expression yield in chosen host",
            "Iterate based on experimental feedback",
        ]
