'''
Author: xx
Date: 2025-03-22 14:42:41
LastEditors: Do not edit
LastEditTime: 2025-03-23 00:53:28
Description: 
FilePath: \zhenxun\zhenxun_bot\zhenxun\builtin_plugins\scheduler\auto_update_group.py
'''
import asyncio
from asyncio import Semaphore
from functools import partial
import nonebot
from nonebot_plugin_apscheduler import scheduler

from zhenxun.services.log import logger
from zhenxun.utils.platform import PlatformUtils

# 创建信号量
update_semaphore = Semaphore(5)

# 自动更新群组信息
@scheduler.scheduled_job(
    "cron",
    hour=3,
    minute=1,
)
async def auto_update_group_info():
    bots = nonebot.get_bots()
    tasks = [update_group_with_timeout(bot) for bot in bots.values()]
    await asyncio.gather(*tasks)
    logger.info("自动更新群组成员信息成功...")

# 自动更新好友信息
@scheduler.scheduled_job(
    "cron",
    hour=3,
    minute=1,
)
async def auto_update_friend_info():
    bots = nonebot.get_bots()
    tasks = [update_friend_with_timeout(bot) for bot in bots.values()]
    await asyncio.gather(*tasks)
    logger.info("自动更新好友信息成功...")

async def update_group_with_timeout(bot):
    try:
        async with update_semaphore:
            # 使用asyncio.wait_for添加超时控制
            await asyncio.wait_for(PlatformUtils.update_group(bot), timeout=30.0)
    except asyncio.TimeoutError:
        logger.error(f"Bot: {bot.self_id} 更新群组信息超时", "自动更新群组")
    except Exception as e:
        logger.error(f"Bot: {bot.self_id} 自动更新群组信息", "自动更新群组", e=e)

async def update_friend_with_timeout(bot):
    try:
        async with update_semaphore:
            # 使用asyncio.wait_for添加超时控制
            await asyncio.wait_for(PlatformUtils.update_friend(bot), timeout=30.0)
    except asyncio.TimeoutError:
        logger.error(f"Bot: {bot.self_id} 更新好友信息超时", "自动更新好友")
    except Exception as e:
        logger.error(f"Bot: {bot.self_id} 自动更新好友信息错误", "自动更新好友", e=e)
