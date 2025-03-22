from datetime import datetime, timedelta
from asyncio import Semaphore, TimeoutError, wait_for
import asyncio

import nonebot
from nonebot_plugin_apscheduler import scheduler
import pytz

from zhenxun.configs.config import Config
from zhenxun.models.chat_history import ChatHistory
from zhenxun.models.group_console import GroupConsole
from zhenxun.models.task_info import TaskInfo
from zhenxun.services.log import logger
from zhenxun.utils.platform import PlatformUtils

Config.add_plugin_config(
    "chat_check",
    "STATUS",
    True,
    help="是否开启群组两日内未发送任何消息，关闭该群全部被动",
    default_value=True,
    type=bool,
)

# 创建信号量，限制最大并发数为5
CHECK_SEMAPHORE = Semaphore(5)

@scheduler.scheduled_job(
    "cron",
    hour=4,
    minute=40,
)
async def _():
    if not Config.get_config("chat_history", "FLAG"):
        logger.debug("未开启历史发言记录，过滤群组发言检测...")
        return
    if not Config.get_config("chat_check", "STATUS"):
        logger.debug("未开启群组聊天时间检查，过滤群组发言检测...")
        return
    """检测群组发言时间并禁用全部被动"""
    update_list = []
    if modules := await TaskInfo.annotate().values_list("module", flat=True):
        for bot in nonebot.get_bots().values():
            group_list, _ = await PlatformUtils.get_group_list(bot, True)
            for group in group_list:
                try:
                    if await check_group_chat_activity(group, modules):
                        update_list.append(group)
                except Exception:
                    logger.error(
                        "检测群组发言时间失败...", "Chat检测", target=group.group_id
                    )
    if update_list:
        await GroupConsole.bulk_update(update_list, ["block_task"], 10)

async def check_group_chat_activity(group, modules) -> bool:
    """
    检查群组聊天活跃度的异步函数
    
    Args:
        group: 群组对象
        modules: 模块列表
    
    Returns:
        bool: 检查是否成功
    """
    try:
        async with CHECK_SEMAPHORE:  # 使用信号量控制并发
            # 使用 wait_for 添加超时控制
            return await wait_for(
                _process_single_group(group, modules),
                timeout=30.0  # 30秒超时
            )
    except TimeoutError:
        logger.error(
            "检查群组聊天活跃度超时", 
            "Chat检测", 
            target=group.group_id
        )
        return False
    except Exception as e:
        logger.error(
            f"检查群组聊天活跃度失败: {str(e)}", 
            "Chat检测", 
            target=group.group_id
        )
        return False

async def _process_single_group(group, modules) -> bool:
    """
    处理单个群组的具体逻辑
    """
    last_message = (
        await ChatHistory.filter(group_id=group.group_id)
        .annotate()
        .order_by("-create_time")
        .first()
    )
    if last_message:
        now = datetime.now(pytz.timezone("Asia/Shanghai"))
        if now - timedelta(days=2) > last_message.create_time:
            _group, _ = await GroupConsole.get_or_create(
                group_id=group.group_id, 
                channel_id__isnull=True
            )
            modules = [f"<{module}" for module in modules]
            _group.block_task = ",".join(modules) + ","
            return True
    return False
