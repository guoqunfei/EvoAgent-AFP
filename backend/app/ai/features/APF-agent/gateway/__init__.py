# gateway/__init__.py
"""
Hermes Gateway 模块

提供多用户会话管理和消息平台接入能力。

核心组件：
- GatewayConfig: 平台无关的 Gateway 配置管理
- UserSession: 单用户隔离会话（独立 Agent 实例 + 记忆 + 技能）
- UserManager: 多用户会话生命周期管理

架构设计采用适配器模式：
- 每个消息平台实现 BasePlatformAdapter 接口即可接入
- 不依赖任何特定平台，Telegram/Slack/Discord/飞书 等均可适配
"""

from .config import GatewayConfig, load_gateway_config, create_default_config
from .user_manager import UserSession, UserManager, user_manager

__all__ = [
    "GatewayConfig",
    "load_gateway_config",
    "create_default_config",
    "UserSession",
    "UserManager",
    "user_manager",
]
