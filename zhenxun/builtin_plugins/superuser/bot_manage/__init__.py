from typing import cast
import asyncio

import nonebot
from nonebot.adapters import Bot
from nonebot.plugin import PluginMetadata
from tortoise.exceptions import DoesNotExist, IntegrityError, TransactionManagementError

from zhenxun.configs.utils import PluginExtraData
from zhenxun.models.bot_console import BotConsole
from zhenxun.models.plugin_info import PluginInfo
from zhenxun.models.task_info import TaskInfo
from zhenxun.services.log import logger
from zhenxun.utils.enum import PluginType
from zhenxun.utils.platform import PlatformUtils

driver = nonebot.get_driver()

__plugin_meta__ = PluginMetadata(
    name="Bot管理",
    description="指定bot对象的功能/被动开关和状态",
    usage="""
    指令:
        bot被动状态                 : bot的被动技能状态
        bot开启/关闭被动[被动名称]    : 被动技能开关
        bot开启/关闭所有被动          : 所有被动技能开关
        bot插件列表: bot插件列表状态  : bot插件列表
        bot开启/关闭所有插件          : 所有插件开关
        bot开启/关闭插件[插件名称]    : 插件开关
        bot休眠                    : bot休眠，屏蔽所有消息
        bot醒来                    : bot醒来
    """.strip(),
    extra=PluginExtraData(
        author="",
        version="0.1",
        plugin_type=PluginType.SUPERUSER,
    ).to_dict(),
)

from .bot_switch import *  # noqa: F403
from .plugin import *  # noqa: F403
from .task import *  # noqa: F403


@driver.on_bot_connect
async def init_bot_console(bot: Bot):
    """初始化Bot管理

    参数:
        bot: Bot
    """
    try:

        async def _retry_get_platform(bot: Bot, retries: int = 5) -> str:
            """重试获取平台信息

            参数:
                bot: Bot
                retries: 最大重试次数

            返回:
                str: 平台信息
            """
            for _ in range(retries):
                platform = PlatformUtils.get_platform(bot)
                if platform != "unknown":
                    return platform
                await asyncio.sleep(1)  # 等待一秒后重试
            return "unknown"  # 如果重试失败，返回"unknown"

        async def _retry_get_bot_data(bot: Bot, platform: str, retries: int = 5):
            """重试获取bot_data

            参数:
                bot: Bot
                platform: 平台信息
                retries: 最大重试次数

            返回:
                BotConsole或None
            """
            for _ in range(retries):
                bot_data = await BotConsole.get_or_none(
                    bot_id=str(bot.self_id), platform=platform
                )
                if bot_data is not None:
                    return bot_data
                await asyncio.sleep(1)  # 等待一秒后重试
            return None  # 如果重试失败，返回None

        async def _filter_blocked_items(
            items_list: list[str], block_list: list[str]
        ) -> list[str]:
            """过滤被block的项目

            参数:
                items_list: 需要过滤的项目列表
                block_list: block列表

            返回:
                list: 过滤后且经过格式化的项目列表
            """
            return [item for item in items_list if item not in block_list]

        plugin_list = [
            plugin.module
            for plugin in await PluginInfo.get_plugins(
                plugin_type__in=[
                    PluginType.NORMAL,
                    PluginType.DEPENDANT,
                    PluginType.ADMIN,
                ]
            )
        ]
        task_list = cast(
            list[str],
            await TaskInfo.filter(status=True).values_list("module", flat=True),
        )

        platform = await _retry_get_platform(bot)  # 使用重试获取平台信息

        # 先尝试获取已存在的记录
        # logger.info(f"获取已存在的记录 {bot.self_id} {platform}", "bot管理")
        bot_data = await _retry_get_bot_data(bot, platform)  # 使用重试获取bot_data
        # logger.info(f"获取已存在的记录 {bot_data}", "bot管理")
        if bot_data is not None:
            # 如果存在，过滤并更新记录
            task_list = await _filter_blocked_items(
                task_list, await bot_data.get_tasks(bot.self_id, False)
            )
            plugin_list = await _filter_blocked_items(
                plugin_list, await bot_data.get_plugins(bot.self_id, False)
            )
            bot_data.available_plugins = BotConsole.convert_module_format(plugin_list)
            bot_data.available_tasks = BotConsole.convert_module_format(task_list)
            await bot_data.save(update_fields=["available_plugins", "available_tasks"])
        else:
            # 如果不存在，创建新记录
            bot_data = await BotConsole.create(
                bot_id=bot.self_id,
                platform=platform,
                available_plugins=BotConsole.convert_module_format(plugin_list),
                available_tasks=BotConsole.convert_module_format(task_list),
            )

        logger.info("初始化Bot管理完成...")

    except Exception as e:
        logger.error(f"初始化Bot管理失败: {str(e)}")
        raise
