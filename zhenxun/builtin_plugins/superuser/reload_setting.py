'''
Author: xx
Date: 2025-03-22 14:42:41
LastEditors: Do not edit
LastEditTime: 2025-03-24 04:45:54
Description: 
FilePath: \zhenxun\zhenxun_bot\zhenxun\builtin_plugins\superuser\reload_setting.py
'''
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.rule import to_me
from nonebot_plugin_alconna import Alconna, Arparma, on_alconna
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_session import EventSession

from zhenxun.configs.config import Config
from zhenxun.configs.utils import PluginExtraData, RegisterConfig
from zhenxun.services.log import logger
from zhenxun.utils.enum import PluginType
from zhenxun.utils.message import MessageUtils

import asyncio

__plugin_meta__ = PluginMetadata(
    name="重载配置",
    description="重新加载config.yaml",
    usage="""
    重载配置
    """.strip(),
    extra=PluginExtraData(
        author="HibiKier",
        version="0.1",
        plugin_type=PluginType.SUPERUSER,
        configs=[
            RegisterConfig(
                key="AUTO_RELOAD",
                value=False,
                help="自动重载配置文件",
                default_value=False,
                type=bool,
            ),
            RegisterConfig(
                key="AUTO_RELOAD_TIME",
                value=180,
                help="自动重载配置文件时长",
                default_value=180,
                type=int,
            ),
        ],
    ).to_dict(),
)

_matcher = on_alconna(
    Alconna(
        "重载配置",
    ),
    rule=to_me(),
    permission=SUPERUSER,
    priority=1,
    block=True,
)

# 添加信号量控制
_reload_semaphore = asyncio.Semaphore(5)

@_matcher.handle()
async def _(session: EventSession, arparma: Arparma):
    Config.reload()
    logger.debug("自动重载配置文件", arparma.header_result, session=session)
    await MessageUtils.build_message("重载完成!").send(reply_to=True)


@scheduler.scheduled_job(
    "interval",
    seconds=Config.get_config("reload_setting", "AUTO_RELOAD_TIME", 180),
)
async def auto_reload_config_task():
    try:
        async with _reload_semaphore:
            if Config.get_config("reload_setting", "AUTO_RELOAD"):
                await asyncio.wait_for(
                    asyncio.sleep(0),  # 添加检查点
                    timeout=30
                )
                Config.reload()
                logger.debug("已自动重载配置文件...")
    except asyncio.TimeoutError:
        logger.error("重载配置文件超时...")
    except Exception as e:
        logger.error("重载配置文件失败", e=e)
