import nonebot
from nonebot import on_notice
from nonebot.adapters import Bot
from nonebot.adapters.onebot.v11 import GroupIncreaseNoticeEvent
from nonebot.plugin import PluginMetadata
from nonebot_plugin_alconna import Alconna, Arparma, on_alconna
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_session import EventSession
import asyncio

from zhenxun.configs.config import BotConfig
from zhenxun.configs.utils import PluginExtraData
from zhenxun.services.log import logger
from zhenxun.utils.enum import PluginType
from zhenxun.utils.message import MessageUtils
from zhenxun.utils.platform import PlatformUtils
from zhenxun.utils.rules import admin_check, ensure_group, notice_rule

from ._data_source import MemberUpdateManage

__plugin_meta__ = PluginMetadata(
    name="更新群组成员列表",
    description="更新群组成员列表",
    usage="""
    更新群组成员的基本信息
    指令：
        更新群组成员信息
    """.strip(),
    extra=PluginExtraData(
        author="HibiKier",
        version="0.1",
        plugin_type=PluginType.SUPER_AND_ADMIN,
        admin_level=1,
    ).to_dict(),
)


_matcher = on_alconna(
    Alconna("更新群组成员信息"),
    rule=admin_check(1) & ensure_group,
    priority=5,
    block=True,
)


_notice = on_notice(priority=1, block=False, rule=notice_rule(GroupIncreaseNoticeEvent))


@_matcher.handle()
async def _(bot: Bot, session: EventSession, arparma: Arparma):
    if gid := session.id3 or session.id2:
        logger.info("更新群组成员信息", arparma.header_result, session=session)
        result = await MemberUpdateManage.update_group_member(bot, gid)
        await MessageUtils.build_message(result).finish(reply_to=True)
    await MessageUtils.build_message("群组id为空...").send()


@_notice.handle()
async def _(bot: Bot, event: GroupIncreaseNoticeEvent):
    if str(event.user_id) == bot.self_id:
        await MemberUpdateManage.update_group_member(bot, str(event.group_id))
        logger.info(
            f"{BotConfig.self_nickname}加入群聊更新群组信息",
            "更新群组成员列表",
            session=event.user_id,
            group_id=event.group_id,
        )


# 添加常量定义和信号量
TIMEOUT_SECONDS = 30
MAX_CONCURRENT_UPDATES = 5
update_semaphore = asyncio.Semaphore(MAX_CONCURRENT_UPDATES)

async def update_group_member_with_limit(bot: Bot, group_id: str) -> bool:
    """
    更新群组成员信息的异步函数，带有超时和并发限制
    
    Args:
        bot (Bot): 机器人实例
        group_id (str): 群组ID
        
    Returns:
        bool: 更新是否成功
    """
    try:
        async with update_semaphore:
            async with asyncio.timeout(TIMEOUT_SECONDS):
                await MemberUpdateManage.update_group_member(bot, group_id)
                logger.debug(f"群组 {group_id} 成员信息更新成功")
                return True
    except asyncio.TimeoutError:
        logger.warning(f"群组 {group_id} 成员信息更新超时")
        return False
    except Exception as e:
        logger.error(f"群组 {group_id} 成员信息更新失败", e=e)
        return False

@scheduler.scheduled_job(
    "interval",
    minutes=5,
)
async def _():
    for bot in nonebot.get_bots().values():
        if PlatformUtils.get_platform(bot) == "qq":
            try:
                group_list, _ = await PlatformUtils.get_group_list(bot)
                if group_list:
                    for group in group_list:
                        retries = 0
                        while retries < MAX_CONCURRENT_UPDATES:
                            try:
                                # 添加超时控制
                                async with asyncio.timeout(TIMEOUT_SECONDS):
                                    await MemberUpdateManage.update_group_member(
                                        bot, group.group_id
                                    )
                                    logger.debug("自动更新群组成员信息成功...")
                                break  # 成功后跳出重试循环
                            except asyncio.TimeoutError:
                                retries += 1
                                logger.warning(
                                    f"Bot: {bot.self_id} 更新群组成员信息超时 "
                                    f"(重试 {retries}/{MAX_CONCURRENT_UPDATES})",
                                    target=group.group_id,
                                )
                                if retries >= MAX_CONCURRENT_UPDATES:
                                    logger.error(
                                        f"Bot: {bot.self_id} 更新群组成员信息失败，"
                                        f"已达到最大重试次数",
                                        target=group.group_id,
                                    )
                            except Exception as e:
                                logger.error(
                                    f"Bot: {bot.self_id} 自动更新群组成员信息失败",
                                    target=group.group_id,
                                    e=e,
                                )
                                break  # 其他异常直接跳出重试循环
            except Exception as e:
                logger.error(f"Bot: {bot.self_id} 自动更新群组信息", e=e)
        logger.debug(f"自动 Bot: {bot.self_id} 更新群组成员信息成功...")
