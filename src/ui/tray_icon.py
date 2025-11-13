"""
System tray icon with tooltip rotation and context menu.

Provides the main user interface through Windows system tray.
"""

import os
import threading
import time
from typing import Optional, Dict, Callable
from pathlib import Path

import wx
import wx.adv

from ..utils.logger import get_logger
from ..utils.helpers import (
    format_percent_with_arrow, 
    is_trading_time, 
    get_next_trading_time
)
from ..data.models import ETFQuote


class ETFTrayIcon(wx.adv.TaskBarIcon):
    """
    System tray icon with rotating tooltip.
    
    Features:
    - Custom icon in system tray
    - Rotating tooltip showing ETF quotes
    - Right-click context menu
    - Double-click to open detail window
    """
    
    def __init__(
        self,
        icon_path: Optional[str] = None,
        tooltip_format: str = "{name} ({code})\n最新价: {price} ({change_percent})\n更新: {time}",
        rotation_interval: int = 3,
        rotation_mode: str = "both"
    ):
        """
        Initialize tray icon.
        
        Args:
            icon_path: Path to icon file
            tooltip_format: Format string for tooltip
            rotation_interval: Rotation interval in seconds
            rotation_mode: Rotation mode (timer, change, both)
        """
        super().__init__()
        
        self._logger = get_logger(__name__)
        self._tooltip_format = tooltip_format
        self._rotation_interval = rotation_interval
        self._rotation_mode = rotation_mode
        
        # ETF data
        self._etf_data: Dict[str, ETFQuote] = {}
        self._etf_codes: list = []
        self._current_index = 0
        
        # Rotation control
        self._rotation_thread: Optional[threading.Thread] = None
        self._rotation_running = False
        self._rotation_event = threading.Event()
        self._stop_event = threading.Event()
        
        # Pause state
        self._paused = False
        
        # Callbacks
        self._on_settings_callback: Optional[Callable] = None
        self._on_detail_callback: Optional[Callable] = None
        self._on_about_callback: Optional[Callable] = None
        self._on_refresh_callback: Optional[Callable] = None
        self._on_pause_callback: Optional[Callable] = None
        self._on_auto_start_callback: Optional[Callable] = None
        self._on_exit_callback: Optional[Callable] = None
        self._on_menu_open_callback: Optional[Callable] = None
        self._on_menu_close_callback: Optional[Callable] = None
        
        # Set icon
        self._set_icon(icon_path)
        
        # Bind events
        
        self._logger.info("Tray icon initialized")
    
    def _set_icon(self, icon_path: Optional[str]) -> None:
        """
        Set tray icon.
        
        Args:
            icon_path: Path to icon file
        """
        try:
            if icon_path and os.path.exists(icon_path):
                icon = wx.Icon(icon_path)
            else:
                # Use default icon if not found
                icon = wx.Icon()
                icon.CopyFromBitmap(wx.ArtProvider.GetBitmap(
                    wx.ART_INFORMATION, wx.ART_OTHER, (16, 16)
                ))
            
            # Save icon as instance attribute
            self.icon = icon
            self.SetIcon(icon, "ETF Monitor")
            
        except Exception as e:
            self._logger.error(f"Failed to set icon: {e}")
    
    def CreatePopupMenu(self) -> wx.Menu:
        """
        Create right-click context menu.
        
        Returns:
            Context menu
        """
        # 通知暂停悬浮框守护（避免抢占菜单焦点）
        if hasattr(self, '_on_menu_open_callback') and self._on_menu_open_callback:
            try:
                self._on_menu_open_callback()
            except Exception as e:
                self._logger.error(f"Error in menu open callback: {e}")
        
        menu = wx.Menu()
        
        # 绑定菜单销毁事件以恢复守护
        menu.Bind(wx.EVT_MENU_CLOSE, self._on_menu_close)

        item = menu.Append(wx.ID_EXIT, "退出")
        menu.Bind(wx.EVT_MENU, self._on_exit, item)
        
        return menu
    
    def update_data(self, etf_data: Dict[str, ETFQuote], changed_codes: list = None) -> None:
        """
        Update ETF data and optionally trigger rotation.
        
        Args:
            etf_data: Dictionary mapping code to ETFQuote
            changed_codes: List of codes that changed (for change-triggered rotation)
        """
        self._etf_data = etf_data.copy()
        self._etf_codes = list(etf_data.keys())
        
        # Trigger rotation if in change mode and data changed
        if changed_codes and self._rotation_mode in ['change', 'both']:
            if changed_codes:
                # Switch to first changed ETF
                if changed_codes[0] in self._etf_codes:
                    self._current_index = self._etf_codes.index(changed_codes[0])
                    self._update_tooltip()
                    self._rotation_event.set()
    
    def start_rotation(self) -> None:
        """Start tooltip rotation thread."""
        if self._rotation_running:
            return
        
        self._rotation_running = True
        self._stop_event.clear()
        self._rotation_thread = threading.Thread(target=self._rotation_loop, daemon=True)
        self._rotation_thread.start()
        
        self._logger.info(f"Tooltip rotation started: {self._rotation_mode} mode, {self._rotation_interval}s interval")
    
    def stop_rotation(self) -> None:
        """Stop tooltip rotation thread."""
        if not self._rotation_running:
            return
        
        self._rotation_running = False
        self._stop_event.set()
        
        if self._rotation_thread and self._rotation_thread.is_alive():
            self._rotation_thread.join(timeout=2)
        
        self._logger.info("Tooltip rotation stopped")
    
    def _rotation_loop(self) -> None:
        """Rotation loop running in background thread."""
        while self._rotation_running:
            try:
                # Update tooltip with current ETF
                wx.CallAfter(self._update_tooltip)
                
                # Wait for interval or event
                if self._rotation_mode in ['timer', 'both']:
                    # Timer-based rotation
                    if self._stop_event.wait(timeout=self._rotation_interval):
                        break
                    
                    # Move to next ETF
                    self._advance_index()
                    
                elif self._rotation_mode == 'change':
                    # Wait for change event
                    self._rotation_event.wait()
                    self._rotation_event.clear()
                    
                    if not self._rotation_running:
                        break
                        
            except Exception as e:
                self._logger.error(f"Error in rotation loop: {e}")
                time.sleep(1)
    
    def _advance_index(self) -> None:
        """Advance to next ETF in rotation."""
        if not self._etf_codes:
            return
        
        self._current_index = (self._current_index + 1) % len(self._etf_codes)
    
    def _update_tooltip(self) -> None:
        """Update tooltip and icon with current ETF data."""
        if not self._etf_codes or not self._etf_data:
            self.SetIcon(self.icon, "ETF Monitor - 暂无数据")
            return
        
        # Get current ETF
        if self._current_index >= len(self._etf_codes):
            self._current_index = 0
        
        code = self._etf_codes[self._current_index]
        quote = self._etf_data.get(code)
        
        if not quote:
            self.SetIcon(self.icon, "ETF Monitor - 加载中...")
            return
        
        # 创建显示文字：股票名 净值 涨跌幅
        try:
            change_text = format_percent_with_arrow(quote.change_percent)
            # 创建 tooltip 文字（鼠标悬停时显示更详细信息）
            tooltip = f"{quote.name} ({quote.code})\n"
            tooltip += f"最新价: {quote.price:.3f}\n"
            tooltip += f"涨跌幅: {change_text}\n"
            tooltip += f"更新: {quote.update_time}"
            
            # 添加交易状态提示
            if not is_trading_time():
                trading_status = get_next_trading_time()
                tooltip += f"\n[{trading_status}]"
            
            # 更新图标，仅更新 tooltip
            self.SetIcon(self.icon, tooltip)
                
        except Exception as e:
            self._logger.error(f"Error updating icon: {e}", exc_info=True)
            # 出错时使用默认图标
            tooltip = f"{quote.name} ({quote.code})\n{quote.price:.3f}"
            self.SetIcon(self.icon, tooltip)
    
    def update_rotation_settings(self, interval: int, mode: str) -> None:
        """
        Update rotation settings.
        
        Args:
            interval: Rotation interval in seconds
            mode: Rotation mode (timer, change, both)
        """
        self._rotation_interval = interval
        self._rotation_mode = mode
        self._logger.info(f"Rotation settings updated: {mode} mode, {interval}s interval")
    
    def set_paused(self, paused: bool) -> None:
        """
        Set pause state.
        
        Args:
            paused: True to pause, False to resume
        """
        self._paused = paused
    
    # Event handlers
    
    def _on_left_double_click(self, event) -> None:
        """Handle left double-click (disabled)."""
        return
    
    def _on_view_detail(self, event) -> None:
        """Handle view detail menu item."""
        if self._on_detail_callback:
            self._on_detail_callback()
    
    def _on_settings(self, event) -> None:
        """Handle settings menu item."""
        if self._on_settings_callback:
            self._on_settings_callback()
    
    def _on_refresh(self, event) -> None:
        """Handle refresh menu item."""
        if self._on_refresh_callback:
            self._on_refresh_callback()
    
    def _on_pause(self, event) -> None:
        """Handle pause menu item."""
        self._paused = not self._paused
        if self._on_pause_callback:
            self._on_pause_callback(self._paused)
    
    def _on_auto_start(self, event) -> None:
        """Handle auto start menu item."""
        if self._on_auto_start_callback:
            # Get current state and toggle
            self._on_auto_start_callback()
    
    def _on_about(self, event) -> None:
        """Handle about menu item."""
        if self._on_about_callback:
            self._on_about_callback()
    
    def _on_exit(self, event) -> None:
        """Handle exit event."""
        if self._on_exit_callback:
            self._on_exit_callback()

    
    # Callback setters
    
    def set_on_settings(self, callback: Callable) -> None:
        """Set settings callback."""
        self._on_settings_callback = callback
    
    def set_on_detail(self, callback: Callable) -> None:
        """Set detail window callback."""
        self._on_detail_callback = callback
    
    def set_on_about(self, callback: Callable) -> None:
        """Set about callback."""
        self._on_about_callback = callback
    
    def set_on_refresh(self, callback: Callable) -> None:
        """Set refresh callback."""
        self._on_refresh_callback = callback
    
    def set_on_pause(self, callback: Callable) -> None:
        """Set pause callback."""
        self._on_pause_callback = callback
    
    def set_on_auto_start(self, callback: Callable) -> None:
        """Set auto start callback."""
        self._on_auto_start_callback = callback
    
    def set_on_exit(self, callback: Callable) -> None:
        """Set exit callback."""
        self._on_exit_callback = callback

    
    def set_on_menu_open(self, callback: Callable) -> None:
        """Set menu open callback (called when tray menu opens)."""
        self._on_menu_open_callback = callback
    
    def set_on_menu_close(self, callback: Callable) -> None:
        """Set menu close callback (called when tray menu closes)."""
        self._on_menu_close_callback = callback
    
    def _on_menu_close(self, event) -> None:
        """Handle menu close event."""
        if self._on_menu_close_callback:
            try:
                wx.CallLater(200, self._on_menu_close_callback)
            except Exception as e:
                self._logger.error(f"Error in menu close callback: {e}")
        event.Skip()

