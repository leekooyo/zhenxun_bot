'''
Author: xx
Date: 2025-03-22 14:42:41
LastEditors: Do not edit
LastEditTime: 2025-03-23 00:55:31
Description: 
FilePath: \zhenxun\zhenxun_bot\zhenxun\builtin_plugins\scheduler\morning.py
'''
import nonebot
from nonebot.adapters import Bot
from nonebot.plugin import PluginMetadata
from nonebot_plugin_apscheduler import scheduler
import asyncio
from asyncio import Semaphore
from functools import partial

from zhenxun.configs.config import BotConfig
from zhenxun.configs.path_config import IMAGE_PATH
from zhenxun.configs.utils import PluginExtraData, Task
from zhenxun.services.log import logger
from zhenxun.utils.common_utils import CommonUtils
from zhenxun.utils.enum import PluginType
from zhenxun.utils.message import MessageUtils
from zhenxun.utils.platform import broadcast_group

__plugin_meta__ = PluginMetadata(
    name="早晚安被动技能",
    description="早晚安被动技能",
    usage="",
    extra=PluginExtraData(
        author="HibiKier",
        version="0.1",
        plugin_type=PluginType.HIDDEN,
        tasks=[
            Task(
                module="morning_goodnight",
                name="早晚安",
                create_status=False,
                default_status=False,
            )
        ],
    ).to_dict(),
)

driver = nonebot.get_driver()

# 创建信号量
morning_semaphore = Semaphore(5)

async def check(bot: Bot, group_id: str) -> bool:
    return not await CommonUtils.task_is_block(bot, "morning_goodnight", group_id)


# 早上好
@scheduler.scheduled_job(
    "cron",
    hour=6,
    minute=1,
)
async def send_morning_greeting():
    try:
        async with morning_semaphore:
            message = MessageUtils.build_message(["早上好", IMAGE_PATH / "zhenxun" / "zao.jpg"])
            # 设置30秒超时
            await asyncio.wait_for(
                broadcast_group(message, log_cmd="被动早晚安", check_func=check),
                timeout=30
            )
            logger.info("每日早安发送...")
    except asyncio.TimeoutError:
        logger.error("早安消息发送超时...")
    except Exception as e:
        logger.error(f"早安消息发送错误: {str(e)}")


# # 睡觉了
@scheduler.scheduled_job(
    "cron",
    hour=23,
    minute=59,
)
async def send_night_greeting():
    try:
        async with morning_semaphore:
            message = MessageUtils.build_message(
                [
                    f"{BotConfig.self_nickname}要睡觉了，你们也要早点睡呀",
                    IMAGE_PATH / "zhenxun" / "sleep.jpg",
                ]
            )
            # 设置30秒超时
            await asyncio.wait_for(
                broadcast_group(message, log_cmd="被动早晚安", check_func=check),
                timeout=30
            )
            logger.info("每日晚安发送...")
    except asyncio.TimeoutError:
        logger.error("晚安消息发送超时...")
    except Exception as e:
        logger.error(f"晚安消息发送错误: {str(e)}")
