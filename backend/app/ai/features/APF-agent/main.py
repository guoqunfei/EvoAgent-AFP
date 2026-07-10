# main.py
"""
AFP 抗冻蛋白智能设计平台 —— 主入口

运行方式:
  python main.py          # 启动交互模式
  python main.py --demo   # 自动启动 demo 设计任务（Type I HPLC6 抗冻蛋白设计）

交互模式命令: /tools, /memory, /skills, /sessions, /clear, /quit
"""

import os
import sys

# 确保脚本所在目录在 sys.path 中（支持从任意目录运行）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# AFP-agent.py 是核心智能体模块（文件名含连字符，需通过 importlib 加载）
import importlib.util as _importlib_util
_agent_spec = _importlib_util.spec_from_file_location(
    "afp_agent_module", os.path.join(SCRIPT_DIR, "AFP-agent.py")
)
_agent_mod = _importlib_util.module_from_spec(_agent_spec)
_agent_spec.loader.exec_module(_agent_mod)
AIAgent = _agent_mod.AIAgent

DEFAULT_MODEL = "deepseek-v4-pro"

# Demo 任务的默认序列和目标（对应 demo_output.txt 中的 Type I HPLC6 设计）
DEMO_SEQUENCE = "DTASDAAAAAALTAANAKAAAELTAANAAAAAAATAR"
DEMO_TARGET = "将TH活性从0.5°C提高到2.0°C以上（提高4倍），同时保持或改善IRI活性"
DEMO_SCENARIO = "cell_cryopreservation"


def build_afp_system_prompt() -> str:
    """构建 AFP 抗冻蛋白设计专用的系统提示词"""
    return """你是一个抗冻蛋白（AFP）智能设计专家。用户给你序列和设计目标，你调用工具完成设计。

## ⚠️ 关键行为规则（必须遵守）

1. **用户已给出序列和目标 → 直接进入设计流程，不要反问用户！**
   如果用户未指定应用场景，默认使用 cell_cryopreservation（细胞冻存）。

2. **一次性分析**: afp_knowledge_query(query_intent="full_analysis") 已经包含完整分析，
   **不要重复调用 afp_sequence_analyze**——后者是前者的子集，重复调用浪费 token。

3. **突变前必须查看序列**: afp_knowledge_query 结果中的 sequence 字段包含完整序列。
   设计突变时，**人工数一下位置确认 from_aa 正确**。例如序列 DTASDAAAAAALTAANAKAAAELTAANAAAAAAATAR:
   - 位置1=D, 2=T, 3=A, 4=S, 5=D, 6=A, 7=A, 8=A, 9=A, 10=A
   - 11=A, 12=L, 13=T, 14=A, 15=A, 16=N, 17=A, 18=K, 19=A, 20=A
   - 21=A, 22=E, 23=L, 24=T, 25=A, 26=A, 27=N, 28=A, 29=A, 30=A
   - 31=A, 32=A, 33=A, 34=A, 35=T, 36=A, 37=R

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


def main():
    """启动 AFP 抗冻蛋白智能设计平台"""
    # 解析命令行参数
    demo_mode = "--demo" in sys.argv

    print("=" * 60)
    print("🧬 AFP-Designer 抗冻蛋白智能设计平台")
    print("=" * 60)
    print("📦 正在初始化智能体和工具库...")
    print()

    # 创建具有 AFP 专业知识的智能体（默认15轮，达到目标前不提前结束）
    agent = AIAgent(
        model=DEFAULT_MODEL,
        system_prompt=build_afp_system_prompt(),
        max_design_rounds=15,
    )

    # 显示会话 ID
    sid = agent.design_recorder.get_session_id()
    sdir = agent.design_recorder.get_session_dir()
    print(f"📁 会话 ID: {sid}")
    print(f"📁 数据目录: {sdir}")
    print(f"📁 历史会话数: {len(agent.design_recorder.list_sessions())}")
    print()

    if demo_mode:
        print()
        print("=" * 60)
        print("🚀 Demo 模式: 自动启动 Type I HPLC6 抗冻蛋白设计")
        print("=" * 60)
        print(f"   输入序列: {DEMO_SEQUENCE}")
        print(f"   序列长度: {len(DEMO_SEQUENCE)} aa")
        print(f"   设计目标: {DEMO_TARGET}")
        print(f"   应用场景: {DEMO_SCENARIO}")
        print("=" * 60)
        print()

        # 直接启动设计对话
        design_task = (
            f"请设计一个抗冻蛋白。\n\n"
            f"输入序列: {DEMO_SEQUENCE}\n"
            f"序列长度: {len(DEMO_SEQUENCE)} aa\n"
            f"设计目标: {DEMO_TARGET}\n"
            f"应用场景: {DEMO_SCENARIO}\n\n"
            f"请严格按照AFP设计工作流程:\n"
            f"1. 首先调用afp_knowledge_query分析序列\n"
            f"2. 然后调用afp_design_strategy获取策略\n"
            f"3. 接着开始突变→评估→模拟的迭代循环\n"
            f"4. 最后用afp_design_summary总结设计结果"
        )
        agent.chat(design_task)
        # chat() 返回后，继续进入交互模式以便用户追问
        print()
        print("💡 Demo 设计完成。可以继续输入更多设计指令，或 /quit 退出。")
        print()

    else:
        # 提供快速启动提示
        print()
        print("💡 快速开始: 直接输入 AFP 设计任务，例如:")
        print(f"   设计抗冻蛋白序列 {DEMO_SEQUENCE[:20]}...")
        print(f"   目标: {DEMO_TARGET}")
        print(f"   场景: {DEMO_SCENARIO}")
        print()

    agent.run()


if __name__ == "__main__":
    main()
