'''
Author: xx
Date: 2025-03-22 14:42:41
LastEditors: Do not edit
LastEditTime: 2025-03-23 00:52:42
Description: 
FilePath: \zhenxun\zhenxun_bot\zhenxun\builtin_plugins\scheduler\auto_backup.py
'''
from pathlib import Path
import shutil
import asyncio
from asyncio import TimeoutError
from concurrent.futures import ThreadPoolExecutor

from nonebot_plugin_apscheduler import scheduler

from zhenxun.configs.config import Config
from zhenxun.services.log import logger

Config.add_plugin_config(
    "_backup",
    "BACKUP_FLAG",
    True,
    help="是否开启文件备份",
    default_value=True,
    type=bool,
)

Config.add_plugin_config(
    "_backup",
    "BACKUP_DIR_OR_FILE",
    ["data"],
    help="备份的文件夹或文件",
    default_value=[],
    type=list[str],
)

# 创建信号量
_backup_semaphore = asyncio.Semaphore(5)
_thread_pool = ThreadPoolExecutor(max_workers=5)

async def execute_backup_with_timeout(path_file: str, _backup_path: Path) -> None:
    try:
        path = Path(path_file)
        _p = _backup_path / path_file
        
        # 将文件操作放在线程池中执行
        async with _backup_semaphore:
            try:
                await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        _thread_pool,
                        lambda: _do_backup(path, _p, path_file)
                    ),
                    timeout=30.0
                )
                logger.debug(f"已完成自动备份：{path_file}", "自动备份")
            except TimeoutError:
                logger.error(f"备份文件 {path_file} 超时（30s）", "自动备份")
    except Exception as e:
        logger.error(f"自动备份文件 {path_file} 发生错误", "自动备份", e=e)

def _do_backup(path: Path, _p: Path, path_file: str) -> None:
    if path.exists():
        if path.is_dir():
            if _p.exists():
                shutil.rmtree(_p, ignore_errors=True)
            shutil.copytree(path_file, _p)
        else:
            if _p.exists():
                _p.unlink()
            shutil.copy(path_file, _p)

# 自动备份
@scheduler.scheduled_job(
    "cron",
    hour=3,
    minute=25,
)
async def auto_backup():
    if not Config.get_config("_backup", "BACKUP_FLAG"):
        return
    _backup_path = Path() / "backup"
    _backup_path.mkdir(exist_ok=True, parents=True)
    
    if backup_dir_or_file := Config.get_config("_backup", "BACKUP_DIR_OR_FILE"):
        backup_tasks = [
            execute_backup_with_timeout(path_file, _backup_path)
            for path_file in backup_dir_or_file
        ]
        await asyncio.gather(*backup_tasks)
        
    logger.info("自动备份成功...", "自动备份")
