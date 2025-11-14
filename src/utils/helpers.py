"""
Helper functions for data formatting, validation, and common operations.
"""

import re
from typing import Optional, Tuple, Callable, List
import wx
import time
import threading


def format_price(price: Optional[float]) -> str:
    """
    Format price to display string with appropriate precision.
    
    Args:
        price: Price value
        
    Returns:
        Formatted price string (e.g., "1.234")
    """
    if price is None:
        return "--"
    
    return f"{price:.3f}"


def format_percent(percent: Optional[float], include_sign: bool = True) -> str:
    """
    Format percentage to display string with sign and symbol.
    
    Args:
        percent: Percentage value (e.g., 2.35 for 2.35%)
        include_sign: Whether to include + sign for positive values
        
    Returns:
        Formatted percentage string (e.g., "+2.35%", "-1.23%")
    """
    if percent is None:
        return "--"
    
    if include_sign and percent > 0:
        return f"+{percent:.2f}%"
    else:
        return f"{percent:.2f}%"


def format_percent_with_arrow(percent: Optional[float]) -> str:
    """
    Format percentage with directional arrow (↑/↓/-).
    
    Args:
        percent: Percentage value
        
    Returns:
        Formatted percentage string with arrow (e.g., "↑2.35%")
    """
    if percent is None:
        return "--"
    
    if percent > 0:
        return f"↑{percent:.2f}%"
    elif percent < 0:
        return f"↓{abs(percent):.2f}%"
    else:
        return "0.00%"


def format_volume(volume: Optional[int]) -> str:
    """
    Format trading volume to human-readable string.
    
    Args:
        volume: Volume value
        
    Returns:
        Formatted volume string (e.g., "1.2亿", "8500万")
    """
    if volume is None or volume == 0:
        return "--"
    
    # Convert to 亿 (hundred million)
    if volume >= 100_000_000:
        return f"{volume / 100_000_000:.1f}亿"
    
    # Convert to 万 (ten thousand)
    if volume >= 10_000:
        return f"{volume / 10_000:.0f}万"
    
    return str(volume)


def validate_etf_code(code: str) -> bool:
    """
    Validate ETF code format (6-digit number).
    
    Args:
        code: ETF code string
        
    Returns:
        True if valid, False otherwise
    """
    if not code:
        return False
    
    # Must be exactly 6 digits
    pattern = r'^\d{6}$'
    return bool(re.match(pattern, code))


def get_market_prefix(code: str) -> str:
    """
    Get market prefix for ETF code (used in API requests).
    
    Args:
        code: 6-digit ETF code
        
    Returns:
        Market prefix ("1" for Shanghai, "0" for Shenzhen)
    """
    if not code or len(code) != 6:
        return "1"  # Default to Shanghai
    
    # Shanghai market: 50xxxx, 51xxxx, 52xxxx, 56xxxx, 58xxxx
    # Shenzhen market: 15xxxx, 16xxxx, 18xxxx
    first_two = code[:2]
    
    if first_two in ['50', '51', '52', '56', '58']:
        return "1"  # Shanghai
    elif first_two in ['15', '16', '18']:
        return "0"  # Shenzhen
    else:
        # Default to Shanghai for unknown patterns
        return "1"

def parse_symbol(symbol: str) -> Tuple[str, str]:
    market = ""
    core = symbol
    if "." in symbol:
        parts = symbol.split(".")
        core = parts[0]
        market = parts[1].upper()
    return market, core


def get_color_for_change(change_percent: Optional[float]) -> str:
    """
    Get display color name based on change percentage.
    
    Args:
        change_percent: Percentage change
        
    Returns:
        Color name ("green", "red", "gray")
    """
    if change_percent is None:
        return "gray"
    
    if change_percent > 0:
        return "green"
    elif change_percent < 0:
        return "red"
    else:
        return "gray"


def clamp(value: float, min_value: float, max_value: float) -> float:
    """
    Clamp a value between min and max bounds.
    
    Args:
        value: Value to clamp
        min_value: Minimum bound
        max_value: Maximum bound
        
    Returns:
        Clamped value
    """
    return max(min_value, min(value, max_value))


def is_trading_time() -> bool:
    """
    检测当前是否在交易时间内
    
    交易时间：
    - 周一到周五
    - 上午：09:00-11:30（包含盘前准备和集合竞价）
    - 下午：13:00-15:00
    
    Returns:
        True if in trading hours
    """
    from datetime import datetime, time
    
    now = datetime.now()
    
    # 检查是否周末
    if now.weekday() >= 5:  # 5=Saturday, 6=Sunday
        return False
    
    # 检查时间
    current_time = now.time()
    
    # 上午交易时间 09:00-11:30（包含盘前和集合竞价）
    morning_start = time(9, 0)
    morning_end = time(11, 30)
    
    # 下午交易时间 13:00-15:00
    afternoon_start = time(13, 0)
    afternoon_end = time(15, 0)
    
    return (morning_start <= current_time <= morning_end or 
            afternoon_start <= current_time <= afternoon_end)


