import os
import sys
from pathlib import Path
import platform
from typing import Optional, Tuple

import aiofiles
import nonebot
from nonebot import on_command
from nonebot.adapters import Bot
from nonebot.params import ArgStr
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.rule import to_me
from nonebot_plugin_uninfo import Uninfo

from zhenxun.configs.config import BotConfig
from zhenxun.configs.utils import PluginExtraData
from zhenxun.services.log import logger
from zhenxun.utils.enum import PluginType
from zhenxun.utils.message import MessageUtils
from zhenxun.utils.platform import PlatformUtils

__plugin_meta__ = PluginMetadata(
    name="重启",
    description="执行脚本重启真寻",
    usage="重启",
    extra=PluginExtraData(
        author="HibiKier", version="0.1", plugin_type=PluginType.SUPERUSER
    ).to_dict(),
)

class RestartManager:
    def __init__(self):
        self.restart_mark = Path() / "is_restart"
        self.restart_file = Path() / "restart.sh"
        self.is_windows = str(platform.system()).lower() == "windows"

    async def create_restart_script(self, port: int) -> None:
        """创建重启脚本"""
        if self.is_windows or self.restart_file.exists():
            return

        script_content = (
            f"pid=$(netstat -tunlp | grep {port} | awk '{{print $7}}')\n"
            "pid=${pid%/*}\n"
            "kill -9 $pid\n"
            "sleep 3\n"
            "python3 bot.py"
        )
        
        async with aiofiles.open(self.restart_file, "w", encoding="utf8") as f:
            await f.write(script_content)
        os.system("chmod +x ./restart.sh")  # noqa: ASYNC221
        logger.info("已自动生成 restart.sh(重启) 文件，请检查脚本是否与本地指令符合...")

    async def save_restart_info(self, bot_id: str, user_id: str) -> None:
        """保存重启信息"""
        async with aiofiles.open(self.restart_mark, "w", encoding="utf8") as f:
            await f.write(f"{bot_id} {user_id}")

    async def read_restart_info(self) -> Optional[Tuple[str, str]]:
        """读取重启信息"""
        if not self.restart_mark.exists():
            return None
            
        async with aiofiles.open(self.restart_mark, encoding="utf8") as f:
            content = await f.read()
            return tuple(content.split())

    def execute_restart(self) -> None:
        """执行重启操作"""
        if self.is_windows:
            python = sys.executable
            os.execl(python, python, *sys.argv)
        else:
            os.system("./restart.sh")  # noqa: ASYNC221

    async def notify_restart_success(self, bot: Bot, user_id: str) -> None:
        """通知重启成功"""
        if target := PlatformUtils.get_target(user_id=user_id):
            await MessageUtils.build_message(
                f"{BotConfig.self_nickname}已成功重启！"
            ).send(target, bot=bot)
        self.restart_mark.unlink()

restart_manager = RestartManager()
_matcher = on_command(
    "重启",
    permission=SUPERUSER,
    rule=to_me(),
    priority=1,
    block=True,
)

@_matcher.got(
    "flag",
    prompt=f"确定是否重启{BotConfig.self_nickname}？\n确定请回复[是|好|确定]\n（重启失败咱们将失去联系，请谨慎！）",
)
async def handle_restart(bot: Bot, session: Uninfo, flag: str = ArgStr("flag")):
    if flag.lower() not in {"true", "是", "好", "确定", "确定是"}:
        await MessageUtils.build_message("已取消操作...").send()
        return

    await MessageUtils.build_message(
        f"开始重启{BotConfig.self_nickname}..请稍等..."
    ).send()
    
    await restart_manager.save_restart_info(bot.self_id, session.user.id)
    logger.info("开始重启真寻...", "重启", session=session)
    restart_manager.execute_restart()

@nonebot.get_driver().on_bot_connect
async def handle_bot_connect(bot: Bot):
    await restart_manager.create_restart_script(bot.config.port)
    
    if restart_info := await restart_manager.read_restart_info():
        bot_id, user_id = restart_info
        if bot := nonebot.get_bot(bot_id):
            await restart_manager.notify_restart_success(bot, user_id)
