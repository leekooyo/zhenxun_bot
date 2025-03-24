import asyncio
from asyncio.exceptions import TimeoutError
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
import time
from typing import Any, ClassVar, Literal

import aiofiles
from anyio import EndOfStream
import httpx
from httpx import ConnectTimeout, HTTPStatusError, Response
from nonebot_plugin_alconna import UniMessage
from nonebot_plugin_htmlrender import get_browser
from playwright.async_api import Page
from retrying import retry
import rich

from zhenxun.configs.config import BotConfig
from zhenxun.services.log import logger
from zhenxun.utils.message import MessageUtils
from zhenxun.utils.user_agent import get_user_agent

# from .browser import get_browser


class AsyncHttpx:
    proxy: ClassVar[dict[str, str | None]] = {
        "http://": BotConfig.system_proxy,
        "https://": BotConfig.system_proxy,
    }

    @classmethod
    @retry(stop_max_attempt_number=3)
    async def get(
        cls,
        url: str | list[str],
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        verify: bool = True,
        use_proxy: bool = True,
        proxy: dict[str, str] | None = None,
        timeout: int = 30,  # noqa: ASYNC109
        **kwargs,
    ) -> Response:
        """Get

        参数:
            url: url
            params: params
            headers: 请求头
            cookies: cookies
            verify: verify
            use_proxy: 使用默认代理
            proxy: 指定代理
            timeout: 超时时间
        """
        urls = [url] if isinstance(url, str) else url
        return await cls._get_first_successful(
            urls,
            params=params,
            headers=headers,
            cookies=cookies,
            verify=verify,
            use_proxy=use_proxy,
            proxy=proxy,
            timeout=timeout,
            **kwargs,
        )

    @classmethod
    async def _get_first_successful(
        cls,
        urls: list[str],
        **kwargs,
    ) -> Response:
        last_exception = None
        for url in urls:
            try:
                return await cls._get_single(url, **kwargs)
            except Exception as e:
                last_exception = e
                if url != urls[-1]:
                    logger.warning(f"获取 {url} 失败, 尝试下一个")
        raise last_exception or Exception("All URLs failed")

    @classmethod
    async def _get_single(
        cls,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        verify: bool = True,
        use_proxy: bool = True,
        proxy: dict[str, str] | None = None,
        timeout: int = 30,  # noqa: ASYNC109
        **kwargs,
    ) -> Response:
        if not headers:
            headers = get_user_agent()
        _proxy = proxy or (cls.proxy if use_proxy else None)
        async with httpx.AsyncClient(proxies=_proxy, verify=verify) as client:  # type: ignore
            return await client.get(
                url,
                params=params,
                headers=headers,
                cookies=cookies,
                timeout=timeout,
                **kwargs,
            )

    @classmethod
    async def head(
        cls,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        verify: bool = True,
        use_proxy: bool = True,
        proxy: dict[str, str] | None = None,
        timeout: int = 30,  # noqa: ASYNC109
        **kwargs,
    ) -> Response:
        """Get

        参数:
            url: url
            params: params
            headers: 请求头
            cookies: cookies
            verify: verify
            use_proxy: 使用默认代理
            proxy: 指定代理
            timeout: 超时时间
        """
        if not headers:
            headers = get_user_agent()
        _proxy = proxy or (cls.proxy if use_proxy else None)
        async with httpx.AsyncClient(proxies=_proxy, verify=verify) as client:  # type: ignore
            return await client.head(
                url,
                params=params,
                headers=headers,
                cookies=cookies,
                timeout=timeout,
                **kwargs,
            )

    @classmethod
    async def post(
        cls,
        url: str,
        *,
        data: dict[str, Any] | None = None,
        content: Any = None,
        files: Any = None,
        verify: bool = True,
        use_proxy: bool = True,
        proxy: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        timeout: int = 30,  # noqa: ASYNC109
        **kwargs,
    ) -> Response:
        """
        说明:
            Post
        参数:
            url: url
            data: data
            content: content
            files: files
            use_proxy: 是否默认代理
            proxy: 指定代理
            json: json
            params: params
            headers: 请求头
            cookies: cookies
            timeout: 超时时间
        """
        if not headers:
            headers = get_user_agent()
        _proxy = proxy or (cls.proxy if use_proxy else None)
        async with httpx.AsyncClient(proxies=_proxy, verify=verify) as client:  # type: ignore
            return await client.post(
                url,
                content=content,
                data=data,
                files=files,
                json=json,
                params=params,
                headers=headers,
                cookies=cookies,
                timeout=timeout,
                **kwargs,
            )

    @classmethod
    async def get_content(cls, url: str, **kwargs) -> bytes:
        res = await cls.get(url, **kwargs)
        return res.content

    @classmethod
    async def download_file(
        cls,
        url: str | list[str],
        path: str | Path,
        *,
        params: dict[str, str] | None = None,
        verify: bool = True,
        use_proxy: bool = True,
        proxy: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        timeout: int = 30,
        stream: bool = False,
        follow_redirects: bool = True,
        **kwargs,
    ) -> bool:
        """异步下载文件到指定路径。

        Args:
            url: 下载链接或链接列表
            path: 保存文件的路径
            params: 请求参数
            verify: 是否验证SSL证书
            use_proxy: 是否使用默认代理
            proxy: 指定代理配置
            headers: 请求头
            cookies: Cookie信息
            timeout: 超时时间(秒)
            stream: 是否使用流式下载
            follow_redirects: 是否跟随重定向
            **kwargs: 其他传递给 httpx 的参数

        Returns:
            bool: 下载是否成功

        Raises:
            TimeoutError: 下载超时
            HTTPStatusError: HTTP状态码错误
            Exception: 其他异常
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        urls = [url] if isinstance(url, str) else url

        for _ in range(3):  # 重试3次
            for current_url in urls:
                try:
                    if stream:
                        success = await cls._download_with_stream(
                            current_url, path, params, headers, cookies, 
                            verify, use_proxy, proxy, timeout, follow_redirects, **kwargs
                        )
                    else:
                        success = await cls._download_without_stream(
                            current_url, path, params, headers, cookies,
                            use_proxy, proxy, timeout, follow_redirects, **kwargs
                        )
                    if success:
                        return True

                except HTTPStatusError as e:
                    status_code = e.response.status_code
                    logger.warning(
                        f"下载 {current_url} 失败: HTTP {status_code} - {e.response.reason_phrase}"
                    )
                    if status_code == 404:
                        logger.error(f"资源不存在: {current_url}")
                        continue
                    elif status_code in (401, 403):
                        logger.error(f"无访问权限: {current_url}")
                        continue
                    elif status_code >= 500:
                        logger.error(f"服务器错误: {current_url}")
                        continue
                    else:
                        logger.warning(f"尝试下一个地址: {current_url}")

                except (TimeoutError, ConnectTimeout):
                    logger.warning(f"下载 {current_url} 超时.. 尝试下一个地址..")
                except EndOfStream as e:
                    logger.warning(f"下载 {current_url} EndOfStream 异常 Path：{path.absolute()}", e=e)
                    if path.exists():
                        return True
                except Exception as e:
                    logger.error(f"下载 {current_url} 发生未知错误: {str(e)}")

            # 所有URL都尝试完一轮后的等待
            await asyncio.sleep(1)

        logger.error(f"所有下载地址均失败 {url}.. Path：{path.absolute()}")
        return False

    @classmethod
    async def _check_response_status(cls, response: Response, url: str) -> None:
        """检查响应状态码并处理异常情况

        Args:
            response: HTTP响应对象
            url: 请求的URL

        Raises:
            HTTPStatusError: 当状态码不在2xx范围内时抛出
        """
        try:
            response.raise_for_status()
        except HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code == 404:
                raise HTTPStatusError(f"资源不存在: {url}", request=e.request, response=e.response)
            elif status_code in (401, 403):
                raise HTTPStatusError(f"无访问权限: {url}", request=e.request, response=e.response)
            elif status_code >= 500:
                raise HTTPStatusError(f"服务器错误: {url}", request=e.request, response=e.response)
            raise

    @classmethod
    async def _download_without_stream(
        cls, url: str, path: Path, params: dict | None,
        headers: dict | None, cookies: dict | None,
        use_proxy: bool, proxy: dict | None,
        timeout: int, follow_redirects: bool,
        **kwargs
    ) -> bool:
        """普通下载模式"""
        response = await cls.get(
            url, params=params, headers=headers,
            cookies=cookies, use_proxy=use_proxy,
            proxy=proxy, timeout=timeout,
            follow_redirects=follow_redirects, **kwargs
        )
        
        await cls._check_response_status(response, url)
        
        async with aiofiles.open(path, "wb") as wf:
            await wf.write(response.content)
            logger.info(f"下载 {url} 成功.. Path：{path.absolute()}")
        return True

    @classmethod
    async def _download_with_stream(
        cls, url: str, path: Path, params: dict | None,
        headers: dict | None, cookies: dict | None,
        verify: bool, use_proxy: bool, proxy: dict | None,
        timeout: int, follow_redirects: bool,
        **kwargs
    ) -> bool:
        """流式下载模式"""
        if not headers:
            headers = get_user_agent()
        _proxy = proxy or (cls.proxy if use_proxy else None)

        async with httpx.AsyncClient(proxies=_proxy, verify=verify) as client:
            async with client.stream(
                "GET", url, params=params, headers=headers,
                cookies=cookies, timeout=timeout,
                follow_redirects=follow_redirects, **kwargs
            ) as response:
                await cls._check_response_status(response, url)
                logger.info(f"开始下载 {path.name}.. Url: {url}.. Path: {path.absolute()}")
                return await cls._handle_stream_download(response, path)

    @classmethod
    async def _handle_stream_download(cls, response: Response, path: Path) -> bool:
        """处理流式下载的具体逻辑"""
        async with aiofiles.open(path, "wb") as wf:
            total = int(response.headers.get("Content-Length", 0))
            with rich.progress.Progress(
                rich.progress.TextColumn(path.name),
                "[progress.percentage]{task.percentage:>3.0f}%",
                rich.progress.BarColumn(bar_width=None),
                rich.progress.DownloadColumn(),
                rich.progress.TransferSpeedColumn(),
            ) as progress:
                download_task = progress.add_task(
                    "Download",
                    total=total or None,
                )
                async for chunk in response.aiter_bytes():
                    await wf.write(chunk)
                    await wf.flush()
                    progress.update(
                        download_task,
                        completed=response.num_bytes_downloaded,
                    )
                logger.info(f"下载成功.. Path：{path.absolute()}")
        return True

    @classmethod
    async def gather_download_file(
        cls,
        url_list: list[str] | list[list[str]],
        path_list: list[str | Path],
        *,
        limit_async_number: int | None = None,
        params: dict[str, str] | None = None,
        use_proxy: bool = True,
        proxy: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
        timeout: int = 30,  # noqa: ASYNC109
        **kwargs,
    ) -> list[bool]:
        """分组同时下载文件

        参数:
            url_list: url列表
            path_list: 存储路径列表
            limit_async_number: 限制同时请求数量
            params: params
            use_proxy: 使用代理
            proxy: 指定代理
            headers: 请求头
            cookies: cookies
            timeout: 超时时间
        """
        if n := len(url_list) != len(path_list):
            raise UrlPathNumberNotEqual(
                f"Url数量与Path数量不对等，Url：{len(url_list)}，Path：{len(path_list)}"
            )
        if limit_async_number and n > limit_async_number:
            m = float(n) / limit_async_number
            x = 0
            j = limit_async_number
            _split_url_list = []
            _split_path_list = []
            for _ in range(int(m)):
                _split_url_list.append(url_list[x:j])
                _split_path_list.append(path_list[x:j])
                x += limit_async_number
                j += limit_async_number
            if int(m) < m:
                _split_url_list.append(url_list[j:])
                _split_path_list.append(path_list[j:])
        else:
            _split_url_list = [url_list]
            _split_path_list = [path_list]
        tasks = []
        result_ = []
        for x, y in zip(_split_url_list, _split_path_list):
            tasks.extend(
                asyncio.create_task(
                    cls.download_file(
                        url,
                        path,
                        params=params,
                        headers=headers,
                        cookies=cookies,
                        use_proxy=use_proxy,
                        timeout=timeout,
                        proxy=proxy,
                        **kwargs,
                    )
                )
                for url, path in zip(x, y)
            )
            _x = await asyncio.gather(*tasks)
            result_ = result_ + list(_x)
            tasks.clear()
        return result_

    @classmethod
    async def get_fastest_mirror(cls, url_list: list[str]) -> list[str]:
        assert url_list

        async def head_mirror(client: type[AsyncHttpx], url: str) -> dict[str, Any]:
            begin_time = time.time()

            response = await client.head(url=url, timeout=6)

            elapsed_time = (time.time() - begin_time) * 1000
            content_length = int(response.headers.get("content-length", 0))

            return {
                "url": url,
                "elapsed_time": elapsed_time,
                "content_length": content_length,
            }

        logger.debug(f"开始获取最快镜像，可能需要一段时间... | URL列表：{url_list}")
        results = await asyncio.gather(
            *(head_mirror(cls, url) for url in url_list),
            return_exceptions=True,
        )
        _results: list[dict[str, Any]] = []
        for result in results:
            if isinstance(result, BaseException):
                logger.warning(f"获取镜像失败，错误：{result}")
            else:
                logger.debug(f"获取镜像成功，结果：{result}")
                _results.append(result)
        _results = sorted(iter(_results), key=lambda r: r["elapsed_time"])
        return [result["url"] for result in _results]


class AsyncPlaywright:
    @classmethod
    @asynccontextmanager
    async def new_page(
        cls, cookies: list[dict[str, Any]] | dict[str, Any] | None = None, **kwargs
    ) -> AsyncGenerator[Page, None]:
        """获取一个新页面

        参数:
            cookies: cookies
        """
        browser = await get_browser()
        ctx = await browser.new_context(**kwargs)
        if cookies:
            if isinstance(cookies, dict):
                cookies = [cookies]
            await ctx.add_cookies(cookies)  # type: ignore
        page = await ctx.new_page()
        try:
            yield page
        finally:
            await page.close()
            await ctx.close()

    @classmethod
    async def screenshot(
        cls,
        url: str,
        path: Path | str,
        element: str | list[str],
        *,
        wait_time: int | None = None,
        viewport_size: dict[str, int] | None = None,
        wait_until: (
            Literal["domcontentloaded", "load", "networkidle"] | None
        ) = "networkidle",
        timeout: float | None = None,  # noqa: ASYNC109
        type_: Literal["jpeg", "png"] | None = None,
        user_agent: str | None = None,
        cookies: list[dict[str, Any]] | dict[str, Any] | None = None,
        **kwargs,
    ) -> UniMessage | None:
        """截图，该方法仅用于简单快捷截图，复杂截图请操作 page

        参数:
            url: 网址
            path: 存储路径
            element: 元素选择
            wait_time: 等待截取超时时间
            viewport_size: 窗口大小
            wait_until: 等待类型
            timeout: 超时限制
            type_: 保存类型
            user_agent: user_agent
            cookies: cookies
        """
        if viewport_size is None:
            viewport_size = {"width": 2560, "height": 1080}
        if isinstance(path, str):
            path = Path(path)
        wait_time = wait_time * 1000 if wait_time else None
        element_list = [element] if isinstance(element, str) else element
        async with cls.new_page(
            cookies,
            viewport=viewport_size,
            user_agent=user_agent,
            **kwargs,
        ) as page:
            await page.goto(url, timeout=timeout, wait_until=wait_until)
            card = page
            for e in element_list:
                if not card:
                    return None
                card = await card.wait_for_selector(e, timeout=wait_time)
            if card:
                await card.screenshot(path=path, timeout=timeout, type=type_)
                return MessageUtils.build_message(path)
        return None


class UrlPathNumberNotEqual(Exception):
    pass


class BrowserIsNone(Exception):
    pass