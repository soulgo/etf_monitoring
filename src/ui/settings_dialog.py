"""
Settings dialog for managing ETF list and configuration parameters.

Modern flat design with left navigation and right content panels.
Provides user-friendly interface for all configuration options.
"""

from typing import Dict, Optional, List, Tuple
import json

import wx
import httpx

from ..config.manager import ConfigManager
from ..config.validator import ConfigValidator
from ..utils.logger import get_logger
from ..utils.helpers import validate_etf_code


class ETFSearchPopup(wx.PopupWindow):
    """
    ETF search results popup window.
    
    Displays search results with code, name, and add button for each result.
    """
    
    def __init__(self, parent, on_add_callback):
        """
        Initialize search popup.
        
        Args:
            parent: Parent window
            on_add_callback: Callback function when adding ETF (code, name)
        """
        super().__init__(parent, wx.BORDER_SIMPLE)
        
        self._parent = parent
        self._on_add_callback = on_add_callback
        self._logger = get_logger(__name__)
        self._result_panels = []
        
        # Create UI - match search box width (300px)
        popup_width = 300
        popup_height = 250
        
        self._panel = wx.Panel(self, size=(popup_width, popup_height))
        self._panel.SetBackgroundColour(wx.WHITE)
        
        self._main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Scrolled window for results
        self._scrolled = wx.ScrolledWindow(
            self._panel,
            style=wx.VSCROLL | wx.BORDER_NONE,
            size=(popup_width, popup_height)
        )
        self._scrolled.SetScrollRate(0, 10)
        self._scrolled.SetBackgroundColour(wx.WHITE)
        
        self._results_sizer = wx.BoxSizer(wx.VERTICAL)
        self._scrolled.SetSizer(self._results_sizer)
        
        self._main_sizer.Add(self._scrolled, 1, wx.EXPAND)
        self._panel.SetSizer(self._main_sizer)
        
        # Set fixed size for popup
        self.SetSize((popup_width, popup_height))
        self.SetMinSize((popup_width, popup_height))
        
        # Bind events
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)
    
    def show_results(self, results: List[Tuple[str, str]], existing_codes: set) -> None:
        """
        Show search results.
        
        Args:
            results: List of (code, name) tuples
            existing_codes: Set of existing ETF codes
        """
        print(f"[DEBUG] show_results called with {len(results)} results")
        
        # Clear previous results
        self._results_sizer.Clear(True)
        self._result_panels = []
        
        if not results:
            # Show no results message
            no_result_text = wx.StaticText(
                self._scrolled,
                label="未找到匹配的 ETF"
            )
            no_result_text.SetForegroundColour(wx.Colour(128, 128, 128))
            self._results_sizer.Add(no_result_text, 0, wx.ALL, 10)
        else:
            # Add each result
            for code, name in results:
                print(f"[DEBUG] Adding result: {code} - {name}")
                result_panel = self._create_result_item(code, name, code in existing_codes)
                self._result_panels.append(result_panel)
                self._results_sizer.Add(result_panel, 0, wx.EXPAND)
                
                # Add separator
                sep = wx.Panel(self._scrolled, size=(-1, 1))
                sep.SetBackgroundColour(wx.Colour(230, 230, 230))
                self._results_sizer.Add(sep, 0, wx.EXPAND)
        
        self._scrolled.SetSizer(self._results_sizer)
        self._scrolled.FitInside()
        self._scrolled.Layout()
        self._panel.Layout()
        self.Layout()
        
        print(f"[DEBUG] Popup layout completed")
    
    def _create_result_item(self, code: str, name: str, is_existing: bool) -> wx.Panel:
        """Create a result item panel."""
        panel = wx.Panel(self._scrolled, size=(280, 45))
        panel.SetBackgroundColour(wx.WHITE)
        panel.SetMinSize((280, 45))
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Code
        code_text = wx.StaticText(panel, label=code)
        code_font = code_text.GetFont()
        code_font.SetWeight(wx.FONTWEIGHT_BOLD)
        code_font.SetPointSize(9)
        code_text.SetFont(code_font)
        sizer.Add(code_text, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 8)
        
        # Name (truncate if too long)
        display_name = name if len(name) <= 10 else name[:10] + "..."
        name_text = wx.StaticText(panel, label=display_name)
        name_font = name_text.GetFont()
        name_font.SetPointSize(9)
        name_text.SetFont(name_font)
        sizer.Add(name_text, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 8)
        
        # Add button or checkmark
        if is_existing:
            check_text = wx.StaticText(panel, label="✓")
            check_text.SetForegroundColour(wx.Colour(0, 150, 0))
            check_font = check_text.GetFont()
            check_font.SetPointSize(12)
            check_font.SetWeight(wx.FONTWEIGHT_BOLD)
            check_text.SetFont(check_font)
            sizer.Add(check_text, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 8)
        else:
            add_btn = wx.Button(panel, label="+", size=(28, 28))
            add_btn.SetBackgroundColour(wx.Colour(0, 120, 212))
            add_btn.SetForegroundColour(wx.WHITE)
            add_btn_font = add_btn.GetFont()
            add_btn_font.SetPointSize(12)
            add_btn_font.SetWeight(wx.FONTWEIGHT_BOLD)
            add_btn.SetFont(add_btn_font)
            add_btn.Bind(wx.EVT_BUTTON, lambda e, c=code, n=name: self._on_add_clicked(c, n))
            sizer.Add(add_btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 8)
        
        # Hover effect
        panel.Bind(wx.EVT_ENTER_WINDOW, lambda e: panel.SetBackgroundColour(wx.Colour(245, 245, 245)) or panel.Refresh())
        panel.Bind(wx.EVT_LEAVE_WINDOW, lambda e: panel.SetBackgroundColour(wx.WHITE) or panel.Refresh())
        
        panel.SetSizer(sizer)
        panel.Layout()
        return panel
    
    def _on_add_clicked(self, code: str, name: str) -> None:
        """Handle add button click."""
        if self._on_add_callback:
            self._on_add_callback(code, name)
    
    def _on_key_down(self, event) -> None:
        """Handle key down event."""
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Hide()
        else:
            event.Skip()
    
    def position_below(self, widget: wx.Window) -> None:
        """Position popup below the given widget."""
        pos = widget.GetScreenPosition()
        size = widget.GetSize()
        self.SetPosition((pos.x, pos.y + size.height))


