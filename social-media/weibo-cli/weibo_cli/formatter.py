from __future__ import annotations

from datetime import datetime
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from weibo_cli import models

console = Console()


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _fmt_count(n: int) -> str:
    """Format count with 万 / 亿 suffix."""
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}亿"
    if n >= 10_000:
        return f"{n / 10_000:.1f}万"
    return str(n)


def _fmt_time(dt: datetime) -> str:
    """Format datetime to short relative-like string."""
    now = datetime.now()
    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 60:
        return "刚刚"
    if seconds < 3600:
        return f"{int(seconds / 60)}分钟前"
    if seconds < 86400:
        return f"{int(seconds / 3600)}小时前"
    if seconds < 604800:
        return f"{int(seconds / 86400)}天前"

    return dt.strftime("%m-%d")


def _truncate(text: str, length: int = 40) -> str:
    """Truncate text with ellipsis."""
    text = text.replace("\n", " ").strip()
    if len(text) <= length:
        return text
    return text[:length] + "..."


# ─── Tables ───────────────────────────────────────────────────────────────────


def print_hot_list(items: list[models.HotItem]) -> None:
    """Print hot search items as a table."""
    table = Table(title="🔥 微博热搜榜", show_header=True, header_style="bold")
    table.add_column("排名", justify="right", style="cyan", width=4)
    table.add_column("话题", style="white")
    table.add_column("热度", justify="right", style="orange3")

    for item in items:
        rank_str = f"# {item.rank}" if item.rank else "—"
        label = f"[{item.label}]" if item.label else ""
        table.add_row(rank_str, f"{label} {item.word}", _fmt_count(item.num))

    console.print(table)


def print_weibo_list(weibos: list[models.Weibo], full_text: bool = False) -> None:
    """Print a list of weibos as a table."""
    table = Table(title="📝 微博列表", show_header=True, header_style="bold")
    table.add_column("作者", style="cyan", width=12)
    table.add_column("内容", style="white")
    table.add_column("时间", style="dim", width=8)
    table.add_column("赞", justify="right", style="red", width=5)
    table.add_column("评", justify="right", style="blue", width=5)
    table.add_column("转", justify="right", style="green", width=5)

    for w in weibos:
        author = w.user.name if w.user else "未知"
        text = w.text_raw if full_text else _truncate(w.text_raw)
        time_str = _fmt_time(w.created_at)
        table.add_row(
            author,
            text,
            time_str,
            _fmt_count(w.attitudes_count),
            _fmt_count(w.comments_count),
            _fmt_count(w.reposts_count),
        )

    console.print(table)


def print_weibo_detail(w: models.Weibo) -> None:
    """Print a single weibo with full details."""
    author = w.user.name if w.user else "未知"
    verified = "✓" if (w.user and w.user.verified) else ""

    console.print(f"\n[bold cyan]{author}[/bold cyan] {verified} [dim]({_fmt_time(w.created_at)})[/dim]")
    console.print("")
    console.print(Markdown(w.text_raw))
    console.print("")
    console.print(
        f"👍 {w.attitudes_count}  💬 {w.comments_count}  🔄 {w.reposts_count}"
    )
    console.print(f"[dim]{w.url}[/dim]")
    console.print("")


def print_comments(comments: list[models.Comment]) -> None:
    """Print comments as a table."""
    table = Table(title="💬 评论", show_header=True, header_style="bold")
    table.add_column("用户", style="cyan", width=10)
    table.add_column("内容", style="white")
    table.add_column("时间", style="dim", width=8)
    table.add_column("赞", justify="right", style="red", width=5)

    for c in comments:
        user = c.user.name if c.user else "未知"
        table.add_row(user, _truncate(c.text_raw), _fmt_time(c.created_at), _fmt_count(c.like_count))

    console.print(table)


def print_user(user: models.User) -> None:
    """Print user profile."""
    verified_str = "[red]✓ 认证[/red]" if user.verified else ""
    console.print(f"\n[bold cyan]{user.name}[/bold cyan] {verified_str}")
    console.print(f"\n[dim]{user.description}[/dim]\n")
    console.print(
        f"粉丝: {_fmt_count(user.followers_count)} | "
        f"关注: {_fmt_count(user.friends_count)} | "
        f"微博: {_fmt_count(user.statuses_count)}"
    )
    console.print(f"[dim]https://weibo.com/u/{user.id}[/dim]\n")


def print_followers(users: list[models.User]) -> None:
    """Print followers/following as a table."""
    table = Table(title="👥 用户列表", show_header=True, header_style="bold")
    table.add_column("用户", style="cyan", width=15)
    table.add_column("简介", style="white")
    table.add_column("粉丝", justify="right", style="orange3", width=8)

    for u in users:
        table.add_row(u.name, _truncate(u.description, 30), _fmt_count(u.followers_count))

    console.print(table)


# ─── Status Lines ──────────────────────────────────────────────────────────────


def print_auth_status(uid: str | None, logged_in: bool) -> None:
    """Print authentication status."""
    if logged_in and uid:
        console.print(f"[green]✓ 已登录 (UID: {uid})[/green]")
    else:
        console.print("[yellow]⚠ 未登录，请运行 weibo login[/yellow]")


def print_error(message: str) -> None:
    """Print error message to stderr."""
    import sys
    stderr_console = Console(file=sys.stderr)
    stderr_console.print(f"[bold red]错误:[/bold red] {message}")


def print_warning(message: str) -> None:
    """Print warning message."""
    console.print(f"[yellow]警告:[/yellow] {message}")


def print_info(message: str) -> None:
    """Print info message."""
    console.print(f"[blue]ℹ[/blue] {message}")
