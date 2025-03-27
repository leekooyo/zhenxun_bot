"""
Author: xx
Date: 2025-03-22 14:42:41
LastEditors: Do not edit
LastEditTime: 2025-03-25 23:21:12
Description:
FilePath: \zhenxun\zhenxun_bot\zhenxun\builtin_plugins\scheduler\morning.py
"""

from dataclasses import dataclass
from datetime import datetime
import asyncio
from pathlib import Path

import nonebot
from nonebot.adapters import Bot
from nonebot.plugin import PluginMetadata
from nonebot_plugin_apscheduler import scheduler

from zhenxun.configs.config import BotConfig
from zhenxun.configs.path_config import IMAGE_PATH
from zhenxun.configs.utils import PluginExtraData, Task
from zhenxun.models.group_console import GroupConsole
from zhenxun.services.log import logger
from zhenxun.utils.common_utils import CommonUtils
from zhenxun.utils.enum import PluginType
from zhenxun.utils.message import MessageUtils
from zhenxun.utils.platform import PlatformUtils

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


@dataclass
class SendResult:
    """发送结果"""

    success: bool
    message: str


class GroupManager:
    """群组管理类"""

    @staticmethod
    async def get_platform_groups(platform: str) -> list[str]:
        """获取指定平台的有效群组"""
        return await GroupConsole.filter(
            status=True, channel_id__isnull=True, platform=platform
        ).values_list("group_id", flat=True)


class MessageSender:
    """消息发送器"""

    def __init__(self, interval: int = 60):
        self.interval = interval
        self._semaphore = asyncio.Semaphore(5)
        self.BROADCAST_INTERVAL = 10  # 广播消息发送间隔（秒）

    async def check_group(self, bot: Bot, group_id: str) -> bool:
        """检查群组是否可发送"""
        return not await CommonUtils.task_is_block(bot, "morning_goodnight", group_id)

    async def send_to_group(self, bot: Bot, group_id: str, message) -> SendResult:
        """发送消息到单个群组"""
        try:
            if not await self.check_group(bot, group_id):
                return SendResult(False, f"群 {group_id} 已禁用早晚安功能")

            await PlatformUtils.send_message(bot, None, group_id, message)
            return SendResult(True, f"向群 {group_id} 发送成功")
        except Exception as e:
            return SendResult(False, f"向群 {group_id} 发送失败: {e}")

    async def _send_to_platform(
        self, bot: Bot, groups: list, message: str, log_cmd: str
    ) -> bool:
        """向单个平台的群组发送消息

        参数:
            bot: Bot实例
            groups: 群组列表
            message: 要发送的消息
            log_cmd: 日志命令标识

        返回:
            bool: 是否全部发送成功
        """
        platform = PlatformUtils.get_platform(bot)
        if not groups:
            logger.info(f"{log_cmd}: 平台 {platform} 没有需要发送的群组")
            return True

        success = True
        total = len(groups)

        for index, group_id in enumerate(groups, 1):
            result = await self.send_to_group(bot, group_id, message)
            if result.success:
                logger.info(f"{log_cmd}: {result.message}")
            else:
                logger.error(f"{log_cmd}: {result.message}")
                success = False

            # 不是最后一个群组时才需要等待
            if index < total:
                logger.debug(f"{log_cmd}: 等待 {self.BROADCAST_INTERVAL} 秒后继续发送")
                await asyncio.sleep(self.BROADCAST_INTERVAL)

        return success

    async def broadcast(self, message: str, log_cmd: str) -> bool:
        """广播消息

        参数:
            message: 要广播的消息
            log_cmd: 日志命令标识

        返回:
            bool: 广播是否成功
        """
        async with self._semaphore:
            try:
                # 获取机器人列表
                bots = nonebot.get_bots()
                if not bots:
                    logger.error(f"{log_cmd}: 没有可用的Bot连接")
                    return False

                # 按平台发送
                all_success = True
                for bot in bots.values():
                    platform = PlatformUtils.get_platform(bot)
                    groups = await GroupManager.get_platform_groups(platform)

                    platform_success = await self._send_to_platform(
                        bot, groups, message, log_cmd
                    )
                    all_success = all_success and platform_success

                logger.info(f"{log_cmd}: 广播任务完成")
                return all_success

            except Exception as e:
                logger.error(f"{log_cmd}: 广播任务失败: {e}")
                return False


# 创建消息发送器实例
message_sender = MessageSender()


@scheduler.scheduled_job(
    "cron",
    hour=7,
    minute=0,
)
async def morning_greeting():
    """早安问候"""
    start_time = datetime.now()
    message = MessageUtils.build_message(["早上好", IMAGE_PATH / "zhenxun" / "zao.jpg"])

    success = await message_sender.broadcast(message, "早安问候")

    elapsed = (datetime.now() - start_time).total_seconds()
    if success:
        logger.info(f"早安问候任务完成，耗时: {elapsed:.2f}秒")
    else:
        logger.error(f"早安问候任务失败，耗时: {elapsed:.2f}秒")


@scheduler.scheduled_job(
    "cron",
    hour=0,
    minute=0,
)
async def night_greeting():
    """晚安问候"""
    start_time = datetime.now()
    message = MessageUtils.build_message(
        [
            f"{BotConfig.self_nickname}要睡觉了，你们也要早点睡呀",
            IMAGE_PATH / "zhenxun" / "sleep.jpg",
        ]
    )

    success = await message_sender.broadcast(message, "晚安问候")

    elapsed = (datetime.now() - start_time).total_seconds()
    if success:
        logger.info(f"晚安问候任务完成，耗时: {elapsed:.2f}秒")
    else:
        logger.error(f"晚安问候任务失败，耗时: {elapsed:.2f}秒")