def get_next_trading_time() -> str:
    """
    获取下一个交易时间段的描述
    
    Returns:
        描述字符串
    """
    from datetime import datetime, time
    
    now = datetime.now()
    current_time = now.time()
    
    # 周末
    if now.weekday() >= 5:
        return "周末休市"
    
    # 早于09:00
    if current_time < time(9, 0):
        return "盘前准备，09:00 开始"
    
    # 11:30-13:00午休
    if time(11, 30) < current_time < time(13, 0):
        return "午休中，13:00 开盘"
    
    # 15:00后
    if current_time > time(15, 0):
        return "已收盘，明日 09:00 开始"
    
    return "交易中"


def create_text_icon(
    text: str,
    width: int = 350,
    height: int = 32,
    bg_color: Tuple[int, int, int] = (240, 240, 240),
    fg_color: Tuple[int, int, int] = (0, 0, 0),
    font_size: int = 12
) -> wx.Icon:
    """
    创建包含文字的图标，用于系统托盘显示。
    
    Args:
        text: 要显示的文字内容
        width: 图标宽度（像素）
        height: 图标高度（像素）
        bg_color: 背景颜色 RGB 元组
        fg_color: 文字颜色 RGB 元组
        font_size: 字体大小
        
    Returns:
        wx.Icon 对象
    """
    # 创建位图
    bitmap = wx.Bitmap(width, height)
    
    # 创建内存 DC 用于绘制
    dc = wx.MemoryDC()
    dc.SelectObject(bitmap)
    
    # 设置背景色
    dc.SetBackground(wx.Brush(wx.Colour(*bg_color)))
    dc.Clear()
    
    # 设置字体和文字颜色（使用加粗字体提高可读性）
    font = wx.Font(
        font_size,
        wx.FONTFAMILY_DEFAULT,
        wx.FONTSTYLE_NORMAL,
        wx.FONTWEIGHT_BOLD  # 加粗字体
    )
    dc.SetFont(font)
    dc.SetTextForeground(wx.Colour(*fg_color))
    
    # 获取文字尺寸
    text_width, text_height = dc.GetTextExtent(text)
    
    # 居中绘制文字
    x = max(2, (width - text_width) // 2)
    y = (height - text_height) // 2
    dc.DrawText(text, x, y)
    
    # 释放 DC
    dc.SelectObject(wx.NullBitmap)
    
    # 转换为图标
    icon = wx.Icon()
    icon.CopyFromBitmap(bitmap)
    
    return icon


def get_icon_color_for_change(change_percent: float) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    """
    根据涨跌幅获取图标的背景色和前景色。
    
    Args:
        change_percent: 涨跌幅百分比
        
    Returns:
        (背景色 RGB, 前景色 RGB) 元组
    """
    if change_percent > 0:
        # 上涨 - 浅绿背景，更深的绿色文字（提高对比度）
        return (230, 255, 230), (0, 100, 0)
    elif change_percent < 0:
        # 下跌 - 浅红背景，更深的红色文字（提高对比度）
        return (255, 230, 230), (180, 0, 0)
    else:
        # 平盘 - 浅灰背景，更深的灰色文字
        return (240, 240, 240), (60, 60, 60)


class Debouncer:
    def __init__(self):
        self._last = {}

    def allow(self, key: str, interval_ms: int) -> bool:
        now = time.perf_counter()
        last = self._last.get(key, 0.0)
        if (now - last) * 1000 < interval_ms:
            return False
        self._last[key] = now
        return True


def set_button_loading(btn: wx.Button, loading: bool):
    if loading:
        orig = getattr(btn, "_orig_label", None)
        if orig is None:
            setattr(btn, "_orig_label", btn.GetLabel())
        btn.SetLabel("处理中…")
        btn.SetBackgroundColour(wx.Colour(255, 245, 200))
        btn.Refresh()
    else:
        orig = getattr(btn, "_orig_label", None)
        if orig is not None:
            btn.SetLabel(orig)
        btn.SetBackgroundColour(wx.NullColour)
        btn.Refresh()


def run_with_guard(
    button: wx.Button,
    group_buttons: List[wx.Button],
    fn: Callable[[], None],
    on_success: Optional[Callable[[], None]] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
):
    set_button_loading(button, True)
    for b in group_buttons:
        try:
            b.Disable()
        except Exception:
            pass

    def _runner():
        err: Optional[Exception] = None
        try:
            fn()
        except Exception as e:
            err = e

        def _finish():
            set_button_loading(button, False)
            for b in group_buttons:
                try:
                    b.Enable()
                except Exception:
                    pass
            if err is None:
                if on_success:
                    on_success()
            else:
                if on_error:
                    on_error(err)

        wx.CallAfter(_finish)

    threading.Thread(target=_runner, daemon=True).start()