class SettingsDialog(wx.Dialog):
    """
    Settings dialog with modern flat design and left navigation.
    
    Layout (900x600):
    - Left navigation panel (180px): Category selection
    - Right content panel: Dynamic content based on selection
    - Bottom buttons: Save/Cancel/Reset
    
    Categories:
    - 基金管理: ETF list management
    - 刷新设置: Refresh and rotation settings
    - 其他选项: Auto-start and misc options
    - 关于: About information
    """
    
    # Color scheme - Windows 11 inspired
    COLOR_NAV_BG = wx.Colour(245, 245, 245)  # #F5F5F5
    COLOR_NAV_SELECTED = wx.Colour(227, 227, 227)  # #E3E3E3
    COLOR_NAV_HOVER = wx.Colour(235, 235, 235)  # #EBEBEB
    COLOR_CONTENT_BG = wx.Colour(255, 255, 255)  # #FFFFFF
    COLOR_ACCENT = wx.Colour(0, 120, 212)  # #0078D4
    COLOR_TEXT = wx.Colour(0, 0, 0)
    COLOR_TEXT_SECONDARY = wx.Colour(96, 96, 96)
    COLOR_SEPARATOR = wx.Colour(225, 225, 225)
    
    def __init__(self, parent, config_manager: ConfigManager, fetch_name_callback=None):
        """
        Initialize settings dialog.
        
        Args:
            parent: Parent window
            config_manager: Configuration manager instance
            fetch_name_callback: Callback to fetch ETF name from API (receives code, returns name)
        """
        super().__init__(
            parent,
            title="ETF 监控工具 - 设置",
            size=(900, 600),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        
        self._config = config_manager
        self._fetch_name_callback = fetch_name_callback
        self._logger = get_logger(__name__)
        self._etf_name_cache: Dict[str, str] = {}
        
        # Navigation state
        self._current_panel = 0
        self._nav_buttons = []
        
        # Panels
        self._content_panels = []
        
        # Store all ETF data for search filtering
        self._all_etf_items = []  # Store (code, name, remark) tuples
        
        # Search popup
        self._search_popup = None
        
        # Create UI
        self._create_ui()
        
        # Create search popup after UI is created
        self._search_popup = ETFSearchPopup(self, self._on_search_add_etf)
        
        # Load current settings
        self._load_settings()
        
        self.Centre()
        
        # Bind global click handler to close popup
        self.Bind(wx.EVT_LEFT_DOWN, self._on_dialog_click)
    
    def _create_ui(self) -> None:
        """Create user interface with left navigation and right content."""
        main_panel = wx.Panel(self)
        main_panel.SetBackgroundColour(self.COLOR_CONTENT_BG)
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Left navigation panel
        nav_panel = self._create_navigation_panel(main_panel)
        main_sizer.Add(nav_panel, 0, wx.EXPAND)
        
        # Vertical separator
        separator = wx.Panel(main_panel, size=(1, -1))
        separator.SetBackgroundColour(self.COLOR_SEPARATOR)
        main_sizer.Add(separator, 0, wx.EXPAND)
        
        # Right content panel container
        self._content_container = wx.Panel(main_panel)
        self._content_container.SetBackgroundColour(self.COLOR_CONTENT_BG)
        content_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Create all content panels
        self._create_fund_panel(self._content_container, content_sizer)
        self._create_refresh_panel(self._content_container, content_sizer)
        self._create_other_panel(self._content_container, content_sizer)
        self._create_about_panel(self._content_container, content_sizer)
        
        self._content_container.SetSizer(content_sizer)
        main_sizer.Add(self._content_container, 1, wx.EXPAND)
        
        # Bottom buttons panel
        button_panel = self._create_button_panel(main_panel)
        
        # Main layout
        outer_sizer = wx.BoxSizer(wx.VERTICAL)
        outer_sizer.Add(main_sizer, 1, wx.EXPAND)
        
        # Horizontal separator above buttons
        h_separator = wx.Panel(main_panel, size=(-1, 1))
        h_separator.SetBackgroundColour(self.COLOR_SEPARATOR)
        outer_sizer.Add(h_separator, 0, wx.EXPAND)
        
        outer_sizer.Add(button_panel, 0, wx.EXPAND | wx.ALL, 15)
        
        main_panel.SetSizer(outer_sizer)
        
        # Show first panel by default
        self._switch_panel(0)
    
    def _create_navigation_panel(self, parent) -> wx.Panel:
        """Create left navigation panel."""
        nav_panel = wx.Panel(parent, size=(180, -1))
        nav_panel.SetBackgroundColour(self.COLOR_NAV_BG)
        nav_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Navigation items
        nav_items = [
            ("基金管理", "管理自选 ETF 列表"),
            ("刷新设置", "配置刷新和轮播参数"),
            ("其他选项", "开机自启动等设置"),
            ("关于", "版本和软件信息")
        ]
        
        nav_sizer.AddSpacer(10)
        
        for idx, (title, desc) in enumerate(nav_items):
            btn = self._create_nav_button(nav_panel, title, desc, idx)
            self._nav_buttons.append(btn)
            nav_sizer.Add(btn, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        
        nav_panel.SetSizer(nav_sizer)
        return nav_panel
    
    def _create_nav_button(self, parent, title: str, desc: str, index: int) -> wx.Panel:
        """Create a navigation button."""
        btn_panel = wx.Panel(parent)
        btn_panel.SetBackgroundColour(self.COLOR_NAV_BG)
        btn_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title_label = wx.StaticText(btn_panel, label=title)
        title_font = title_label.GetFont()
        title_font.SetPointSize(10)
        title_font.SetWeight(wx.FONTWEIGHT_SEMIBOLD)
        title_label.SetFont(title_font)
        btn_sizer.Add(title_label, 0, wx.ALL, 8)
        
        btn_panel.SetSizer(btn_sizer)
        btn_panel.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        
        # Store index for event handling
        btn_panel._nav_index = index
        
        # Bind events
        btn_panel.Bind(wx.EVT_LEFT_DOWN, lambda e: self._on_nav_click(index))
        title_label.Bind(wx.EVT_LEFT_DOWN, lambda e: self._on_nav_click(index))
        btn_panel.Bind(wx.EVT_ENTER_WINDOW, lambda e: self._on_nav_hover(btn_panel, True))
        btn_panel.Bind(wx.EVT_LEAVE_WINDOW, lambda e: self._on_nav_hover(btn_panel, False))
        
        return btn_panel
    
    def _on_nav_hover(self, panel: wx.Panel, entering: bool) -> None:
        """Handle navigation button hover."""
        if panel._nav_index != self._current_panel:
            if entering:
                panel.SetBackgroundColour(self.COLOR_NAV_HOVER)
            else:
                panel.SetBackgroundColour(self.COLOR_NAV_BG)
            panel.Refresh()
    
    def _on_nav_click(self, index: int) -> None:
        """Handle navigation button click."""
        self._switch_panel(index)
    
    def _switch_panel(self, index: int) -> None:
        """Switch to specified content panel."""
        # Update navigation button styles
        for i, btn in enumerate(self._nav_buttons):
            if i == index:
                btn.SetBackgroundColour(self.COLOR_NAV_SELECTED)
            else:
                btn.SetBackgroundColour(self.COLOR_NAV_BG)
            btn.Refresh()
        
        # Show/hide content panels
        for i, panel in enumerate(self._content_panels):
            panel.Show(i == index)
        
        self._current_panel = index
        self._content_container.Layout()
    
    def _create_fund_panel(self, parent, sizer) -> None:
        """Create fund management panel."""
        panel = wx.Panel(parent)
        panel.SetBackgroundColour(self.COLOR_CONTENT_BG)
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title and search bar row
        title_row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Title
        title = wx.StaticText(panel, label="我的自选 ETF")
        title_font = title.GetFont()
        title_font.SetPointSize(14)
        title_font.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        title_row_sizer.Add(title, 0, wx.ALIGN_CENTER_VERTICAL)
        
        title_row_sizer.AddStretchSpacer()
        
        # Search box
        search_label = wx.StaticText(panel, label="搜索：")
        search_label.SetForegroundColour(self.COLOR_TEXT_SECONDARY)
        title_row_sizer.Add(search_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        
        self._search_box = wx.SearchCtrl(panel, size=(250, 28), style=wx.TE_PROCESS_ENTER)
        self._search_box.ShowSearchButton(True)
        self._search_box.ShowCancelButton(True)
        self._search_box.SetHint("输入代码或名称，回车搜索")
        # Bind multiple events to ensure search triggers
        self._search_box.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, self._on_search_enter)  # Click search button
        self._search_box.Bind(wx.EVT_TEXT_ENTER, self._on_search_enter)  # Press Enter
        self._search_box.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self._on_search_cancel)
        title_row_sizer.Add(self._search_box, 0, wx.ALIGN_CENTER_VERTICAL)
        
        panel_sizer.Add(title_row_sizer, 0, wx.EXPAND | wx.ALL, 15)
        
        # Description
        desc = wx.StaticText(panel, label="添加和管理您要监控的 ETF 基金")
        desc.SetForegroundColour(self.COLOR_TEXT_SECONDARY)
        panel_sizer.Add(desc, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)
        
        # ETF List
        self._etf_list = wx.ListCtrl(
            panel,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SIMPLE
        )
        self._etf_list.InsertColumn(0, "代码", width=120)
        self._etf_list.InsertColumn(1, "名称", width=200)
        self._etf_list.InsertColumn(2, "备注", width=240)
        panel_sizer.Add(self._etf_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)
        
        # Button row
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self._add_btn = wx.Button(panel, label="添加", size=(100, 32))
        self._add_btn.SetBackgroundColour(self.COLOR_ACCENT)
        self._add_btn.SetForegroundColour(wx.WHITE)
        self._add_btn.Bind(wx.EVT_BUTTON, self._on_add_etf)
        button_sizer.Add(self._add_btn, 0, wx.RIGHT, 8)
        
        self._delete_btn = wx.Button(panel, label="删除", size=(100, 32))
        self._delete_btn.Bind(wx.EVT_BUTTON, self._on_delete_etf)
        button_sizer.Add(self._delete_btn, 0, wx.RIGHT, 8)
        
        self._clear_btn = wx.Button(panel, label="清空", size=(100, 32))
        self._clear_btn.Bind(wx.EVT_BUTTON, self._on_clear_etf)
        button_sizer.Add(self._clear_btn, 0)
        
        panel_sizer.Add(button_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)
        
        panel.SetSizer(panel_sizer)
        self._content_panels.append(panel)
        sizer.Add(panel, 1, wx.EXPAND)
    
    def _create_refresh_panel(self, parent, sizer) -> None:
        """Create refresh settings panel."""
        panel = wx.Panel(parent)
        panel.SetBackgroundColour(self.COLOR_CONTENT_BG)
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(panel, label="刷新设置")
        title_font = title.GetFont()
        title_font.SetPointSize(14)
        title_font.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        panel_sizer.Add(title, 0, wx.ALL, 15)
        
        # Description
        desc = wx.StaticText(panel, label="配置数据刷新频率和托盘轮播行为")
        desc.SetForegroundColour(self.COLOR_TEXT_SECONDARY)
        panel_sizer.Add(desc, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)
        
        # Content area with proper spacing
        content_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Refresh interval
        refresh_label = wx.StaticText(panel, label="数据刷新间隔")
        refresh_font = refresh_label.GetFont()
        refresh_font.SetWeight(wx.FONTWEIGHT_SEMIBOLD)
        refresh_label.SetFont(refresh_font)
        content_sizer.Add(refresh_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 15)
        
        refresh_desc = wx.StaticText(panel, label="设置从接口获取最新行情的时间间隔（3-30秒）")
        refresh_desc.SetForegroundColour(self.COLOR_TEXT_SECONDARY)
        content_sizer.Add(refresh_desc, 0, wx.LEFT | wx.RIGHT | wx.TOP, 15)
        
        refresh_ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._refresh_slider = wx.Slider(
            panel, value=5, minValue=3, maxValue=30,
            style=wx.SL_HORIZONTAL, size=(300, -1)
        )
        self._refresh_slider.Bind(wx.EVT_SLIDER, self._on_refresh_slider_change)
        refresh_ctrl_sizer.Add(self._refresh_slider, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 15)
        
        self._refresh_value = wx.SpinCtrl(panel, value="5", min=3, max=30, size=(80, 28))
        self._refresh_value.Bind(wx.EVT_SPINCTRL, self._on_refresh_spin_change)
        refresh_ctrl_sizer.Add(self._refresh_value, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        
        refresh_ctrl_sizer.Add(wx.StaticText(panel, label="秒"), 0, wx.ALIGN_CENTER_VERTICAL)
        
        content_sizer.Add(refresh_ctrl_sizer, 0, wx.ALL, 15)
        
        # Separator
        sep1 = wx.Panel(panel, size=(-1, 1))
        sep1.SetBackgroundColour(self.COLOR_SEPARATOR)
        content_sizer.Add(sep1, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 10)
        
        # Rotation interval
        rotation_label = wx.StaticText(panel, label="托盘轮播间隔")
        rotation_label.SetFont(refresh_font)
        content_sizer.Add(rotation_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 15)
        
        rotation_desc = wx.StaticText(panel, label="设置托盘图标提示信息切换的时间间隔（1-60秒）")
        rotation_desc.SetForegroundColour(self.COLOR_TEXT_SECONDARY)
        content_sizer.Add(rotation_desc, 0, wx.LEFT | wx.RIGHT | wx.TOP, 15)
        
        rotation_ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._rotation_slider = wx.Slider(
            panel, value=3, minValue=1, maxValue=60,
            style=wx.SL_HORIZONTAL, size=(300, -1)
        )
        self._rotation_slider.Bind(wx.EVT_SLIDER, self._on_rotation_slider_change)
        rotation_ctrl_sizer.Add(self._rotation_slider, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 15)
        
        self._rotation_value = wx.SpinCtrl(panel, value="3", min=1, max=60, size=(80, 28))
        self._rotation_value.Bind(wx.EVT_SPINCTRL, self._on_rotation_spin_change)
        rotation_ctrl_sizer.Add(self._rotation_value, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        
        rotation_ctrl_sizer.Add(wx.StaticText(panel, label="秒"), 0, wx.ALIGN_CENTER_VERTICAL)
        
        content_sizer.Add(rotation_ctrl_sizer, 0, wx.ALL, 15)
        
        # Separator
        sep2 = wx.Panel(panel, size=(-1, 1))
        sep2.SetBackgroundColour(self.COLOR_SEPARATOR)
        content_sizer.Add(sep2, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 10)
        
        # Rotation mode
        mode_label = wx.StaticText(panel, label="轮播触发模式")
        mode_label.SetFont(refresh_font)
        content_sizer.Add(mode_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 15)
        
        mode_desc = wx.StaticText(panel, label="选择何时切换托盘显示的 ETF")
        mode_desc.SetForegroundColour(self.COLOR_TEXT_SECONDARY)
        content_sizer.Add(mode_desc, 0, wx.LEFT | wx.RIGHT | wx.TOP, 15)
        
        self._rotation_mode = wx.RadioBox(
            panel,
            choices=["定时轮播", "价格变化时", "两者都"],
            style=wx.RA_SPECIFY_COLS,
            majorDimension=3
        )
        content_sizer.Add(self._rotation_mode, 0, wx.ALL, 15)
        
        panel_sizer.Add(content_sizer, 0, wx.EXPAND)
        
        panel.SetSizer(panel_sizer)
        self._content_panels.append(panel)
        sizer.Add(panel, 1, wx.EXPAND)
    
    def _create_other_panel(self, parent, sizer) -> None:
        """Create other options panel."""
        panel = wx.Panel(parent)
        panel.SetBackgroundColour(self.COLOR_CONTENT_BG)
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(panel, label="其他选项")
        title_font = title.GetFont()
        title_font.SetPointSize(14)
        title_font.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        panel_sizer.Add(title, 0, wx.ALL, 15)
        
        # Description
        desc = wx.StaticText(panel, label="启动行为和其他杂项设置")
        desc.SetForegroundColour(self.COLOR_TEXT_SECONDARY)
        panel_sizer.Add(desc, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)
        
        # Floating window display control
        floating_label = wx.StaticText(panel, label="悬浮窗显示")
        floating_font = floating_label.GetFont()
        floating_font.SetWeight(wx.FONTWEIGHT_SEMIBOLD)
        floating_label.SetFont(floating_font)
        panel_sizer.Add(floating_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 15)
        
        self._floating_window_cb = wx.CheckBox(panel, label="显示右下角悬浮窗")
        panel_sizer.Add(self._floating_window_cb, 0, wx.ALL, 15)
        
        # Auto start
        auto_start_label = wx.StaticText(panel, label="开机启动")
        auto_font = auto_start_label.GetFont()
        auto_font.SetWeight(wx.FONTWEIGHT_SEMIBOLD)
        auto_start_label.SetFont(auto_font)
        panel_sizer.Add(auto_start_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 15)
        
        self._auto_start_cb = wx.CheckBox(panel, label="开机自动启动 ETF 监控工具")
        panel_sizer.Add(self._auto_start_cb, 0, wx.ALL, 15)
        
        panel.SetSizer(panel_sizer)
        self._content_panels.append(panel)
        sizer.Add(panel, 1, wx.EXPAND)
    
    def _create_about_panel(self, parent, sizer) -> None:
        """Create about information panel."""
        panel = wx.Panel(parent)
        panel.SetBackgroundColour(self.COLOR_CONTENT_BG)
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(panel, label="关于")
        title_font = title.GetFont()
        title_font.SetPointSize(14)
        title_font.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        panel_sizer.Add(title, 0, wx.ALL, 15)
        
        # App name and version
        app_name = wx.StaticText(panel, label="ETF 监控工具")
        app_font = app_name.GetFont()
        app_font.SetPointSize(16)
        app_font.SetWeight(wx.FONTWEIGHT_BOLD)
        app_name.SetFont(app_font)
        panel_sizer.Add(app_name, 0, wx.LEFT | wx.RIGHT | wx.TOP, 15)
        
        version = wx.StaticText(panel, label="版本 1.0.0")
        version.SetForegroundColour(self.COLOR_TEXT_SECONDARY)
        panel_sizer.Add(version, 0, wx.LEFT | wx.RIGHT | wx.TOP, 15)
        
        panel_sizer.AddSpacer(20)
        
        # Description
        desc_lines = [
            "一个轻量级的 Windows 桌面应用",
            "用于实时监控自选 ETF 的价格变化",
            "",
            "特性：",
            "• 实时行情监控",
            "• 系统托盘轮播显示",
            "• 右下角悬浮窗",
            "• 智能轮播模式",
            "• 主备接口自动切换",
        ]
        
        for line in desc_lines:
            if line.startswith("•"):
                label = wx.StaticText(panel, label=line)
            else:
                label = wx.StaticText(panel, label=line)
                if line and not line.endswith("："):
                    label.SetForegroundColour(self.COLOR_TEXT_SECONDARY)
            panel_sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 15)
        
        panel_sizer.AddSpacer(20)
        
        # Copyright
        copyright = wx.StaticText(panel, label="© 2025 ETF Monitor. All rights reserved.")
        copyright.SetForegroundColour(self.COLOR_TEXT_SECONDARY)
        copyright_font = copyright.GetFont()
        copyright_font.SetPointSize(8)
        copyright.SetFont(copyright_font)
        panel_sizer.Add(copyright, 0, wx.LEFT | wx.RIGHT | wx.TOP, 15)
        
        panel.SetSizer(panel_sizer)
        self._content_panels.append(panel)
        sizer.Add(panel, 1, wx.EXPAND)
    
    def _create_button_panel(self, parent) -> wx.Panel:
        """Create bottom button panel."""
        button_panel = wx.Panel(parent)
        button_panel.SetBackgroundColour(self.COLOR_CONTENT_BG)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        button_sizer.AddStretchSpacer()
        
        # Reset button (left aligned)
        reset_btn = wx.Button(button_panel, label="恢复默认", size=(100, 32))
        reset_btn.Bind(wx.EVT_BUTTON, self._on_reset)
        button_sizer.Add(reset_btn, 0, wx.RIGHT, 10)
        
        button_sizer.AddStretchSpacer()
        
        # Cancel button
        cancel_btn = wx.Button(button_panel, wx.ID_CANCEL, "取消", size=(100, 32))
        cancel_btn.Bind(wx.EVT_BUTTON, self._on_cancel)
        button_sizer.Add(cancel_btn, 0, wx.RIGHT, 10)
        
        # Save button (accent color)
        save_btn = wx.Button(button_panel, wx.ID_OK, "保存", size=(100, 32))
        save_btn.SetBackgroundColour(self.COLOR_ACCENT)
        save_btn.SetForegroundColour(wx.WHITE)
        save_btn.Bind(wx.EVT_BUTTON, self._on_save)
        button_sizer.Add(save_btn, 0)
        
        button_panel.SetSizer(button_sizer)
        return button_panel
    
    def _on_refresh_slider_change(self, event) -> None:
        """Handle refresh slider change."""
        value = self._refresh_slider.GetValue()
        self._refresh_value.SetValue(value)
    
    def _on_refresh_spin_change(self, event) -> None:
        """Handle refresh spin control change."""
        value = self._refresh_value.GetValue()
        self._refresh_slider.SetValue(value)
    
    def _on_rotation_slider_change(self, event) -> None:
        """Handle rotation slider change."""
        value = self._rotation_slider.GetValue()
        self._rotation_value.SetValue(value)
    
    def _on_rotation_spin_change(self, event) -> None:
        """Handle rotation spin control change."""
        value = self._rotation_value.GetValue()
        self._rotation_slider.SetValue(value)
    
    def _get_etf_display_name(self, code: str) -> str:
        """Return display name for ETF code, with optional API lookup."""
        if code in self._etf_name_cache:
            return self._etf_name_cache[code]

        name = f"ETF{code}"
        if self._fetch_name_callback:
            try:
                fetched_name = self._fetch_name_callback(code)
                if fetched_name:
                    name = fetched_name
            except Exception as e:
                self._logger.warning(f"Failed to fetch name for {code}: {e}")

        self._etf_name_cache[code] = name
        return name

    def _load_settings(self) -> None:
        """Load current settings from configuration."""
        # Load ETF list
        etf_list = self._config.get('etf_list', [])
        for code in etf_list:
            name = self._get_etf_display_name(code)
            remark = ""
            self._all_etf_items.append((code, name, remark))
            index = self._etf_list.InsertItem(self._etf_list.GetItemCount(), code)
            self._etf_list.SetItem(index, 1, name)
            self._etf_list.SetItem(index, 2, remark)
        
        # Load refresh interval
        refresh_interval = self._config.get('refresh_interval', 5)
        self._refresh_slider.SetValue(refresh_interval)
        self._refresh_value.SetValue(refresh_interval)
        
        # Load rotation interval
        rotation_interval = self._config.get('rotation_interval', 3)
        self._rotation_slider.SetValue(rotation_interval)
        self._rotation_value.SetValue(rotation_interval)
        
        # Load rotation mode
        rotation_mode = self._config.get('rotation_mode', 'both')
        mode_map = {'timer': 0, 'change': 1, 'both': 2}
        self._rotation_mode.SetSelection(mode_map.get(rotation_mode, 2))
        
        # Load floating window enabled state
        floating_enabled = self._config.get('floating_window.enabled', True)
        self._floating_window_cb.SetValue(floating_enabled)
        
        # Load auto start
        auto_start = self._config.get('auto_start', False)
        self._auto_start_cb.SetValue(auto_start)
    
    def _on_add_etf(self, event) -> None:
        """Handle add ETF button - opens dialog to input code."""
        # Create input dialog
        dlg = wx.TextEntryDialog(
            self,
            "请输入 ETF 代码（6位数字）：",
            "添加 ETF",
            ""
        )
        
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        
        code = dlg.GetValue().strip()
        dlg.Destroy()
        
        # Validate code
        if not validate_etf_code(code):
            wx.MessageBox(
                "ETF 代码必须是6位数字",
                "输入错误",
                wx.OK | wx.ICON_ERROR
            )
            return
        
        # Check if already exists in stored data
        if any(item[0] == code for item in self._all_etf_items):
                wx.MessageBox(
                    f"ETF {code} 已经存在",
                    "重复添加",
                    wx.OK | wx.ICON_WARNING
                )
                return
        
        # Fetch name from API if callback provided
        name = self._get_etf_display_name(code)
        remark = ""
        
        # Add to stored data
        self._all_etf_items.append((code, name, remark))
        
        # Refresh the list view (respecting current search filter)
        self._refresh_etf_list()
        
        self._logger.info(f"Added ETF: {code} - {name}")
    
    def _on_delete_etf(self, event) -> None:
        """Handle delete ETF button."""
        selected = self._etf_list.GetFirstSelected()
        if selected == -1:
            wx.MessageBox(
                "请先选择要删除的 ETF",
                "未选择",
                wx.OK | wx.ICON_WARNING
            )
            return
        
        code = self._etf_list.GetItemText(selected, 0)
        
        # Confirm deletion
        if wx.MessageBox(
            f"确定要删除 {code} 吗？",
            "确认删除",
            wx.YES_NO | wx.ICON_QUESTION
        ) == wx.YES:
            # Remove from stored data
            self._all_etf_items = [item for item in self._all_etf_items if item[0] != code]
            
            # Refresh the list view
            self._refresh_etf_list()
            
            self._logger.info(f"Deleted ETF: {code}")
    
    def _on_clear_etf(self, event) -> None:
        """Handle clear ETF button."""
        if len(self._all_etf_items) == 0:
            return
        
        if wx.MessageBox(
            "确定要清空所有 ETF 吗？",
            "确认清空",
            wx.YES_NO | wx.ICON_QUESTION
        ) == wx.YES:
            self._all_etf_items.clear()
            self._etf_list.DeleteAllItems()
            self._search_box.SetValue("")  # Clear search box
            self._logger.info("Cleared all ETFs")
    
    def _on_save(self, event) -> None:
        """Handle save button."""
        # Collect ETF codes from stored data (not from filtered list)
        etf_codes = [item[0] for item in self._all_etf_items]
        
        # Validate ETF list
        is_valid, error = ConfigValidator.validate_etf_list(etf_codes)
        if not is_valid:
            wx.MessageBox(
                f"ETF 列表验证失败：{error}",
                "验证错误",
                wx.OK | wx.ICON_ERROR
            )
            return
        
        # Get values
        refresh_interval = self._refresh_value.GetValue()
        rotation_interval = self._rotation_value.GetValue()
        
        mode_map = {0: 'timer', 1: 'change', 2: 'both'}
        rotation_mode = mode_map[self._rotation_mode.GetSelection()]
        
        floating_window_enabled = self._floating_window_cb.GetValue()
        auto_start = self._auto_start_cb.GetValue()
        
        # Update configuration
        self._config.set('etf_list', etf_codes)
        self._config.set('refresh_interval', refresh_interval)
        self._config.set('rotation_interval', rotation_interval)
        self._config.set('rotation_mode', rotation_mode)
        self._config.set('floating_window.enabled', floating_window_enabled)
        self._config.set('auto_start', auto_start)
        
        # Save to file
        if self._config.save():
            self._logger.info("Configuration saved successfully")
            self.EndModal(wx.ID_OK)
        else:
            wx.MessageBox(
                "保存配置失败，请查看日志",
                "保存失败",
                wx.OK | wx.ICON_ERROR
            )
    
    def _on_cancel(self, event) -> None:
        """Handle cancel button - close dialog without saving."""
        self._logger.info("Settings dialog cancelled")
        self.EndModal(wx.ID_CANCEL)
    
    def _on_reset(self, event) -> None:
        """Handle reset button."""
        if wx.MessageBox(
            "确定要恢复默认设置吗？\n所有自选 ETF 和配置将被清空。",
            "确认恢复默认",
            wx.YES_NO | wx.ICON_QUESTION
        ) == wx.YES:
            # Clear ETF data
            self._all_etf_items.clear()
            self._etf_list.DeleteAllItems()
            self._search_box.SetValue("")
            
            # Reset sliders
            self._refresh_slider.SetValue(5)
            self._refresh_value.SetValue(5)
            self._rotation_slider.SetValue(3)
            self._rotation_value.SetValue(3)
            
            # Reset rotation mode
            self._rotation_mode.SetSelection(2)  # both
            
            # Reset auto start
            self._auto_start_cb.SetValue(False)
            
            self._logger.info("Settings reset to defaults")

    def _on_search_cancel(self, event) -> None:
        """Handle search cancel button."""
        self._search_box.SetValue("")
        if self._search_popup and self._search_popup.IsShown():
            self._search_popup.Hide()
    
    def _refresh_etf_list(self) -> None:
        """Refresh ETF list - show all items."""
        # Clear current list
        self._etf_list.DeleteAllItems()
        
        # Add all items
        for code, name, remark in self._all_etf_items:
            index = self._etf_list.InsertItem(self._etf_list.GetItemCount(), code)
            self._etf_list.SetItem(index, 1, name)
            self._etf_list.SetItem(index, 2, remark)
    
    def _on_search_enter(self, event) -> None:
        """Handle search box enter key or search button click - trigger online search."""
        keyword = self._search_box.GetValue().strip()
        
        print(f"[DEBUG] Search triggered! Keyword: '{keyword}'")  # Console debug
        self._logger.info(f"=== SEARCH TRIGGERED === Keyword: '{keyword}'")
        
        if not keyword:
            self._logger.info("Empty keyword, hiding popup")
            if self._search_popup:
                self._search_popup.Hide()
            return
        
        # Use a busy cursor to show searching
        busy = wx.BusyCursor()
        
        try:
            # Search ETF online
            self._logger.info(f"Calling search API with keyword: {keyword}")
            print(f"[DEBUG] Calling API...")
            
            results = self._search_etf_online(keyword)
            
            print(f"[DEBUG] API returned: {results}")
            
            if results is not None:
                self._logger.info(f"Search returned {len(results)} results")
                print(f"[DEBUG] Found {len(results)} results")
                
                # Get existing codes
                existing_codes = set(item[0] for item in self._all_etf_items)
                
                # Show results in popup
                self._search_popup.show_results(results, existing_codes)
                self._search_popup.position_below(self._search_box)
                self._search_popup.Show()
                self._logger.info("Search popup shown successfully")
                print("[DEBUG] Popup shown")
            else:
                # Search failed, show error
                self._logger.error("Search API returned None - network error")
                print("[DEBUG] API returned None - error")
                wx.MessageBox(
                    "搜索失败，请检查网络连接或稍后重试",
                    "搜索错误",
                    wx.OK | wx.ICON_WARNING
                )
        except Exception as e:
            self._logger.error(f"Search error: {e}", exc_info=True)
            print(f"[DEBUG] Exception: {e}")
            wx.MessageBox(
                f"搜索出错：{str(e)}",
                "错误",
                wx.OK | wx.ICON_ERROR
            )
        finally:
            del busy
    
    def _search_etf_online(self, keyword: str) -> Optional[List[Tuple[str, str]]]:
        """
        Search ETF online using Eastmoney API.
        
        Args:
            keyword: Search keyword (code or name)
            
        Returns:
            List of (code, name) tuples, or None if failed
        """
        try:
            url = "http://searchapi.eastmoney.com/api/suggest/get"
            params = {
                "input": keyword,
                "type": "14",  # 14 = 基金
                "token": "D43BF722C8E33BDC906FB84D85E326E8",
                "count": "50"
            }
            
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                if data.get("QuotationCodeTable") and data["QuotationCodeTable"].get("Data"):
                    results = []
                    for item in data["QuotationCodeTable"]["Data"]:
                        code = item.get("Code", "")
                        name = item.get("Name", "")
                        
                        # Filter only ETF (code usually 6 digits)
                        if code and name and len(code) == 6 and code.isdigit():
                            # Additional check: ETF names often contain "ETF"
                            if "ETF" in name.upper() or "LOF" in name.upper():
                                results.append((code, name))
                    
                    self._logger.info(f"Found {len(results)} ETF results for '{keyword}'")
                    return results
                else:
                    self._logger.warning(f"No results found for '{keyword}'")
                    return []
                    
        except httpx.TimeoutException:
            self._logger.error(f"Search timeout for '{keyword}'")
            return None
        except Exception as e:
            self._logger.error(f"Search failed for '{keyword}': {e}")
            return None
    
    def _on_search_add_etf(self, code: str, name: str) -> None:
        """
        Handle adding ETF from search results.
        
        Args:
            code: ETF code
            name: ETF name
        """
        # Check if already exists
        if any(item[0] == code for item in self._all_etf_items):
            # Already exists, just refresh popup to show checkmark
            existing_codes = set(item[0] for item in self._all_etf_items)
            
            # Get current search results from popup (we need to store them)
            # For now, just hide the popup and show message
            self._search_popup.Hide()
            wx.MessageBox(
                f"ETF {code} 已经在列表中",
                "提示",
                wx.OK | wx.ICON_INFORMATION
            )
            return
        
        # Add to stored data
        self._all_etf_items.append((code, name, ""))
        
        # Cache the name
        self._etf_name_cache[code] = name
        
        # Refresh the list view
        self._refresh_etf_list()
        
        # Update popup to show checkmark
        existing_codes = set(item[0] for item in self._all_etf_items)
        
        # Re-trigger search to update popup
        keyword = self._search_box.GetValue().strip()
        if keyword:
            results = self._search_etf_online(keyword)
            if results:
                self._search_popup.show_results(results, existing_codes)
        
        self._logger.info(f"Added ETF from search: {code} - {name}")
    
    def _on_dialog_click(self, event) -> None:
        """Handle dialog click to close popup."""
        # Close popup when clicking outside
        if self._search_popup and self._search_popup.IsShown():
            # Check if click is within search box or popup
            mouse_pos = wx.GetMousePosition()
            search_rect = self._search_box.GetScreenRect()
            
            if not search_rect.Contains(mouse_pos):
                popup_rect = self._search_popup.GetScreenRect()
                if not popup_rect.Contains(mouse_pos):
                    self._search_popup.Hide()
        
        event.Skip()
