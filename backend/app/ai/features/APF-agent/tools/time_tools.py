# tools/time_tools.py
"""
时间相关工具集
包含：获取当前时间、日期格式化等
"""

from datetime import datetime
import pytz
from .registry import tool_registry


# ============================================================
# 工具1: get_current_time - 获取当前时间
# ============================================================

@tool_registry.tool(
    name="get_current_time",
    description="获取当前日期和时间。可以指定时区（如 Asia/Shanghai、America/New_York、Europe/London），默认返回本地时间和UTC时间。",
    timezone="string:时区名称，例如 'Asia/Shanghai'、'America/New_York'，可选参数，不提供则返回本地时间"
)
def get_current_time_handler(timezone: str = None) -> dict:
    """
    获取当前时间
    
    参数:
        timezone: 时区名称（如 'Asia/Shanghai'），可选
    
    返回:
        包含日期、时间、时区、时间戳的字典
    """
    result = {
        "success": True,
        "timestamp": int(datetime.now().timestamp()),
    }
    
    if timezone:
        try:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            result["timezone"] = timezone
            result["datetime"] = now.strftime("%Y-%m-%d %H:%M:%S")
            result["iso"] = now.isoformat()
        except Exception as e:
            return {
                "success": False,
                "error": f"无效的时区: {timezone}",
                "available_timezones_hint": "例如: Asia/Shanghai, America/New_York, Europe/London"
            }
    else:
        # 返回本地时间
        now = datetime.now()
        result["timezone"] = "local"
        result["datetime"] = now.strftime("%Y-%m-%d %H:%M:%S")
        result["iso"] = now.isoformat()
        
        # 同时提供UTC时间作为参考
        utc_now = datetime.now(pytz.UTC)
        result["utc_datetime"] = utc_now.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # 添加星期信息
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_en = weekdays[datetime.now().weekday()]
    weekday_cn = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][datetime.now().weekday()]
    result["weekday"] = {"en": weekday_en, "cn": weekday_cn}
    
    return result


# ============================================================
# 工具2: calculate_date - 日期计算
# ============================================================

@tool_registry.tool(
    name="calculate_date",
    description="计算日期偏移。给定一个起始日期和偏移量，计算目标日期。",
    start_date="string:起始日期，格式 YYYY-MM-DD，如 '2024-01-01'，可选，默认为今天",
    days="integer:偏移天数，正数为未来，负数为过去，可选",
    months="integer:偏移月数，可选",
    years="integer:偏移年数，可选"
)
def calculate_date_handler(
    start_date: str = None,
    days: int = 0,
    months: int = 0,
    years: int = 0
) -> dict:
    """
    计算日期偏移
    
    参数:
        start_date: 起始日期，格式 YYYY-MM-DD，不提供则使用今天
        days: 偏移天数
        months: 偏移月数
        years: 偏移年数
    """
    from dateutil.relativedelta import relativedelta
    
    try:
        if start_date:
            base = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            base = datetime.now()
        
        target = base + relativedelta(years=years, months=months, days=days)
        
        return {
            "success": True,
            "start_date": base.strftime("%Y-%m-%d"),
            "offset": {
                "days": days,
                "months": months,
                "years": years
            },
            "target_date": target.strftime("%Y-%m-%d"),
            "day_of_week": target.strftime("%A")
        }
    
    except ValueError as e:
        return {"success": False, "error": f"日期格式错误: {e}"}
    except Exception as e:
        return {"success": False, "error": f"计算失败: {e}"}


def register_all_tools():
    """注册所有时间工具（装饰器已自动注册，此函数仅用于兼容性）"""
    pass