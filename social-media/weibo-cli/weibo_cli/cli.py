from __future__ import annotations

import sys
from typing import Any

import click

from weibo_cli import (
    __version__,
    cache,
    client,
    config,
    exceptions,
    formatter,
    models,
    parser,
    serialization,
)
from weibo_cli.auth import get_credentials


# ─── Output Dispatcher ─────────────────────────────────────────────────────────


def _output(data: Any, fmt: str) -> None:
    """Route data to appropriate formatter based on format flag."""
    if fmt == "rich":
        return  # Formatters print directly
    elif fmt == "json":
        serialization.output_json(data, pretty=True)
    elif fmt == "yaml":
        serialization.output_yaml(data)
    elif fmt == "compact":
        serialization.output_json(data, pretty=False)


# ─── Global Options ───────────────────────────────────────────────────────────


@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    """
    weibo-cli — 微博命令行工具

    登录: weibo login
    热搜: weibo hot
    搜索: weibo search <关键词>
    用户: weibo user <uid>
    时间线: weibo timeline [uid]
    发帖: 暂不支持（微博限制严格）
    """
    pass


# ─── Auth Group ───────────────────────────────────────────────────────────────


@cli.group("auth")
def auth_group() -> None:
    """认证管理"""
    pass


@auth_group.command("status")
def auth_status() -> None:
    """查看当前登录状态"""
    creds = config.load_credentials()
    logged_in = creds is not None and bool(creds.cookie)
    formatter.print_auth_status(creds.uid if creds else None, logged_in)


@auth_group.command("login")
def auth_login() -> None:
    """登录微博（浏览器Cookie提取）"""
    from weibo_cli.auth import login
    from weibo_cli import exceptions

    click.echo("正在启动登录流程...")
    try:
        login()
        creds = config.load_credentials()
        formatter.print_auth_status(creds.uid if creds else None, True)
    except exceptions.AuthenticationError as e:
        formatter.print_error(str(e))
        raise SystemExit(1)


@auth_group.command("qr-login")
def auth_qr_login() -> None:
    """二维码登录（无需浏览器）"""
    from weibo_cli.auth import qr_login
    from weibo_cli import exceptions

    click.echo("正在获取二维码，请用微博手机App扫描...")
    try:
        qr_login()
        creds = config.load_credentials()
        formatter.print_auth_status(creds.uid if creds else None, True)
    except exceptions.AuthenticationError as e:
        formatter.print_error(str(e))
        raise SystemExit(1)


@auth_group.command("logout")
def auth_logout() -> None:
    """退出登录"""
    config.clear_credentials()
    formatter.print_info("已退出登录")


@auth_group.command("clear-cache")
def auth_clear_cache() -> None:
    """清除本地缓存"""
    cache.Cache().clear()
    formatter.print_info("缓存已清除")


# ─── Hot Search ───────────────────────────────────────────────────────────────


@cli.command("hot")
@click.option("--count", "-n", default=10, help="显示条数")
@click.option("--fmt", "-f", type=click.Choice(["rich", "json", "yaml", "compact"]), default=None, help="输出格式")
def hot(count: int, fmt: str | None) -> None:
    """
    微博热搜榜

    示例:
      weibo hot              # 显示前10条
      weibo hot -n 20        # 显示前20条
      weibo hot -f json      # JSON输出
    """
    fmt = fmt or serialization.detect_format(None)

    try:
        wb_client = client.WeiboClient(use_cache=True)
        raw = wb_client.hot_search(page_size=count)
        items = parser.parse_hot_search(raw)

        if fmt == "rich":
            formatter.print_hot_list(items)
        else:
            _output([item.to_dict() for item in items], fmt)

    except exceptions.WeiboError as e:
        formatter.print_error(str(e))
        sys.exit(1)


# ─── Trending ─────────────────────────────────────────────────────────────────


@cli.command("trending")
@click.option("--fmt", "-f", type=click.Choice(["rich", "json", "yaml", "compact"]), default=None)
def trending(fmt: str | None) -> None:
    """
    微博热议话题（侧边栏）

    示例:
      weibo trending
    """
    fmt = fmt or serialization.detect_format(None)

    try:
        wb_client = client.WeiboClient(use_cache=True)
        raw = wb_client.trending()
        items = parser.parse_trending(raw)

        if fmt == "rich":
            formatter.print_hot_list(items)
        else:
            _output([item.to_dict() for item in items], fmt)

    except exceptions.WeiboError as e:
        formatter.print_error(str(e))
        sys.exit(1)


# ─── Timeline ─────────────────────────────────────────────────────────────────


@cli.command("timeline")
@click.option("--uid", "-u", default=None, help="用户UID（为空则查看登录用户首页）")
@click.option("--page", "-p", default=1, help="页码")
@click.option("--fmt", "-f", type=click.Choice(["rich", "json", "yaml", "compact"]), default=None)
def timeline(uid: str | None, page: int, fmt: str | None) -> None:
    """
    用户微博时间线

    示例:
      weibo timeline -u 1195230310        # 查看指定用户微博
      weibo timeline --page 2             # 查看更多
    """
    fmt = fmt or serialization.detect_format(None)

    try:
        wb_client = client.WeiboClient(use_cache=False)

        if uid:
            raw = wb_client.user_posts(uid, page=page)
            weibos = parser.parse_user_posts(raw)
        else:
            raw = wb_client.home_timeline(page=page)
            weibos = parser.parse_timeline(raw)

        if fmt == "rich":
            formatter.print_weibo_list(weibos)
        else:
            _output([w.to_dict() for w in weibos], fmt)

    except exceptions.WeiboError as e:
        formatter.print_error(str(e))
        sys.exit(1)


