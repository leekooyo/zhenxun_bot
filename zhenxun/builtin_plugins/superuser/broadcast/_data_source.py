import asyncio

from nonebot.adapters import Bot
import nonebot_plugin_alconna as alc
from nonebot_plugin_alconna import Image, UniMsg
from nonebot_plugin_session import EventSession

from zhenxun.services.log import logger
from zhenxun.utils.common_utils import CommonUtils
from zhenxun.utils.message import MessageUtils
from zhenxun.utils.platform import PlatformUtils


class BroadcastManage:
    # 类变量定义发送间隔
    BROADCAST_INTERVAL = 10  # 秒
    
    @classmethod
    async def _build_message_list(cls, message: UniMsg) -> list:
        """构建消息列表
        
        参数:
            message: UniMsg 消息内容
            
        返回:
            list: 处理后的消息列表
        """
        message_list = []
        for msg in message:
            if isinstance(msg, alc.Image) and msg.url:
                message_list.append(Image(url=msg.url))
            elif isinstance(msg, alc.Text):
                message_list.append(msg.text)
        return message_list

    @classmethod
    async def _send_to_single_group(
        cls, 
        bot: Bot, 
        message_list: list,
        group: any,
        session: EventSession
    ) -> bool:
        """向单个群组发送消息
        
        参数:
            bot: Bot实例
            message_list: 消息列表
            group: 群组信息
            session: 会话信息
            
        返回:
            bool: 发送是否成功
        """
        try:
            if await CommonUtils.task_is_block(
                bot, "broadcast", group.group_id
            ):
                logger.info(
                    "群组已屏蔽广播",
                    "广播",
                    session=session,
                    target=f"{group.group_id}:{group.channel_id}",
                )
                return False

            target = PlatformUtils.get_target(
                group_id=group.group_id, 
                channel_id=group.channel_id
            )
            if not target:
                logger.warning("target为空", "广播", session=session)
                return False

            await MessageUtils.build_message(message_list).send(target, bot)
            logger.debug(
                "发送成功",
                "广播",
                session=session,
                target=f"{group.group_id}:{group.channel_id}",
            )
            # 将等待时间移到send方法中，使逻辑更清晰
            return True

        except Exception as e:
            logger.error(
                "发送失败",
                "广播",
                session=session,
                target=f"{group.group_id}:{group.channel_id}",
                e=e,
            )
            return False

    @classmethod
    async def send(
        cls, bot: Bot, message: UniMsg, session: EventSession
    ) -> tuple[int, int]:
        """发送广播消息

        参数:
            bot: Bot实例
            message: 消息内容
            session: 会话信息

        返回:
            tuple[int, int]: (发送成功的群组数量, 发送失败的群组数量)
        """
        message_list = await cls._build_message_list(message)
        group_list, _ = await PlatformUtils.get_group_list(bot)
        
        if not group_list:
            logger.info("没有可用的群组", "广播", session=session)
            return 0, 0
            
        success_count = 0
        total = len(group_list)
        
        for index, group in enumerate(group_list, 1):
            if await cls._send_to_single_group(bot, message_list, group, session):
                success_count += 1
            
            # 不是最后一个群组时才需要等待
            if index < total:
                logger.debug(
                    f"等待 {cls.BROADCAST_INTERVAL} 秒后继续发送",
                    "广播",
                    session=session
                )
                await asyncio.sleep(cls.BROADCAST_INTERVAL)
                
        logger.info(
            f"广播完成: 成功 {success_count} 个群组, 失败 {total - success_count} 个群组",
            "广播",
            session=session
        )
        return success_count, total - success_count
