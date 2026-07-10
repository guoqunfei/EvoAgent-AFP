# trajectory.py
"""
任务执行轨迹跟踪模块
用于记录任务过程中的工具调用、错误、用户反馈等信息，
为反思和学习闭环提供数据支持
"""

import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class ToolCallRecord:
    """单次工具调用的记录"""
    name: str
    arguments: Dict[str, Any]
    result: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0
    success: bool = True


@dataclass
class ErrorRecord:
    """错误记录"""
    message: str
    occurred_at: float = field(default_factory=time.time)
    context: str = ""
    resolved: bool = False
    resolution_notes: str = ""


@dataclass
class TaskTrajectory:
    """
    任务执行轨迹
    
    记录一次完整任务执行的所有相关信息，
    用于后续的反思和技能生成
    """
    # 任务信息
    task_description: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # 执行记录
    tool_calls: List[ToolCallRecord] = field(default_factory=list)
    errors: List[ErrorRecord] = field(default_factory=list)
    user_corrections: List[str] = field(default_factory=list)
    
    # 结果评估
    overall_success: bool = False
    success_reasoning: str = ""  # 成功的原因分析
    failure_reasoning: str = ""  # 失败的原因分析
    
    # 可能生成的技能信息
    skill_suggestion: Optional[Dict[str, Any]] = None
    
    def add_tool_call(self, name: str, arguments: Dict, result: Dict, duration_ms: float, success: bool = True):
        """添加工具调用记录"""
        self.tool_calls.append(ToolCallRecord(
            name=name, arguments=arguments, result=result,
            timestamp=time.time(), duration_ms=duration_ms, success=success
        ))
    
    def add_error(self, message: str, context: str = ""):
        """添加错误记录"""
        self.errors.append(ErrorRecord(message=message, context=context))
    
    def add_user_correction(self, correction: str):
        """添加用户纠正"""
        self.user_corrections.append(correction)
    
    def mark_error_resolved(self, error_index: int, resolution_notes: str = ""):
        """标记错误已解决"""
        if 0 <= error_index < len(self.errors):
            self.errors[error_index].resolved = True
            self.errors[error_index].resolution_notes = resolution_notes
    
    def mark_success(self, reasoning: str = ""):
        """标记任务成功"""
        self.overall_success = True
        self.success_reasoning = reasoning
    
    def mark_failure(self, reasoning: str = ""):
        """标记任务失败"""
        self.overall_success = False
        self.failure_reasoning = reasoning
        self.end_time = time.time()
    
    def finish(self):
        """结束轨迹记录"""
        self.end_time = time.time()
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "task_description": self.task_description,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            "duration_seconds": self.end_time - self.start_time if self.end_time else None,
            "tool_calls_count": len(self.tool_calls),
            "error_count": len(self.errors),
            "user_corrections_count": len(self.user_corrections),
            "overall_success": self.overall_success,
            "success_reasoning": self.success_reasoning,
            "failure_reasoning": self.failure_reasoning,
            "tool_calls": [asdict(tc) for tc in self.tool_calls],
            "errors": [{"message": e.message, "resolved": e.resolved} for e in self.errors],
            "user_corrections": self.user_corrections
        }
    
    def should_create_skill(self) -> bool:
        """
        判断当前任务是否值得生成技能
        
        触发条件（与Hermes源码中的SKILLS_GUIDANCE一致）：
        1. 复杂任务：工具调用次数 >= 5
        2. 错误恢复：发生过错误且最终被解决
        3. 用户纠正：用户提供了修正指导
        """
        conditions = []
        
        if len(self.tool_calls) >= 5:
            conditions.append("complex_task")
        
        # 检查是否有错误被解决
        has_resolved_error = any(e.resolved for e in self.errors)
        if has_resolved_error:
            conditions.append("error_recovery")
        
        if self.user_corrections:
            conditions.append("user_correction")
        
        should_create = len(conditions) >= 1
        
        # 只有成功完成的任务才应该生成技能
        should_create = should_create and self.overall_success
        
        return should_create


class TrajectoryTracker:
    """
    轨迹跟踪管理器（单例模式）
    管理当前活跃的任务轨迹
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._current_trajectory = None
            cls._instance._trajectory_history = []
        return cls._instance
    
    def start_trajectory(self, task_description: str) -> TaskTrajectory:
        """开始新的任务轨迹"""
        self._current_trajectory = TaskTrajectory(task_description=task_description)
        return self._current_trajectory
    
    def get_current_trajectory(self) -> Optional[TaskTrajectory]:
        """获取当前轨迹"""
        return self._current_trajectory
    
    def finish_trajectory(self) -> Optional[TaskTrajectory]:
        """完成当前轨迹并保存到历史"""
        if self._current_trajectory:
            self._current_trajectory.finish()
            self._trajectory_history.append(self._current_trajectory.to_dict())
            completed = self._current_trajectory
            self._current_trajectory = None
            return completed
        return None
    
    def get_recent_trajectories(self, limit: int = 10) -> List[Dict]:
        """获取最近完成的轨迹"""
        return self._trajectory_history[-limit:]


# 全局单例
trajectory = TrajectoryTracker()