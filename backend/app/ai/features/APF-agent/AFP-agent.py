import requests
import json
import os
import logging
import time
import uuid
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional

# ================== 加载动画（后台线程） ==================
class Spinner:
    """终端加载动画 —— 在 LLM 等待期间显示旋转指示器"""
    def __init__(self, message="思考中"):
        self.message = message
        self.running = False
        self.thread = None
        self._chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def _spin(self):
        i = 0
        while self.running:
            print(f"\r   {self._chars[i % len(self._chars)]} {self.message}...", end="", flush=True)
            time.sleep(0.1)
            i += 1

    def start(self, message=None):
        if message:
            self.message = message
        self.running = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.3)
        print("\r" + " " * (len(self.message) + 10) + "\r", end="", flush=True)

# 全局单例
_spinner = Spinner()

# ================== 脚本所在目录（所有生成文件夹均放在该目录下） ==================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

from session_store import SessionStore
from design_recorder import DesignRecorder

# ================== 导入工具注册中心 ==================
from tools.registry import tool_registry
from tools.file_tools import register_all_tools

# ================== 第09讲：导入轨迹跟踪和反思模块 ==================
from trajectory import trajectory, TaskTrajectory
from reflection import (
    build_reflection_prompt,
    build_failure_reflection_prompt,
    build_nudge_reflection_prompt
)

# ================== 配置区域 ==================
# 明文备用 Key（当环境变量未设置时使用），请替换为您的真实密钥
FALLBACK_API_KEY = "sk-86ee1add040a40abaf96b00e529903bd"
# 使用的模型（可选 "deepseek-v4-pro" 或 "deepseek-v4-flash"）
DEFAULT_MODEL = "deepseek-v4-pro"
# =============================================

# 优先使用环境变量，若无则使用明文后备
API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not API_KEY:
    API_KEY = FALLBACK_API_KEY
    print("⚠️ 未检测到环境变量 DEEPSEEK_API_KEY，使用代码中的明文 Key")

if not API_KEY or API_KEY == "您的明文API密钥":
    raise ValueError("❌ 请设置有效的 API Key：要么配置环境变量，要么修改 FALLBACK_API_KEY")

