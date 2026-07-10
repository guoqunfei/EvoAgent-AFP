# reflection.py
"""
反思模块
负责任务完成/失败后的成果评估和技能生成决策
"""

import json
from typing import Dict, Any, Optional, List

from trajectory import TaskTrajectory


def build_reflection_prompt(trajectory_data: TaskTrajectory) -> str:
    """
    构建反思提示词（用于复杂任务完成后的技能生成评估）
    
    Hermes通过SKILLS_GUIDANCE提示词引导Agent自主评估任务价值，
    本函数生成结构化的反思提示
    """
    tool_calls_list = []
    for tc in trajectory_data.tool_calls:
        tool_calls_list.append({
            "name": tc.name,
            "arguments": tc.arguments,
            "success": tc.success
        })
    
    # 构建触发条件判定
    triggers = []
    if len(trajectory_data.tool_calls) >= 5:
        triggers.append("复杂任务（5次以上工具调用）")
    if any(e.resolved for e in trajectory_data.errors):
        triggers.append("错误恢复")
    if trajectory_data.user_corrections:
        triggers.append("用户纠正")
    
    triggers_text = ", ".join(triggers) if triggers else "检测到值得学习的经验"
    
    prompt = f"""请基于刚才完成的任务，提取经验并生成可复用技能。

**【触发条件】** {triggers_text}

**【任务信息】**
- 任务描述: {trajectory_data.task_description}
- 执行结果: {'成功' if trajectory_data.overall_success else '失败'}
- 工具调用次数: {len(trajectory_data.tool_calls)}
- 错误次数: {len(trajectory_data.errors)}
- 用户纠正: {len(trajectory_data.user_corrections)} 次

**【执行摘要】**
{', '.join([f"工具调用: {tc.name}" for tc in trajectory_data.tool_calls[:5]])}

**【你必须做：调用 skill_manage 创建技能】**

1. **技能命名**: 使用小写连字符格式，如 'design-afp-mutation', 'fix-database'
2. **YAML frontmatter** (JSON字符串) 必须包含：
   - name: 技能名称
   - description: 清晰说明什么场景下使用
   - version: 1.0.0

3. **Markdown正文**应包含：
   - **何时使用**: 描述技能的适用场景
   - **操作步骤**: 详细、按顺序的操作步骤
   - **常见陷阱**: 执行中可能遇到的问题及解决方案
   - **验证方法**: 如何确认技能执行成功

请立即调用 skill_manage(action='create', name='技能名', frontmatter='...', content='...')
"""

    return prompt


def build_failure_reflection_prompt(trajectory_data: TaskTrajectory) -> str:
    """
    构建失败反思的提示词（用于生成错误教训记忆）
    
    任务失败时，不是简单地放弃，而是从失败中提炼教训存入记忆
    """
    # 错误信息摘要
    error_info = []
    for err in trajectory_data.errors:
        error_info.append(f"- 错误: {err.message}")
        if err.context:
            error_info.append(f"  上下文: {err.context}")
        if err.resolution_notes:
            error_info.append(f"  解决方法: {err.resolution_notes}")
    
    error_summary = "\n".join(error_info) if error_info else "未能采集到详细的错误信息"
    
    prompt = f"""任务执行失败了，请分析原因并用技能（Skill）记录教训。

**【执行失败的任务】**
- 任务描述: {trajectory_data.task_description}
- 工具调用次数: {len(trajectory_data.tool_calls)}
- 发生的错误:
{error_summary}

**【你必须做：创建一个技能来记录教训】**
请调用 skill_manage(action='create') 创建技能，技能必须包含：
- name: 使用 'avoid-xxx-error' 格式
- description: 清晰说明什么场景下使用
- frontmatter: {{"name":"...","description":"...","version":"1.0.0"}}
- content (Markdown格式):
  ## 何时使用
  （描述触发该技能的场景）
  ## 操作步骤
  （正确的操作步骤）
  ## 常见陷阱
  （本次失败的原因和避免方法）
  ## 验证方法
  （如何确认问题已解决）
"""

    return prompt


def build_nudge_reflection_prompt(
    recent_trajectories: List[Dict],
    current_memory_context: str,
    current_skills_list: str
) -> str:
    """
    构建Nudge反思提示词（定时触发，总结近期对话精华）
    用于周期性回顾和提炼值得长期保存的信息
    """
    trajectories_summary = []
    for t in recent_trajectories[-5:]:  # 只看最近5个轨迹
        trajectories_summary.append(f"- {t.get('task_description', '无描述')} ({'成功' if t.get('overall_success') else '失败'})")
    
    recent_work = "\n".join(trajectories_summary) if trajectories_summary else "暂无完成的轨迹"
    
    prompt = f"""请回顾近期的工作，提炼值得长期保存的信息。

**【近期完成的任务】**
{recent_work}

**【当前已有记忆】**
{current_memory_context if current_memory_context else "暂无"}

**【当前已有技能】**
{current_skills_list if current_skills_list else "暂无"}

**【判断标准】**
- 完成了可复用的工作流 → **优先使用 skill_manage(action='create') 生成技能**
- 用户透露了长期有效的偏好或习惯 → 使用 add_memory(target="user")
- 发现了有用的环境事实或最佳实践 → 使用 add_memory(target="memory")

如果没有值得记录的内容，直接回答"没有需要记录的内容"。

**【重要提醒】**
- 优先创建技能而非记忆——技能是"如何做"，记忆是"是什么"
- 技能可被未来对话复用，价值远高于单条记忆
- 记忆容量有限（MEMORY约2200字符，USER约1375字符），只记录真正重要的信息
"""

    return prompt