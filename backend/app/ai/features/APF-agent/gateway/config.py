# gateway/config.py
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class GatewayConfig:
    """Gateway总体配置（平台无关）

    通过 ~/.hermes/gateway.yaml 统一管理所有平台配置。
    各消息平台的配置由各自的 Adapter 自行定义和加载，
    Gateway 层只负责通用运行时参数。
    """
    data_root: str = "./data"              # 数据根目录
    users_dir: str = "users"               # 用户数据子目录

    # 运行时配置
    max_concurrent_tasks: int = 10         # 最大并发处理数
    message_timeout: int = 60              # 消息处理超时（秒）

    # 平台开关（各 Adapter 自行扩展各自的配置段）
    # 例如接入 Slack 时只需在 gateway.yaml 中添加 slack 段，
    # 然后实现 SlackAdapter 读取对应配置即可


def load_gateway_config(config_path: str = None) -> GatewayConfig:
    """加载Gateway配置（平台无关）

    只负责加载 Gateway 通用配置（data_root、运行时参数等）。
    各平台的配置（token、白名单等）由对应的 Adapter 自行解析。
    """
    if config_path is None:
        config_path = Path.home() / ".hermes" / "gateway.yaml"

    config = GatewayConfig()

    if not Path(config_path).exists():
        # 返回默认配置
        return config

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        gateway_data = data.get("gateway", {})

        if "data_root" in gateway_data:
            config.data_root = gateway_data["data_root"]
        if "users_dir" in gateway_data:
            config.users_dir = gateway_data["users_dir"]
        if "max_concurrent_tasks" in gateway_data:
            config.max_concurrent_tasks = gateway_data["max_concurrent_tasks"]
        if "message_timeout" in gateway_data:
            config.message_timeout = gateway_data["message_timeout"]

    except Exception as e:
        print(f"⚠️ 加载配置失败: {e}")

    return config


def create_default_config():
    """创建默认配置文件（供初次使用）

    生成平台无关的 gateway.yaml 模板。
    后续接入具体平台（Slack / Discord / 飞书 / 微信 等）时，
    手动添加对应平台的配置段即可。
    """
    config_dir = Path.home() / ".hermes"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / "gateway.yaml"

    if config_path.exists():
        return str(config_path)

    default_config = {
        "gateway": {
            "data_root": "./data",
            "users_dir": "users",
            "max_concurrent_tasks": 10,
            "message_timeout": 60
        }
        # 接入新平台时在此添加对应的配置段，例如：
        # "slack": {
        #     "enabled": true,
        #     "bot_token": "xoxb-...",
        #     "app_token": "xapp-..."
        # },
        # "discord": {
        #     "enabled": true,
        #     "token": "..."
        # }
    }

    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(default_config, f, allow_unicode=True, indent=2)

    print(f"✅ 已创建配置文件: {config_path}")
    print("💡 接入具体消息平台时，在配置文件中添加对应平台的配置段即可")

    return str(config_path)