# 配置日志系统
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
log_filename = os.path.join(LOG_DIR, f"api_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class AIAgent:
    def __init__(
        self,
        system_prompt: Optional[str] = None,
        model: str = "anthropic/claude-3.5-sonnet",
        max_history_tokens: int = 4000,
        # ================== 第10讲：多用户隔离支持 ==================
        memory_store: Optional[Any] = None,
        session_store: Optional[Any] = None,
        skill_store: Optional[Any] = None,
        # ================== 设计轮次控制 ==================
        max_design_rounds: int = 15,
    ):
        # 初始化记忆存储（优先使用外部注入，否则使用全局单例）
        if memory_store is not None:
            self.memory_store = memory_store
        else:
            self.memory_store = globals().get('memory_store', None)
            if self.memory_store is None:
                # 如果全局单例也不存在，从 tools.memory_tools 导入
                from tools.memory_tools import memory_store as _ms
                self.memory_store = _ms

        # 初始化技能存储（优先使用外部注入）
        if skill_store is not None:
            self.skill_store = skill_store
        else:
            self.skill_store = globals().get('skill_store', None)
            if self.skill_store is None:
                from skill_store import skill_store as _ss
                self.skill_store = _ss
        self.skills_since_last_check = 0

        # 构建包含记忆和技能的System Prompt
        self.system_prompt = system_prompt or self._build_system_prompt_with_memory()
        self.model = model
        self.max_history_tokens = max_history_tokens

        # 确保工具已注册
        self._ensure_tools_registered()

        # 消息历史（以System Prompt开头）
        self.conversation_history: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt}
        ]

        # 工具调用信息缓存
        self._pending_tool_calls: List[Dict] = []

        # 打印记忆加载状态
        memory_context = self.memory_store.get_memory_context()
        if memory_context:
            print("🧠 已加载持久记忆:")
            print(memory_context)

        # 初始化会话存储（优先使用外部注入）
        if session_store is not None:
            self.session_store = session_store
        else:
            self.session_store = SessionStore()

        # 生成或读取当前会话ID（可以用日期+随机字符串）
        self.session_id = self._get_or_create_session_id()
        self.turn_counter = 0

        # ================== 第09讲：Nudge Engine 和轨迹跟踪 ==================
        # Nudge计数器：每完成一轮对话自动递增，达到阈值时触发反思
        self.nudge_counter = 0
        self.nudge_interval = 5  # 每5轮对话触发一次Nudge反思
        # 当前活跃的任务轨迹（由 TrajectoryTracker 单例管理）
        self.current_trajectory: Optional[TaskTrajectory] = None

        # ================== 设计轮次控制 ==================
        self.max_design_rounds = max_design_rounds  # 总设计轮次上限（可通过语言输入调整）
        self.min_design_rounds = 15  # 最少运行轮次（达到目标前不提前结束）
        self.design_round_count = 0  # 当前已完成的设计轮次
        self.design_recorder = DesignRecorder()  # 设计记录器（存盘+可视化）

    def _get_or_create_session_id(self) -> str:
        """获取或创建会话ID（用于区分不同的会话）"""
        # 简单实现：每次启动新的会话
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    def _ensure_tools_registered(self):
        """确保所有工具已注册"""
        if not tool_registry.list_tools():
            register_all_tools()
            print(f"📦 已加载 {len(tool_registry.list_tools())} 个工具:")
            for tool_name in tool_registry.list_tools():
                print(f"   🔧 {tool_name}")

    def _build_system_prompt_with_memory(self) -> str:
        """构建包含记忆、技能和会话检索的完整System Prompt"""
        base_prompt = """你是一个智能AI助手，名叫Hermes。你的回答要简洁、有帮助。

**你的角色**：
- 你是一个专业的个人助理，帮助用户解决问题
- 你擅长文件操作、命令行执行、信息检索、数学计算、时间处理等任务

**可用工具**：
- 文件操作: read_file, write_file
- 系统命令: execute_shell
- 时间处理: get_current_time, calculate_date
- 数学计算: calculate, basic_math
- 网页搜索: web_search, fetch_url
- 记忆管理: add_memory, replace_memory, remove_memory, list_memory
- 会话检索: search_memory, search_by_date, get_session_stats
- 技能管理: skill_manage, track_skill_usage, get_skill_health, mark_skill_outdated

**记忆系统**：
- 你拥有跨会话的持久记忆能力
- 每次会话开始时，系统会自动加载已有的记忆
- 当用户透露偏好、习惯或环境信息时，使用 add_memory 记录下来
- 记录时使用 target="user" 存储用户画像，target="memory" 存储环境事实
- 发现记忆中有错误信息时，使用 replace_memory 更新
- 过时的信息使用 remove_memory 清理

**记忆检索能力**：
- 你拥有跨会话的记忆检索能力，可以搜索历史对话
- 当用户问起之前讨论过的问题、提到某个旧概念、或要求回忆细节时，使用 search_memory 工具
- 搜索历史时说明关键词，如 search_memory(query="数据库配置")
- 基于检索到的历史信息来回答用户的问题
- 如果检索不到，诚实告知用户

**记忆检索的时机**：
- 用户询问"我之前说过什么"、"上次我们讨论过..."时
- 提到某个具体概念或关键词，需要确认是否之前出现过
- 想要复用之前验证过的方案时
- 帮助用户"翻旧账"找回遗漏信息时

**技能系统（Skills）——技能的"活"体现在三个层面：复用、验证、修复**：
- 技能是你的过程性记忆——记录"如何做某类任务"的成功路径
- 完成复杂任务后，使用 `skill_manage(action='create')` 将经验固化为可复用技能
- 技能应包含：操作步骤、常见陷阱、验证方法
- 技能格式遵循 agentskills.io 标准：YAML frontmatter + Markdown 正文

**技能生成触发条件**：
- 涉及3次以上工具调用的复杂任务
- 从错误中成功恢复并找到解决方案
- 走通了一条不直观但有效的流程
- 用户提供了关键修正指导

**技能复用指南（翻手册）**：
- 当用户任务描述匹配某个技能的适用场景时，使用 `skill_manage(action='read', name='技能名')` 加载详细步骤
- 技能元数据（名称+描述）已预加载到System Prompt，你需要自主判断是否匹配
- 使用 `skill_manage(action='list')` 查看完整技能列表
- 技能是你的"操作手册"——执行复杂任务时先翻手册，不要凭记忆重做

**技能验证机制（对照手册执行并确认）**：
- 执行技能步骤后，必须按技能中"## 验证方法"部分的标准进行检查
- 验证通过 → 报告成功 → 使用 track_skill_usage 记录成功
- 验证不通过 → 分析失败原因 → 判断是 patch 还是 update
  - 核心步骤正确、仅细节过时 → 使用 `skill_manage(action='patch')` 精准修复
  - 核心逻辑已完全失效 → 使用 `skill_manage(action='update')` 完全重写

**技能自我改进（发现手册有问题就改）**：
- 使用技能时，如果发现步骤过时、不完整或有错误，立即用 `skill_manage(action='patch')` 修正
- patch vs update 的选择：
  - patch：技能整体有效但部分步骤过时 → 精准替换特定段落
  - update：技能核心逻辑已失效 → 完全重写整个技能
- 不需要等待用户指示——主动维护技能库，技能是"活资产"而非"死文档"
- When using a skill and finding it outdated, incomplete, or wrong, patch it immediately — don't wait to be asked. Skills that aren't maintained become liabilities.

**技能管理规则**：
- 完成复杂任务（3+工具调用、从错误中恢复、用户提供修正）后，必须使用 `skill_manage(action='create')` 将经验沉淀为技能
- 使用技能后，根据执行效果判断技能是否有效，使用 track_skill_usage 记录结果
- 不维护的技能会成为债务，请及时更新
- 技能拥有完整的生命周期：创建 → 使用 → 验证 → 修复 → 复用

**行为准则**：
- 回答要简洁，不要啰嗦
- 如果用户的问题不明确，请主动询问澄清
- 如果你不知道答案，诚实地告诉用户，不要编造
- 使用工具后，基于工具返回的结果来回答用户
- 使用技能后，基于步骤执行并反馈结果
- 不断总结经验，让技能库越来越丰富
"""

        # 获取记忆上下文（使用已初始化的 self.memory_store）
        memory_context = self.memory_store.get_memory_context()

        # 获取技能上下文
        skills_context = self._load_skills_context()

        parts = [base_prompt]

        if memory_context:
            parts.append(f"\n{memory_context}")

        parts.append(f"\n{skills_context}")

        return "\n".join(parts)
    
    def _default_system_prompt(self) -> str:
        """默认系统提示词（第04讲版本）"""
        return """你是一个智能AI助手，名叫Hermes。你的回答要简洁、有帮助。

**你的角色**：
- 你是一个专业的个人助理，帮助用户解决问题
- 你擅长文件操作、命令行执行、信息检索、数学计算、时间处理等任务

**可用工具**：
- 文件操作: read_file, write_file
- 系统命令: execute_shell
- 时间处理: get_current_time, calculate_date
- 数学计算: calculate, basic_math
- 网页搜索: web_search, fetch_url

**工具使用指南**：
- 当用户询问时间或日期时，使用 get_current_time
- 当用户需要计算时，使用 calculate
- 当用户需要搜索信息时，使用 web_search
- 当用户要求读取文件时，使用 read_file
- 当用户要求写入文件时，使用 write_file
- 当用户要求执行命令时，使用 execute_shell

**行为准则**：
- 回答要简洁，不要啰嗦
- 如果用户的问题不明确，请主动询问澄清
- 如果你不知道答案，诚实地告诉用户，不要编造
- 使用工具后，基于工具返回的结果来回答用户
"""

    def _load_skills_context(self) -> str:
        """
        加载技能上下文（用于 System Prompt 注入）

        Hermes采用"渐进式披露"策略：
        - 技能元数据（name+description）预加载到System Prompt
        - 详细步骤在Agent需要时才按需读取
        - 用最少的tokens换取最高的信息密度
        """
        stats = self.skill_store.get_stats()

        if stats["total_skills"] == 0:
            return "\n📚 **技能库**：暂无技能。完成复杂任务后，我会自动创建技能。\n"

        # 构建技能摘要列表
        skills_metadata = self.skill_store.get_skills_for_matching()
        skills_list = "\n".join([
            f"  - **{s['display_name']}** (`{s['name']}`): {s['description'][:100]}"
            for s in skills_metadata[:10]  # 限制显示数量
        ])

        # 检查过时技能
        outdated = self.skill_store.get_outdated_skills()
        outdated_warning = ""
        if outdated:
            outdated_names = ", ".join([s['display_name'] for s in outdated])
            outdated_warning = f"\n⚠️ **过时技能警告**：{outdated_names} 需要修复。使用后请主动 patch。"

        return f"""
📚 **可用技能 ({stats['total_skills']} 个)**：
{skills_list if skills_list else '暂无'}

💡 **技能复用规则**：
- 用户任务与技能匹配时，使用 `skill_manage(action='read', name='技能名')` 加载详细步骤
- 执行后按技能的"验证方法"检查，验证通过则记录成功
- 发现步骤过时 → 立即 `skill_manage(action='patch')` 精准修复
- 核心逻辑失效 → 使用 `skill_manage(action='update')` 完全重写
- 使用 `skill_manage(action='list')` 查看完整技能列表
- When using a skill and finding it outdated, patch it immediately — don't wait.
{outdated_warning}
"""

    def _get_matching_skills(self, user_input: str) -> List[Dict]:
        """
        根据用户输入匹配技能（基于关键词的辅助匹配）

        Hermes中技能匹配主要由LLM自主完成——模型看到System Prompt中的技能列表，
        自主判断是否匹配。此方法作为辅助，在LLM调用前注入匹配提示。

        参数:
            user_input: 用户的任务描述

        返回:
            按匹配分数排序的技能列表
        """
        return self.skill_store.match_skills(user_input, limit=3)

    def _verify_skill_execution(self, skill_name: str, execution_result: Dict) -> Dict:
        """
        验证技能执行是否成功

        Hermes的验证机制基于"执行后反馈"——Agent在技能执行完成后，
        判断技能是否达到预期效果，并将验证结果纳入技能评估。

        参数:
            skill_name: 技能名称
            execution_result: 执行结果的原始返回

        返回:
            验证结果字典
        """
        # 获取技能文件中的验证方法
        skill_content = self.skill_store.read(skill_name)

        if not skill_content.get("success"):
            return {"success": False, "message": "无法读取技能内容"}

        markdown = skill_content.get("content", "")

        # 提取"验证方法"部分
        verification_section = self._extract_verification_section(markdown)

        # 如果没有定义验证方法，根据执行结果粗略判断
        if not verification_section:
            # 检查执行结果中是否有明显的错误标志
            if "error" in str(execution_result).lower():
                result_verdict = "partial"
                verification_details = "执行结果中有错误信息"
            elif execution_result.get("success", False):
                result_verdict = "success"
                verification_details = "执行报告成功"
            else:
                result_verdict = "failed"
                verification_details = "执行未报告成功"
        else:
            # 有明确的验证方法，让模型来判断（通过后续的LLM调用）
            result_verdict = "unknown"
            verification_details = f"需按验证方法检查: {verification_section[:200]}"

        # 根据验证结果决定行动
        action_needed = None
        if result_verdict == "failed":
            action_needed = "patch"
        elif result_verdict == "partial":
            action_needed = "review"  # 需要人工/模型审查

        return {
            "success": result_verdict == "success",
            "skill_name": skill_name,
            "verdict": result_verdict,
            "details": verification_details,
            "action_needed": action_needed
        }

    def _extract_verification_section(self, markdown: str) -> str:
        """
        从SKILL.md中提取"验证方法"部分

        Hermes的技能文件包含"## 验证方法"章节，Agent执行完技能步骤后，
        按此标准进行检查，形成"执行-验证-修复-复用"的闭环。
        """
        import re
        pattern = r'##\s*验证方法\s*\n+(.*?)(?=\n##|\Z)'
        match = re.search(pattern, markdown, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""

    def _add_verification_to_prompt(self, skill_name: str, step_context: str = "") -> str:
        """
        为技能调用添加验证提示

        当Agent读取技能后，此方法生成验证提示，指导Agent执行后
        按技能定义的验证标准检查，形成验证闭环。
        """
        skill_content = self.skill_store.read(skill_name)

        if not skill_content.get("success"):
            return ""

        markdown = skill_content.get("content", "")
        verification_section = self._extract_verification_section(markdown)

        if verification_section:
            return f"""
**【执行完成后验证】**
请按以下标准验证技能是否成功执行：
{verification_section}

如果验证通过，报告成功。
如果验证不通过，使用 skill_manage(action='patch', name='{skill_name}', old_text='[需修复的步骤]', new_text='[修正后的步骤]') 进行修复。
如果技能中的步骤存在更严重的问题，考虑使用 skill_manage(action='update') 重写。
"""
        return ""

    def _should_create_skill(self, task_complexity: dict) -> bool:
        """
        判断当前任务是否值得生成技能

        Hermes 的触发条件（与书中第5节一致）：
        - 工具调用次数 ≥ 3
        - 发生过错误恢复
        - 用户提供了修正指导
        - 走通了复杂的多步骤流程
        """
        triggers = []

        if task_complexity.get("tool_calls", 0) >= 3:
            triggers.append("complex_task")
        if task_complexity.get("had_error_recovery"):
            triggers.append("error_recovery")
        if task_complexity.get("had_user_guidance"):
            triggers.append("user_guidance")

        should_create = len(triggers) >= 1

        if should_create:
            print(f"🎯 检测到技能生成触发条件: {', '.join(triggers)}")

        return should_create

    def _trigger_skill_reflection(self, task_complexity: dict):
        """
        触发技能反思：判断复杂任务的经验是否应该沉淀为技能

        Hermes 使用 skill_manage 工具自主创建技能。
        受 skills_since_last_check 冷却控制，不会每次对话都触发。
        """
        if not self._should_create_skill(task_complexity):
            return

        # 重置冷却计数器（_iters_since_skill 归零）
        self.skills_since_last_check = 0

        print("🔔 [Nudge] 检测到复杂任务，正在总结经验并生成技能...")

        # 构建技能生成的提示词
        reflection_prompt = f"""
请基于刚才完成的任务，创建一个可复用的技能（Skill）文档。

**【任务复杂度指标】**
- 工具调用次数: {task_complexity.get('tool_calls', 0)}
- 经历过错误恢复: {task_complexity.get('had_error_recovery', False)}
- 用户提供了修正: {task_complexity.get('had_user_guidance', False)}

**【技能要求】**
1. 技能名称：使用小写连字符格式，如 'deploy-flask'
2. YAML frontmatter 必须包含 name 和 description
3. 正文应包含：操作步骤、常见陷阱、验证方法
4. 参考以下格式：

---
name: example-skill
description: 示例技能：解决X类问题的标准步骤
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [example, tutorial]
    category: general
---

## 何时使用
描述技能的适用场景。

## 操作步骤
详细的操作步骤。

## 常见陷阱
- 陷阱1及其解决方法

## 验证方法
确认技能有效的方法。

请调用 `skill_manage(action='create')` 来创建这个技能。技能名称请根据任务内容自行命名。
"""
        # 调用模型进行技能反思
        print("🤖 Hermes 正在总结技能经验...")
        self.call_llm_and_extract_skill(reflection_prompt)

    def _get_recent_exchange(self) -> List[Dict]:
        """
        安全截取最近一轮对话（从最近一条 user 消息开始），
        保证 assistant(tool_calls) → tool 的完整配对，避免 API 400 错误。
        """
        # 先做全量清理
        self._sanitize_history()

        # 从后往前找最近一条 user 消息
        start_idx = 1  # 默认跳过 system prompt
        for i in range(len(self.conversation_history) - 1, 0, -1):
            if self.conversation_history[i]["role"] == "user":
                start_idx = i
                break

        result = self.conversation_history[start_idx:]

        # 二次清理：确保截取片段开头没有孤立的 tool 消息
        while len(result) > 0 and result[0].get("role") == "tool":
            result.pop(0)

        return result

    def call_llm_and_extract_skill(self, user_prompt: str):
        """调用模型进行技能反思，让Agent自主创建技能"""
        # 构建包含对话上下文的消息列表
        messages = [{"role": "system", "content": "你是一个技能总结助手。请根据对话历史，将刚才完成的任务经验沉淀为可复用技能。"}]

        # 安全截取：从最近一条 user 消息开始，保证 tool_calls→tool 完整配对
        messages.extend(self._get_recent_exchange())

        # 最后追加重构反思指令
        messages.append({"role": "user", "content": user_prompt})

        # 调用模型（带工具），模型会自主决定是否调用 skill_manage
        response = self._call_llm_with_tools(messages)

        if "error" in response:
            print(f"   ⚠️ 技能反思调用失败: {response['error']}")
            return

        message = response["message"]
        finish_reason = response["finish_reason"]

        # 如果模型决定调用工具（skill_manage），执行工具调用
        if finish_reason == "tool_calls" and "tool_calls" in message:
            tool_results = self._execute_tool_calls(message["tool_calls"])
            for tr in tool_results:
                status = "✅" if tr["result"].get("success", True) else "❌"
                action = tr["result"].get("action", "")
                msg = tr["result"].get("message", tr["result"].get("error", ""))
                print(f"   {status} 技能{action}: {msg}")
        else:
            content = message.get("content", "")
            if content:
                print(f"   📝 反思结果: {content[:200]}...")

    def _sanitize_history(self) -> int:
        """
        扫描全部历史，删除所有孤立的 tool 消息。

        DeepSeek API 要求每条 role='tool' 消息前必须有对应的
        assistant(tool_calls) 消息。同一个 assistant 可能触发多条 tool 消息，
        因此需要向前跳过连续的 tool 消息找到真正的配对 assistant。

        返回被清理的消息数量。
        """
        removed = 0
        i = 1  # 跳过 system prompt（index 0）
        while i < len(self.conversation_history):
            msg = self.conversation_history[i]
            if msg.get("role") == "tool":
                # 向前查找最近的非 tool 消息（跳过连续的 tool 消息）
                j = i - 1
                while j >= 0 and self.conversation_history[j].get("role") == "tool":
                    j -= 1
                # j 现在是最近的非 tool 消息，必须是 assistant 且含 tool_calls
                if j < 0 or not (
                    self.conversation_history[j].get("role") == "assistant"
                    and self.conversation_history[j].get("tool_calls")
                ):
                    self.conversation_history.pop(i)
                    removed += 1
                    continue  # 不递增 i，pop 后当前索引指向下一条
            i += 1
        return removed

    def _estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """估算消息列表的token数量（简化：1 token ≈ 4个字符）"""
        total_chars = 0
        for msg in messages:
            total_chars += len(msg.get("content", ""))
        return total_chars // 4

    def _truncate_history(self):
        """
        截断过长的历史，保证 assistant(tool_calls) → tool 配对完整。

        策略：从后往前累计 token，在 user 消息处截断。
        截断后自动清理孤立的 tool 消息。
        """
        if self._estimate_tokens(self.conversation_history) <= self.max_history_tokens:
            return

        # 先做一次清理
        self._sanitize_history()

        # 找到安全截断点（user 消息）
        safe_cut = 1  # 至少保留 system prompt
        running_tokens = self._estimate_tokens([self.conversation_history[0]])

        for i in range(1, len(self.conversation_history)):
            msg_tokens = self._estimate_tokens([self.conversation_history[i]])
            running_tokens += msg_tokens

            if running_tokens > self.max_history_tokens:
                break

            if self.conversation_history[i].get("role") == "user":
                safe_cut = i

        if safe_cut > 1 and safe_cut < len(self.conversation_history) - 1:
            self.conversation_history = (
                [self.conversation_history[0]] +
                self.conversation_history[safe_cut:]
            )

        # 截断后再清理一次（以防截断点破坏了配对）
        self._sanitize_history()
    
    def add_user_message(self, message: str):
        self.conversation_history.append({"role": "user", "content": message})
    
    def add_assistant_message(self, message: str):
        self.conversation_history.append({"role": "assistant", "content": message})
    
    def _generate_summary(self, user_message: str, assistant_message: str) -> Optional[str]:
        """
        生成对话摘要（简化版：截取前200字符作为摘要）

        在实际部署中，这里可以调用LLM生成高质量摘要。
        Hermes的设计：摘要用于加速检索和降低存储成本。
        """
        combined = f"Q: {user_message}\nA: {assistant_message}"
        if len(combined) <= 200:
            return combined
        return combined[:197] + "..."

    def _record_exchange(self, user_message: str, assistant_message: str):
        """记录一轮对话到持久化数据库"""
        self.turn_counter += 1

        self.session_store.add_exchange(
            session_id=self.session_id,
            user_message=user_message,
            assistant_message=assistant_message,
            turn_number=self.turn_counter,
            tool_calls=self._pending_tool_calls if self._pending_tool_calls else None,
            summary=self._generate_summary(user_message, assistant_message)
        )

        # 重置本轮工具调用记录
        self._pending_tool_calls = []

        print(f"📝 已记录第{self.turn_counter}轮对话到会话数据库")

    def clear_history(self):
        self.conversation_history = [{"role": "system", "content": self.system_prompt}]
        print("🗑️ 对话历史已清空")
    
    def get_history_length(self) -> int:
        return len(self.conversation_history)
    
    def call_llm_stream(self, messages: List[Dict[str, str]]) -> str:
        """
        流式调用 DeepSeek API（仅用于普通对话，不携带 tools）
        """
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True
        }
        
        # 记录请求信息
        request_info = {
            "url": url,
            "method": "POST",
            "headers": {k: v for k, v in headers.items() if k != "Authorization"},
            "payload": payload,
            "timestamp": datetime.now().isoformat()
        }
        logger.info(f"REQUEST: {json.dumps(request_info, ensure_ascii=False, indent=2)}")
        
        response = requests.post(url, headers=headers, json=payload, stream=True)
        
        if response.status_code != 200:
            error_msg = f"API 错误：{response.status_code} - {response.text}"
            print(f"\n❌ {error_msg}")
            error_info = {
                "status_code": response.status_code,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"RESPONSE ERROR: {json.dumps(error_info, ensure_ascii=False, indent=2)}")
            return error_msg
        
        full_response = ""
        raw_chunks = []
        
        for line in response.iter_lines(decode_unicode=True):
            if line:
                raw_chunks.append(line)
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            print(content, end="", flush=True)
                            full_response += content
                    except json.JSONDecodeError:
                        pass
        
        print()
        
        response_info = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "raw_chunks": raw_chunks,
            "full_response": full_response,
            "timestamp": datetime.now().isoformat()
        }
        logger.info(f"RESPONSE: {json.dumps(response_info, ensure_ascii=False, indent=2)}")
        
        return full_response
    
    def _call_llm_with_tools(self, messages: List[Dict]) -> Dict[str, Any]:
        """
        非流式调用 LLM，支持工具调用（携带 tools 参数）
        """
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        tools = tool_registry.get_schemas()
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "stream": False
        }
        
        # 记录请求信息
        request_info = {
            "url": url,
            "method": "POST",
            "headers": {k: v for k, v in headers.items() if k != "Authorization"},
            "payload": payload,
            "timestamp": datetime.now().isoformat()
        }
        logger.info(f"TOOL REQUEST: {json.dumps(request_info, ensure_ascii=False, indent=2)}")

        # 启动加载动画
        _spinner.start("LLM 推理中")
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
        finally:
            _spinner.stop()

        if response.status_code != 200:
            error_msg = f"API 错误：{response.status_code} - {response.text}"
            error_info = {
                "status_code": response.status_code,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"TOOL RESPONSE ERROR: {json.dumps(error_info, ensure_ascii=False, indent=2)}")
            return {"error": error_msg}
        
        result = response.json()
        logger.info(f"TOOL RESPONSE: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        message = result["choices"][0]["message"]
        finish_reason = result["choices"][0]["finish_reason"]
        
        return {
            "message": message,
            "finish_reason": finish_reason
        }
    
    def _execute_tool_calls(self, tool_calls: List[Dict], max_retries: int = 2) -> List[Dict]:
        """
        执行工具调用（支持重试）
        
        参数:
            tool_calls: LLM返回的tool_calls列表
            max_retries: 每个工具的最大重试次数
        """
        results = []
        
        for tool_call in tool_calls:
            if "function" in tool_call:
                tool_name = tool_call["function"]["name"]
                arguments = json.loads(tool_call["function"]["arguments"])
                tool_id = tool_call.get("id", "")
            else:
                tool_name = tool_call.get("name", "")
                arguments = tool_call.get("arguments", {})
                tool_id = tool_call.get("id", "")
            
            handler = tool_registry.get_handler(tool_name)
            
            if not handler:
                results.append({
                    "tool_call_id": tool_id,
                    "tool_name": tool_name,
                    "result": {"success": False, "error": f"未知工具: {tool_name}"}
                })
                continue
            
            # 带重试的执行
            result = None
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    result = handler(**arguments)
                    
                    # 检查结果中的success标志
                    if isinstance(result, dict):
                        if result.get("success", True):
                            break  # 成功，跳出重试循环
                        else:
                            last_error = result.get("error", "执行返回失败")
                            # 非瞬态错误（已存在/不存在/权限等）不应重试
                            non_retry_keywords = ["已存在", "不存在", "权限", "格式错误", "不能为空"]
                            is_non_retryable = any(kw in last_error for kw in non_retry_keywords)
                            if is_non_retryable:
                                break  # 不重试
                            if attempt < max_retries:
                                print(f"   ⚠️ 工具 {tool_name} 重试 {attempt+1}/{max_retries}: {last_error}")
                                time.sleep(1.0 * (attempt + 1))  # 递增等待
                            continue
                    else:
                        break  # 非字典结果视为成功
                        
                except Exception as e:
                    last_error = str(e)
                    if attempt < max_retries:
                        print(f"   ⚠️ 工具 {tool_name} 重试 {attempt+1}/{max_retries}: {last_error}")
                        time.sleep(1.0 * (attempt + 1))
                    continue
            
            # 如果所有重试都失败
            if result is None or (isinstance(result, dict) and not result.get("success", True)):
                result = {"success": False, "error": f"重试{max_retries}次后失败: {last_error}"}
            
            results.append({
                "tool_call_id": tool_id,
                "tool_name": tool_name,
                "result": result
            })

            print(f"   🔧 执行工具: {tool_name}")
            # 参数: JSON 显示
            args_display = json.dumps(arguments, ensure_ascii=False)
            print(f"   📥 参数: {args_display}")
            # 结果: 完整 JSON 输出，不截断
            status = "✅" if result.get("success", True) else "❌"
            try:
                result_display = json.dumps(result, ensure_ascii=False, indent=2)
            except (TypeError, ValueError):
                result_display = json.dumps(result, ensure_ascii=False)
            print(f"   {status} 结果:\n{result_display}")
        
        return results
    
    def chat(self, user_input: str) -> str:
        """
        单轮对话入口，支持多轮工具调用，支持技能匹配和复用，并自动记录到数据库

        Hermes的技能复用流程：
        1. 用户输入 → 技能匹配（关键词辅助） → 注入匹配提示
        2. LLM自主判断是否匹配技能 → 调用 skill_manage(action='read')
        3. 执行技能步骤 → 验证执行结果
        4. 验证通过/失败 → 记录统计/触发patch修复
        """
        # ================== 解析用户指定的设计轮次 ==================
        import re as _re
        round_match = _re.search(r'(\d+)\s*[轮论]', user_input)
        if round_match:
            parsed_rounds = int(round_match.group(1))
            if 1 <= parsed_rounds <= 100:
                self.max_design_rounds = parsed_rounds
                print(f"🎯 设计轮次已设置为: {self.max_design_rounds} 轮")

        # 技能匹配：根据用户输入查找相关技能
        matched_skills = self._get_matching_skills(user_input)

        # 如果有匹配的技能，增强用户消息（辅助LLM决策）
        enhanced_input = user_input
        if matched_skills:
            best_match = matched_skills[0]
            skill_hint = (
                f"\n\n💡 **技能匹配提示**: 用户的请求与技能 "
                f"'{best_match['display_name']}' (匹配分数: {best_match['match_score']}) 相关。"
            )
            if best_match['match_score'] >= 5:
                skill_hint += (
                    f" 如果确定匹配，请使用 skill_manage(action='read', "
                    f"name='{best_match['skill_name']}') 加载详细步骤，"
                    f"执行后按技能的验证标准检查结果。"
                )
            enhanced_input = user_input + skill_hint

            if matched_skills[0]["match_score"] >= 5:
                print(f"🎯 技能匹配: '{matched_skills[0]['display_name']}' (分数: {matched_skills[0]['match_score']})")

        self.add_user_message(enhanced_input)
        self._truncate_history()

        # ================== 第09讲：开始任务轨迹跟踪 ==================
        if not self.current_trajectory:
            self.current_trajectory = trajectory.start_trajectory(user_input)
        else:
            # 如果有未结束的轨迹，追加新任务描述
            self.current_trajectory.task_description += f"; {user_input}"

        # 重置本轮工具调用记录
        self._pending_tool_calls = []

        # 跟踪任务复杂度（用于技能生成判断）
        task_complexity = {
            "tool_calls": 0,
            "had_error_recovery": False,
            "had_user_guidance": False
        }

        # 多轮工具调用循环：直到 LLM 不再请求工具，或达到轮次上限
        # 每轮 LLM 调用（含工具调用）消耗 1 个循环计数
        # 设计轮次 = 完成 mutation+evaluate+simulate 的次数
        remaining_design_rounds = max(3, self.max_design_rounds - self.design_round_count)
        max_rounds = min(remaining_design_rounds * 3 + 2, 60)  # 每设计轮约需3次LLM调用
        mutation_count_this_chat = 0
        for loop_idx in range(max_rounds):
            response = self._call_llm_with_tools(self.conversation_history)

            if "error" in response:
                print(f"\n❌ {response['error']}")
                self._record_exchange(user_input, response['error'])

                # ================== 第09讲：API错误时完成轨迹并触发失败学习 ==================
                completed_traj = trajectory.finish_trajectory()
                if completed_traj:
                    completed_traj.add_error(message=response['error'], context="LLM API调用失败")
                    completed_traj.mark_failure(f"API错误: {response['error']}")
                    self._trigger_failure_learning(completed_traj)

                return response['error']

            message = response["message"]
            finish_reason = response["finish_reason"]

            # 如果 LLM 请求工具调用
            if finish_reason == "tool_calls" and "tool_calls" in message:
                # 累积记录本轮工具调用
                self._pending_tool_calls.extend(message["tool_calls"])

                # 累积工具调用计数
                task_complexity["tool_calls"] += len(message["tool_calls"])

                # ================== 第09讲：记录工具调用到轨迹 ==================
                traj = trajectory.get_current_trajectory()
                if traj:
                    for tc in message["tool_calls"]:
                        tool_name = tc.get("function", {}).get("name", tc.get("name", "unknown"))
                        tool_args = {}
                        try:
                            raw_args = tc.get("function", {}).get("arguments", tc.get("arguments", "{}"))
                            tool_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                        except (json.JSONDecodeError, TypeError):
                            tool_args = {"raw": str(raw_args)}
                        traj.add_tool_call(
                            name=tool_name,
                            arguments=tool_args,
                            result={},
                            duration_ms=0.0,
                            success=True  # 先标记成功，执行后如有错误再更新
                        )

                # 检测本轮是否包含突变操作（用于设计轮次计数和轮次提示）
                has_mutation = any(
                    tc.get("function", tc).get("name", "") == "afp_mutate_sequence"
                    for tc in message["tool_calls"]
                )
                has_evaluate = any(
                    tc.get("function", tc).get("name", "") == "afp_evaluate_mutation"
                    for tc in message["tool_calls"]
                )

                if has_mutation:
                    mutation_count_this_chat += 1
                    self.design_round_count += 1
                    # ================== 轮次开始提示 ==================
                    remaining = self.max_design_rounds - self.design_round_count
                    print(f"\n{'='*50}")
                    print(f"🧬 Round {self.design_round_count}/{self.max_design_rounds} — 开始突变设计")
                    print(f"{'='*50}")

                # 将助手的工具调用请求加入历史
                self.conversation_history.append(message)

                # 执行工具
                tool_results = self._execute_tool_calls(message["tool_calls"])

                # 检查是否有错误恢复（任何工具执行失败视为错误恢复）
                for tr in tool_results:
                    if isinstance(tr.get("result"), dict) and not tr["result"].get("success", True):
                        task_complexity["had_error_recovery"] = True
                        # ================== 第09讲：记录错误到轨迹 ==================
                        if traj:
                            error_msg = tr["result"].get("error", "工具执行失败")
                            traj.add_error(message=error_msg, context=f"工具: {tr.get('tool_name', 'unknown')}")
                        break

                # 将工具执行结果加入历史
                for tr in tool_results:
                    result_content = tr["result"]

                    # 【技能验证钩子】LLM 读取技能后，自动注入验证提示
                    # 实现"执行→验证→修复→复用"闭环中的"验证"环节
                    if tr["tool_name"] == "skill_manage" and isinstance(result_content, dict):
                        if result_content.get("action") == "read" and result_content.get("success"):
                            skill_name = result_content.get("skill_name", "")
                            if skill_name:
                                verification = self._add_verification_to_prompt(skill_name)
                                if verification:
                                    result_content = dict(result_content)
                                    result_content["_verification_guidance"] = verification
                                    print(f"   🔍 技能验证提示已注入: {skill_name}")

                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tr["tool_call_id"],
                        "content": json.dumps(result_content, ensure_ascii=False)
                    })

                # ================== 记录设计基线（输入序列分析） ==================
                if not getattr(self.design_recorder, '_analysis_saved', False):
                    for tr in tool_results:
                        if tr.get("tool_name") == "afp_knowledge_query":
                            r = tr.get("result", {})
                            if r.get("success"):
                                self.design_recorder.design_target = user_input[:200]
                                self.design_recorder.save_input_analysis(r)
                                self.design_recorder._analysis_saved = True
                                print(f"   📁 会话 ID: {self.design_recorder.get_session_id()}")
                            break

                # ================== 轮次结束提示 + 记录本轮数据 ==================
                if has_mutation and has_evaluate:
                    # 本轮同时包含突变+评估 → 输出轮次小结
                    eval_result = None
                    sim_result = None
                    for tr in tool_results:
                        if tr.get("tool_name") == "afp_evaluate_mutation":
                            eval_result = tr.get("result", {})
                        if tr.get("tool_name") == "afp_ice_bind_simulate":
                            sim_result = tr.get("result", {})

                    verdict = eval_result.get("verdict", "?") if eval_result else "?"
                    verdict_icon = {"PASS": "✅", "WARNING": "⚠️", "REJECTED": "❌", "CAUTION": "🟡"}.get(verdict, "❓")
                    sim_changes = sim_result.get("comparison_with_original", {}).get("changes", {}) if sim_result else {}
                    th_change = sim_changes.get("th_change_pct", 0)
                    iri_change = sim_changes.get("iri_change_pct", 0)

                    remaining = self.max_design_rounds - self.design_round_count
                    print(f"{'─'*50}")
                    print(f"📊 Round {self.design_round_count} 小结 | 判定: {verdict_icon} {verdict} | "
                          f"TH {th_change:+.1f}% | IRI {iri_change:+.1f}% | 剩余 {remaining} 轮")
                    print(f"{'─'*50}")

                    # ================== 记录本轮数据到文件 ==================
                    # 提取突变参数和理由
                    mut_args = {}
                    mut_rationale = ""
                    for tc in message["tool_calls"]:
                        fn = tc.get("function", tc)
                        if fn.get("name") == "afp_mutate_sequence":
                            try:
                                raw = fn.get("arguments", "{}")
                                mut_args = json.loads(raw) if isinstance(raw, str) else raw
                                mut_rationale = mut_args.get("rationale", "")
                            except (json.JSONDecodeError, TypeError):
                                pass
                            break

                    mutations_list = mut_args.get("mutations", [])
                    if isinstance(mutations_list, str):
                        try:
                            mutations_list = json.loads(mutations_list)
                        except (json.JSONDecodeError, TypeError):
                            mutations_list = []

                    self.design_recorder.record_round(
                        round_num=self.design_round_count,
                        original_seq=mut_args.get("original_sequence", ""),
                        mutated_seq=mut_args.get("mutated_sequence", ""),
                        mutations=mutations_list,
                        rationale=mut_rationale,
                        eval_result=eval_result,
                        sim_result=sim_result,
                    )

                # 继续循环，让 LLM 查看工具结果后决定是否继续调工具
                continue

            else:
                # 无工具调用 — LLM 给出了文本回复
                content = message.get("content", "")
                for char in content:
                    print(char, end="", flush=True)
                    time.sleep(0.01)
                print()
                self.add_assistant_message(content)

                # ================== 判断是否需要继续设计 ==================
                is_design_task = mutation_count_this_chat > 0

                remaining = self.max_design_rounds - self.design_round_count
                min_rounds = getattr(self, 'min_design_rounds', 15)

                # 检测 LLM 是否认为设计已完成
                completion_markers = [
                    "设计完成", "最终报告", "FINAL", "达到目标",
                    "设计最终报告", "AFP 设计最终报告",
                ]
                design_complete = any(m in content for m in completion_markers)

                # 提前结束条件：达到最小轮数 AND (达到上限 或 LLM 认为完成)
                can_stop_early = (
                    self.design_round_count >= min_rounds
                    and (remaining <= 0 or design_complete)
                )

                if not can_stop_early and remaining > 0:
                    # 注入继续指令
                    if self.design_round_count < min_rounds:
                        hint = (f"至少还需完成 {min_rounds - self.design_round_count} 轮设计。"
                                f"请继续调用 afp_mutate_sequence 进行下一轮突变。")
                    else:
                        hint = (f"还剩 {remaining} 轮。请继续下一轮突变，"
                                f"或如果已达成目标，调用 afp_design_summary 总结。")
                    continue_prompt = (
                        f"\n\n⚠️ **设计继续**：当前 {self.design_round_count}/{self.max_design_rounds} 轮。{hint}"
                    )
                    self.conversation_history.append({
                        "role": "user",
                        "content": continue_prompt,
                    })
                    print(f"\n🔄 自动继续 (第{self.design_round_count}/{self.max_design_rounds}轮, 至少还需{max(0, min_rounds - self.design_round_count)}轮)...")
                    continue  # 继续循环

                # 设计完成或达到上限 — 记录并返回
                self._record_exchange(user_input, content)

                # ================== 保存设计记录 ==================
                if self.design_recorder and self.design_round_count > 0:
                    self.design_recorder.save_summary()
                    print(f"   📁 设计数据目录: {self.design_recorder.get_session_dir()}")

                completed_traj = trajectory.finish_trajectory()
                if completed_traj:
                    completed_traj.mark_success("LLM 完成设计并给出回复")

                    if completed_traj.should_create_skill():
                        self._trigger_skill_generation_from_trajectory(completed_traj)

                if self.skills_since_last_check >= 3:
                    self._trigger_skill_reflection(task_complexity)

                return content

        # 达到最大轮次仍未结束 → 注入总结指令
        remaining = self.max_design_rounds - self.design_round_count
        if remaining <= 0:
            summary_prompt = (
                f"已达到设计轮次上限 ({self.max_design_rounds}轮)。"
                f"请调用 afp_design_summary 总结所有设计结果，"
                f"然后输出最终设计报告（包含: 原始/最终序列、突变路径、性能对比、设计经验）。"
            )
        else:
            summary_prompt = (
                f"已达到单轮工具调用上限。当前已完成 {self.design_round_count}/{self.max_design_rounds} 轮设计。"
                f"请总结当前进展，并指明下一步方向。"
            )

        # 追加总结指令到历史，让 LLM 再回答一次
        self.conversation_history.append({"role": "user", "content": summary_prompt})
        print(f"\n📊 {summary_prompt[:100]}...")

        # 最后一次 LLM 调用（不带工具，直接文本回复）
        try:
            response = self._call_llm_with_tools(self.conversation_history)
            if "error" not in response:
                content = response.get("message", {}).get("content", "")
                if content:
                    print(f"\n🤖 Hermes: {content}")
                    self.add_assistant_message(content)
                    self._record_exchange(user_input, content)
                    return content
        except Exception:
            pass

        fallback = f"设计流程结束。共完成 {self.design_round_count}/{self.max_design_rounds} 轮设计。"
        self.add_assistant_message(fallback)
        self._record_exchange(user_input, fallback)

        completed_traj = trajectory.finish_trajectory()
        if completed_traj:
            completed_traj.mark_failure("达到工具调用上限")

            if not completed_traj.overall_success:
                self._trigger_failure_learning(completed_traj)

        if self.skills_since_last_check >= 3:
            self._trigger_skill_reflection(task_complexity)

        return fallback

    
    def run(self):
        """主对话循环（第09讲：整合自进化学习闭环）"""
        print("=" * 60)
        skills_count = self.skill_store.get_stats()["total_skills"]
        print(f"🤖 Hermes Agent v0.9.0 (自进化版)")
        print(f"📝 模型: {self.model}")
        print(f"⏰ Nudge间隔: 每{self.nudge_interval}轮对话")
        print(f"🧠 技能触发条件: 5+工具调用 / 错误恢复 / 用户纠正")
        print(f"📦 可用工具: {', '.join(tool_registry.list_tools())}")
        print(f"📚 已加载技能: {skills_count} 个")
        print("⌨️  可用命令:")
        print("   /clear    - 清空对话历史")
        print("   /history  - 查看对话历史")
        print("   /tools    - 查看可用工具")
        print("   /memory   - 查看当前持久记忆")
        print("   /skills         - 查看技能库")
        print("   /skills status  - 查看技能运行状况报告")
        print("   /nudge    - 手动触发记忆反思")
        print("   /sessions - 查看会话数据库统计")
        print("   /quit     - 退出程序")
        print("=" * 60)

        while True:
            try:
                user_input = input("\n👤 你: ").strip()

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    self._handle_command(user_input)
                    continue

                # 执行对话（chat() 内部已整合轨迹跟踪和学习循环触发）
                self.chat(user_input)

                # ================== 第09讲：Nudge Engine 计数器 ==================
                # 每轮对话后递增Nudge计数器
                self.nudge_counter += 1
                self.skills_since_last_check += 1

                # 到达Nudge阈值时触发周期性反思
                if self.nudge_counter >= self.nudge_interval:
                    self._nudge_reflection()
                    self.nudge_counter = 0  # 反思完成后重置计数器

            except KeyboardInterrupt:
                print("\n\n👋 使用 /quit 退出")
            except Exception as e:
                print(f"\n❌ 发生错误: {e}")
                # ================== 第09讲：错误驱动的即时触发 ==================
                # 当发生异常时，立即触发失败学习（不走计数器等待）
                traj = trajectory.get_current_trajectory()
                if traj:
                    traj.add_error(message=str(e), context="对话循环异常")
                    traj.mark_failure(f"异常中断: {e}")
                completed_traj = trajectory.finish_trajectory()
                if completed_traj and not completed_traj.overall_success:
                    self._trigger_failure_learning(completed_traj)
    

    def _trigger_reflection(self, turn_count: int):
        """触发Nudge反思：提醒Agent回顾对话，判断哪些值得记"""
        print(f"\n🔔 [Nudge: 第{turn_count}轮] 正在回顾刚才的对话，判断哪些值得永久记住...")
        
        reflection_prompt = f"""请快速回顾一下刚才的全部对话（共{turn_count}轮）。判断是否有值得记录到持久记忆的信息。

    **【反思标准】**
    - 用户透露了姓名、偏好、习惯、工作方式 → 记入 USER.md
    - 用户纠正了你的错误 → 更新或更正 MEMORY.md 中的相关条目
    - 出现了环境事实（项目路径、依赖、服务器地址） → 记入 MEMORY.md
    - 重复出现的问题或成功的工作流 → 使用 skill_manage(action='create') 沉淀为技能

    **【操作指南】**
    - 使用 add_memory(target="user") 记录用户偏好
    - 使用 add_memory(target="memory") 记录环境事实
    - 使用 replace_memory 更正过时的信息
    - 如果没有值得记录的内容，直接说"没有需要记录的内容"

    **【当前已有记忆】**
    {self.memory_store.get_memory_context() if self.memory_store.get_memory_context() else "暂无"}

    **【特别注意】**
    - 记忆是跨会话永久的！只记录真正重要的、长期有效的信息。
    - 记录要简洁明确，每条记忆应是一个完整的事实陈述。
    - 不要记录临时性的、一次性的信息。
    - USER.md + MEMORY.md 总容量约 3500 字符（约 1300 tokens），记录前请确认容量是否充足。

    请基于以上标准进行反思。"""
        
        print("🤖 Hermes 正在自我反思中...")
        # 调用模型进行反思，但不保存到对话历史
        self.call_llm_and_extract_memory(reflection_prompt)


    def call_llm_and_extract_memory(self, user_prompt: str):
        """调用模型进行反思，提取值得记忆的信息并执行记忆工具"""
        # 构建包含对话上下文的消息列表
        messages = [{"role": "system", "content": "你是一个记忆管理助手。请根据对话历史，判断是否有值得记录到持久记忆的信息。"}]

        # 安全截取：从最近一条 user 消息开始，保证 tool_calls→tool 完整配对
        messages.extend(self._get_recent_exchange())

        # 最后追加重构反思指令
        messages.append({"role": "user", "content": user_prompt})

        # 调用模型（带工具），模型会自主决定是否调用记忆工具
        response = self._call_llm_with_tools(messages)

        if "error" in response:
            print(f"   ⚠️ 记忆反思调用失败: {response['error']}")
            return

        message = response["message"]
        finish_reason = response["finish_reason"]

        # 如果模型决定调用工具（add_memory, replace_memory 等），执行工具调用
        if finish_reason == "tool_calls" and "tool_calls" in message:
            tool_results = self._execute_tool_calls(message["tool_calls"])
            for tr in tool_results:
                status = "✅" if tr["result"].get("success", True) else "❌"
                tool_name = tr.get("tool_name", "")
                msg = tr["result"].get("message", tr["result"].get("error", ""))
                print(f"   {status} 记忆工具 {tool_name}: {msg}")
        else:
            content = message.get("content", "")
            if content and "没有需要记录" not in content:
                print(f"   📝 反思结果: {content[:200]}...")
    
    # ================== 第09讲：自进化学习循环方法 ==================

    def _call_llm_for_reflection(self, prompt: str, context: str = "reflection"):
        """
        调用LLM执行反思（不保存到对话历史，但允许工具调用）

        Hermes学习循环的核心执行器——无论是Nudge反思、技能生成还是失败学习，
        都通过此方法调用LLM，LLM自主决定调用 skill_manage、add_memory 等工具。

        参数:
            prompt: 反思提示词
            context: 反思上下文标签（用于日志区分和系统提示词定制）
        """
        # 根据反思上下文定制系统提示词，引导 LLM 选择正确的工具
        context_prompts = {
            "skill_creation": (
                "你是Hermes的技能创建助手。你的任务是将刚才的任务经验固化为可复用技能。"
                "请务必调用 skill_manage(action='create') 创建技能。"
                "技能命名使用小写连字符格式（如 'design-afp-mutation'），"
                "frontmatter 必须包含 name 和 description，content 包含操作步骤、常见陷阱、验证方法。"
            ),
            "failure_learning": (
                "你是Hermes的失败学习助手。你的任务是从失败中提炼教训。"
                "请务必调用 skill_manage(action='create') 创建一个技能，记录："
                "1) 失败的原因 2) 如何避免 3) 正确的操作步骤。"
                "技能命名如 'avoid-xxx-error'，这会让Hermes在未来避免重复同样的错误。"
            ),
            "nudge": (
                "你是Hermes的定期回顾助手。请回顾近期对话，"
                "判断是否有值得长期保存的信息。如果有经验可复用，"
                "调用 skill_manage(action='create') 创建技能；"
                "如果只涉及用户偏好或环境事实，调用 add_memory 记录。"
            ),
        }
        system_content = context_prompts.get(
            context,
            f"你是Hermes的{context}助手。请根据对话历史做出决策，"
            f"优先调用 skill_manage(action='create') 创建技能来沉淀可复用经验。"
        )

        # 构建消息列表（使用独立system prompt，不污染主对话历史）
        messages = [{"role": "system", "content": system_content}]

        # 安全截取最近对话，保证 tool_calls→tool 完整配对
        messages.extend(self._get_recent_exchange())

        # 追加反思指令
        messages.append({"role": "user", "content": prompt})

        # 调用模型（带工具），模型会自主决定是否调用 skill_manage / add_memory 等工具
        response = self._call_llm_with_tools(messages)

        if "error" in response:
            print(f"   ⚠️ [{context}] 反思调用失败: {response['error']}")
            return

        message = response["message"]
        finish_reason = response["finish_reason"]

        # 如果模型决定调用工具，执行工具调用
        if finish_reason == "tool_calls" and "tool_calls" in message:
            tool_results = self._execute_tool_calls(message["tool_calls"])
            for tr in tool_results:
                status = "✅" if tr["result"].get("success", True) else "❌"
                action = tr["result"].get("action", "")
                msg = tr["result"].get("message", tr["result"].get("error", ""))
                print(f"   {status} [{context}] {tr.get('tool_name', '')} {action}: {msg}")
        else:
            content = message.get("content", "")
            if content and "没有需要记录" not in content:
                print(f"   📝 [{context}] 反思结果: {content[:200]}...")

    def _trigger_skill_generation_from_trajectory(self, traj: TaskTrajectory):
        """
        基于完整轨迹触发技能生成（成功型反思）

        Hermes的"成功→提炼→复用"路径：
        当任务成功完成且满足技能生成条件时，构建反思提示词，
        让LLM自主将成功经验固化为可复用技能（调用 skill_manage create）。
        """
        # 构建反思提示
        reflection_prompt = build_reflection_prompt(traj)

        print("\n🧠 [学习循环] 检测到值得沉淀的经验，正在生成技能...")

        # 调用LLM进行技能生成
        self._call_llm_for_reflection(reflection_prompt, context="skill_creation")

        # 重置冷却计数器
        self.skills_since_last_check = 0

    def _trigger_failure_learning(self, traj: TaskTrajectory):
        """
        任务失败时触发学习（失败型反思）

        Hermes的"失败→反思→记录教训"路径：
        任务失败不是结束，而是学习的机会。从失败中提炼教训，
        存入记忆或生成修复技能，让Agent从错误中变得更聪明。

        参数:
            traj: 失败的任务轨迹
        """
        # 构建失败反思提示词
        failure_prompt = build_failure_reflection_prompt(traj)

        print("\n📖 [学习循环] 从失败中学习，记录教训...")

        # 调用LLM进行失败反思
        self._call_llm_for_reflection(failure_prompt, context="failure_learning")

        # 重置冷却计数器
        self.skills_since_last_check = 0

    def _nudge_reflection(self):
        """
        Nudge反思：周期性回顾近期工作，提炼值得长期保存的信息

        Hermes的"定时回顾"机制：
        维护nudge_counter计数器，每nudge_interval轮对话自动触发一次。
        回顾近期轨迹、当前记忆和技能，让LLM自主判断是否有值得记录的信息。

        与 _trigger_reflection 的区别：
        - _trigger_reflection：基于对话历史的简单回顾（旧版）
        - _nudge_reflection：基于轨迹数据的结构化回顾（第09讲新版）
        """
        # 获取最近完成的轨迹
        recent_traj = trajectory.get_recent_trajectories(5)

        # 获取当前记忆和技能上下文
        memory_context = self.memory_store.get_memory_context()
        skills_metadata = self.skill_store.get_skills_for_matching()
        skills_list = "\n".join([
            f"- {s['display_name']} (`{s['name']}`): {s['description'][:80]}"
            for s in skills_metadata[:10]
        ])

        # 构建Nudge反思提示词
        nudge_prompt = build_nudge_reflection_prompt(
            recent_trajectories=recent_traj,
            current_memory_context=memory_context or "暂无记忆",
            current_skills_list=skills_list or "暂无技能"
        )

        print(f"\n⏰ [Nudge: 第{self.nudge_counter}轮] 正在回顾近期对话，提炼值得长期保存的信息...")
        print("🤖 Hermes 正在反思中...")

        # 调用LLM进行反思
        self._call_llm_for_reflection(nudge_prompt, context="nudge")

    # ================== 命令处理 ==================

    def _handle_command(self, command: str):
        cmd = command.lower().strip()
        if cmd in ["/quit", "/exit"]:
            print("👋 再见！")
            exit(0)
        elif cmd == "/clear":
            self.clear_history()
            print(f"📊 当前历史消息数量: {self.get_history_length()}")
        elif cmd == "/history":
            self._show_history()
        elif cmd == "/tools":
            self._show_tools()
        elif cmd == "/memory":
            self._show_memory()
        elif cmd == "/skills":
            self._show_skills()
        elif cmd.startswith("/skills "):
            sub = command[7:].strip()
            self._show_skills(sub_command=sub)
        elif cmd == "/nudge":
            self._nudge_reflection()
        elif cmd == "/sessions":
            self._show_session_stats()
        else:
            print(f"❌ 未知命令: {command}")
            print("   可用命令: /clear, /history, /tools, /memory, /skills, /skills status, /nudge, /sessions, /quit")
    
    def _show_history(self):
        print("\n" + "=" * 40)
        print("📜 对话历史")
        print("=" * 40)
        for i, msg in enumerate(self.conversation_history):
            role = msg["role"]
            content = msg.get("content", "")
            if len(content) > 100:
                content = content[:100] + "..."
            if role == "system":
                print(f"[{i}] 🔧 SYSTEM: {content}")
            elif role == "user":
                print(f"[{i}] 👤 USER: {content}")
            elif role == "assistant":
                print(f"[{i}] 🤖 ASSISTANT: {content}")
            elif role == "tool":
                print(f"[{i}] 🛠️ TOOL: {content[:80]}...")
        print("=" * 40)
        print(f"📊 总计 {len(self.conversation_history)} 条消息")
        print(f"📝 Token估算: {self._estimate_tokens(self.conversation_history)}")
    
    def _show_tools(self):
        print(f"\n📦 可用工具 ({len(tool_registry.list_tools())} 个):")
        for tool_name in tool_registry.list_tools():
            handler = tool_registry.get_handler(tool_name)
            schemas = tool_registry.get_schemas()
            desc = ""
            for s in schemas:
                if s["function"]["name"] == tool_name:
                    desc = s["function"].get("description", "")
                    break
            print(f"   🔧 {tool_name}: {desc[:80]}...")

    def _show_memory(self):
        """显示当前持久记忆"""
        print("\n" + "=" * 50)
        memory_context = self.memory_store.get_memory_context()
        if memory_context:
            print("🧠 当前持久记忆:")
            print(memory_context)
        else:
            print("🧠 暂无持久记忆")
        print("=" * 50)

    def _show_skills(self, sub_command: str = ""):
        """
        显示技能库，支持查看健康状态

        用法:
            /skills        - 查看技能列表
            /skills status - 查看技能运行状况报告
        """
        if sub_command == "status":
            self._show_skills_health()
            return

        print("\n" + "=" * 50)
        stats = self.skill_store.get_stats()
        print(f"📚 技能库 ({stats['total_skills']} 个技能):")
        print(f"   存储路径: {stats['skills_root']}")

        # 获取过时技能列表
        outdated = self.skill_store.get_outdated_skills()
        outdated_names = {s["name"] for s in outdated}

        if stats["skills"]:
            for s in stats["skills"]:
                health = self.skill_store.get_skill_health(s["name"])
                status_icon = self._health_icon(health["health_status"])
                outdated_mark = " ⚠️过时" if s["name"] in outdated_names else ""
                print(f"   {status_icon} {s['display_name']} (v{s['version']}){outdated_mark}")
                print(f"      健康评分: {health.get('health_score', 50)}分 | 使用: {health.get('usage_count', 0)}次 | 成功率: {health.get('success_rate', 0.0)}")
                print(f"      {s['description'][:100]}")
        else:
            print("   📭 暂无技能。完成复杂任务后会自动创建。")
        print("=" * 50)
        print("💡 使用 /skills status 查看详细健康报告")

    def _show_skills_health(self):
        """显示技能运行状况报告"""
        print("\n" + "=" * 50)
        print("📊 技能运行状况报告")
        print("=" * 50)

        stats = self.skill_store.get_stats()

        if stats["total_skills"] == 0:
            print("📭 暂无技能。")
            return

        for s in stats["skills"]:
            health = self.skill_store.get_skill_health(s["name"])
            status_icon = self._health_icon(health["health_status"])

            print(f"\n{status_icon} {s['display_name']} (v{s['version']})")
            print(f"   健康状态: {self._health_label(health.get('health_status', 'unknown'))} ({health.get('health_score', 0)}分)")
            print(f"   使用次数: {health.get('usage_count', 0)}次")
            print(f"   成功率: {health.get('success_rate', 0.0)}")
            print(f"   消息: {health.get('message', '未知')}")

        print("\n" + "=" * 50)

    def _health_icon(self, status: str) -> str:
        """返回健康状态图标"""
        icons = {
            "healthy": "🟢",
            "needs_review": "🟡",
            "needs_patch": "🔴",
            "deprecated": "⚫",
            "unused": "⚪"
        }
        return icons.get(status, "❓")

    def _health_label(self, status: str) -> str:
        """返回健康状态标签"""
        labels = {
            "healthy": "healthy (良好)",
            "needs_review": "needs_review (需要审查)",
            "needs_patch": "needs_patch (需要修复)",
            "deprecated": "deprecated (已废弃)",
            "unused": "unused (未使用)"
        }
        return labels.get(status, status)

    def _show_session_stats(self):
        """显示会话数据库统计"""
        print("\n" + "=" * 50)
        stats = self.session_store.get_stats()
        print(f"📊 会话数据库统计:")
        print(f"   总对话轮次: {stats['total_exchanges']}")
        print(f"   总会话数:   {stats['total_sessions']}")
        print(f"   当前会话ID: {self.session_id}")
        print(f"   当前轮次:   {self.turn_counter}")
        print("=" * 50)


def main():
    """启动 Agent，所有数据目录均放在脚本所在目录下"""
    from memory_store import MemoryStore
    from skill_store import SkillStore

    # 所有数据目录均指向脚本所在目录
    memories_dir = os.path.join(SCRIPT_DIR, "memories")
    data_dir = os.path.join(SCRIPT_DIR, "data")
    skills_dir = os.path.join(SCRIPT_DIR, "skills")

    agent_memory_store = MemoryStore(
        memory_path=os.path.join(memories_dir, "MEMORY.json"),
        user_path=os.path.join(memories_dir, "USER.json"),
    )
    agent_skill_store = SkillStore(skills_root=skills_dir)
    agent_session_store = SessionStore(db_path=os.path.join(data_dir, "sessions.db"))

    agent = AIAgent(
        model=DEFAULT_MODEL,
        memory_store=agent_memory_store,
        skill_store=agent_skill_store,
        session_store=agent_session_store,
    )
    agent.run()


if __name__ == "__main__":
    main()