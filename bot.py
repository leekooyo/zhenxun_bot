import nonebot
nonebot.init()
# from nonebot.adapters.discord import Adapter as DiscordAdapter
# from nonebot.adapters.dodo import Adapter as DoDoAdapter
# from nonebot.adapters.kaiheila import Adapter as KaiheilaAdapter
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter
from zhenxun.services.db_context import disconnect, init

# 初始化 NoneBot
# 获取驱动
driver = nonebot.get_driver()

# 注册适配器
driver.register_adapter(OneBotV11Adapter)

# 启动和关闭时的操作
driver.on_startup(init)
driver.on_shutdown(disconnect)

# 加载 nonebot_plugin_apscheduler
nonebot.load_plugin("nonebot_plugin_localstore")
nonebot.load_plugin("nonebot_plugin_orm")
nonebot.load_plugin("nonebot_plugin_session_orm")
nonebot.load_plugin("nonebot_plugin_userinfo")

# 加载其他插件
nonebot.load_plugins("zhenxun/builtin_plugins")
nonebot.load_plugins("zhenxun/plugins")

if __name__ == "__main__":
    nonebot.run()