# ─── Search ───────────────────────────────────────────────────────────────────


@cli.command("search")
@click.argument("keyword")
@click.option("--page", "-p", default=1, help="页码")
@click.option("--fmt", "-f", type=click.Choice(["rich", "json", "yaml", "compact"]), default=None)
def search(keyword: str, page: int, fmt: str | None) -> None:
    """
    搜索微博

    示例:
      weibo search Python
      weibo search AI -n 20
    """
    fmt = fmt or serialization.detect_format(None)

    try:
        wb_client = client.WeiboClient(use_cache=True)
        raw = wb_client.search(keyword, page=page)
        weibos = parser.parse_search(raw)

        if fmt == "rich":
            formatter.print_weibo_list(weibos)
        else:
            _output([w.to_dict() for w in weibos], fmt)

    except exceptions.WeiboError as e:
        formatter.print_error(str(e))
        sys.exit(1)


# ─── Status / Comments ────────────────────────────────────────────────────────


@cli.command("status")
@click.argument("mblog_id")
@click.option("--fmt", "-f", type=click.Choice(["rich", "json", "yaml", "compact"]), default=None)
def status_cmd(mblog_id: str, fmt: str | None) -> None:
    """
    查看单条微博详情

    示例:
      weibo status NsIjy4WXe
    """
    fmt = fmt or serialization.detect_format(None)

    try:
        wb_client = client.WeiboClient(use_cache=True)
        raw = wb_client.status(mblog_id)
        w = parser.parse_status(raw)

        if fmt == "rich":
            formatter.print_weibo_detail(w)
        else:
            _output(w.to_dict(), fmt)

    except exceptions.WeiboError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@cli.command("comments")
@click.argument("mblog_id")
@click.option("--page", "-p", default=1, help="页码")
@click.option("--fmt", "-f", type=click.Choice(["rich", "json", "yaml", "compact"]), default=None)
def comments_cmd(mblog_id: str, page: int, fmt: str | None) -> None:
    """
    查看微博评论

    示例:
      weibo comments NsIjy4WXe
    """
    fmt = fmt or serialization.detect_format(None)

    try:
        wb_client = client.WeiboClient(use_cache=False)
        raw = wb_client.comments(mblog_id, page=page)
        comments = parser.parse_comments(raw)

        if fmt == "rich":
            formatter.print_comments(comments)
        else:
            _output([c.to_dict() for c in comments], fmt)

    except exceptions.WeiboError as e:
        formatter.print_error(str(e))
        sys.exit(1)


# ─── User ─────────────────────────────────────────────────────────────────────


@cli.command("user")
@click.argument("uid")
@click.option("--fmt", "-f", type=click.Choice(["rich", "json", "yaml", "compact"]), default=None)
def user_cmd(uid: str, fmt: str | None) -> None:
    """
    查看用户资料

    示例:
      weibo user 1195230310
    """
    fmt = fmt or serialization.detect_format(None)

    try:
        wb_client = client.WeiboClient(use_cache=True)
        raw = wb_client.user_info(uid)
        user = parser.parse_user(raw)

        if fmt == "rich":
            formatter.print_user(user)
        else:
            _output(user.to_dict(), fmt)

    except exceptions.WeiboError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@cli.command("followers")
@click.argument("uid")
@click.option("--page", "-p", default=1, help="页码")
@click.option("--fmt", "-f", type=click.Choice(["rich", "json", "yaml", "compact"]), default=None)
def followers_cmd(uid: str, page: int, fmt: str | None) -> None:
    """
    查看用户粉丝

    示例:
      weibo followers 1195230310
    """
    fmt = fmt or serialization.detect_format(None)

    try:
        wb_client = client.WeiboClient(use_cache=False)
        raw = wb_client.followers(uid, page=page)
        users = parser.parse_followers(raw)

        if fmt == "rich":
            formatter.print_followers(users)
        else:
            _output([u.to_dict() for u in users], fmt)

    except exceptions.WeiboError as e:
        formatter.print_error(str(e))
        sys.exit(1)


@cli.command("following")
@click.argument("uid")
@click.option("--page", "-p", default=1, help="页码")
@click.option("--fmt", "-f", type=click.Choice(["rich", "json", "yaml", "compact"]), default=None)
def following_cmd(uid: str, page: int, fmt: str | None) -> None:
    """
    查看用户关注

    示例:
      weibo following 1195230310
    """
    fmt = fmt or serialization.detect_format(None)

    try:
        wb_client = client.WeiboClient(use_cache=False)
        raw = wb_client.following(uid, page=page)
        users = parser.parse_followers(raw)

        if fmt == "rich":
            formatter.print_followers(users)
        else:
            _output([u.to_dict() for u in users], fmt)

    except exceptions.WeiboError as e:
        formatter.print_error(str(e))
        sys.exit(1)


# ─── Entry Point ──────────────────────────────────────────────────────────────


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
