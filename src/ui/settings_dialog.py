"""
Settings dialog for managing ETF list and configuration parameters.

Provides user-friendly interface for all configuration options.
"""

from typing import Dict

import wx

from ..config.manager import ConfigManager
from ..config.validator import ConfigValidator
from ..utils.logger import get_logger
from ..utils.helpers import validate_etf_code


class SettingsDialog(wx.Dialog):
    """
    Settings dialog with ETF management and parameter configuration.
    
    Layout (600x500):
    - ETF list management (add, delete, clear)
    - Refresh interval slider
    - Rotation interval slider
    - Rotation mode radio buttons
    - Auto start checkbox
    - Save/Cancel/Reset buttons
    """
    
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
            size=(820, 760),
            style=wx.DEFAULT_DIALOG_STYLE
        )
        
        self._config = config_manager
        self._fetch_name_callback = fetch_name_callback
        self._logger = get_logger(__name__)
        self._etf_name_cache: Dict[str, str] = {}
        
        # Create UI
        self._create_ui()
        
        # Load current settings
        self._load_settings()
        
        self.Centre()
    
    def _create_ui(self) -> None:
        """Create user interface."""
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # ETF List Section
        etf_box = wx.StaticBox(panel, label="我的自选 ETF")
        etf_sizer = wx.StaticBoxSizer(etf_box, wx.VERTICAL)
        
        # ETF List Control
        self._etf_list = wx.ListCtrl(
            panel,
            size=(-1, 380),
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN
        )
        self._etf_list.SetMinSize((-1, 360))
        self._etf_list.InsertColumn(0, "代码", width=150)
        self._etf_list.InsertColumn(1, "名称", width=260)
        self._etf_list.InsertColumn(2, "备注", width=260)
        
        etf_sizer.Add(self._etf_list, 1, wx.EXPAND | wx.ALL, 5)
        
        # Add/Delete buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self._code_input = wx.TextCtrl(panel, size=(140, -1))
        self._code_input.SetHint("输入代码")
        btn_sizer.Add(self._code_input, 0, wx.ALL, 2)
        
        self._add_btn = wx.Button(panel, label="添加")
        self._add_btn.Bind(wx.EVT_BUTTON, self._on_add_etf)
        btn_sizer.Add(self._add_btn, 0, wx.ALL, 2)
        
        self._delete_btn = wx.Button(panel, label="删除")
        self._delete_btn.Bind(wx.EVT_BUTTON, self._on_delete_etf)
        btn_sizer.Add(self._delete_btn, 0, wx.ALL, 2)
        
        self._clear_btn = wx.Button(panel, label="清空")
        self._clear_btn.Bind(wx.EVT_BUTTON, self._on_clear_etf)
        btn_sizer.Add(self._clear_btn, 0, wx.ALL, 2)
        
        etf_sizer.Add(btn_sizer, 0, wx.ALL, 5)
        
        main_sizer.Add(etf_sizer, 2, wx.EXPAND | wx.ALL, 10)
        
        # Refresh Settings Section
        refresh_box = wx.StaticBox(panel, label="刷新设置")
        refresh_sizer = wx.StaticBoxSizer(refresh_box, wx.VERTICAL)
        
        # Refresh interval slider
        refresh_label = wx.StaticText(panel, label="数据刷新间隔：")
        refresh_sizer.Add(refresh_label, 0, wx.ALL, 5)
        
        refresh_slider_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._refresh_slider = wx.Slider(
            panel, value=5, minValue=3, maxValue=30,
            style=wx.SL_HORIZONTAL | wx.SL_LABELS
        )
        refresh_slider_sizer.Add(self._refresh_slider, 1, wx.EXPAND | wx.ALL, 2)
        refresh_slider_sizer.Add(wx.StaticText(panel, label="秒"), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        refresh_sizer.Add(refresh_slider_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # Rotation interval slider
        rotation_label = wx.StaticText(panel, label="托盘轮播间隔：")
        refresh_sizer.Add(rotation_label, 0, wx.ALL, 5)
        
        rotation_slider_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._rotation_slider = wx.Slider(
            panel, value=3, minValue=1, maxValue=60,
            style=wx.SL_HORIZONTAL | wx.SL_LABELS
        )
        rotation_slider_sizer.Add(self._rotation_slider, 1, wx.EXPAND | wx.ALL, 2)
        rotation_slider_sizer.Add(wx.StaticText(panel, label="秒"), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        refresh_sizer.Add(rotation_slider_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # Rotation mode radio buttons
        mode_label = wx.StaticText(panel, label="轮播模式：")
        refresh_sizer.Add(mode_label, 0, wx.ALL, 5)
        
        self._rotation_mode = wx.RadioBox(
            panel,
            choices=["定时轮播", "价格变化时", "两者都"],
            style=wx.RA_SPECIFY_ROWS
        )
        refresh_sizer.Add(self._rotation_mode, 0, wx.ALL, 5)
        
        main_sizer.Add(refresh_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # Other Options Section
        other_box = wx.StaticBox(panel, label="其他选项")
        other_sizer = wx.StaticBoxSizer(other_box, wx.VERTICAL)
        
        self._auto_start_cb = wx.CheckBox(panel, label="开机自动启动")
        other_sizer.Add(self._auto_start_cb, 0, wx.ALL, 5)
        
        main_sizer.Add(other_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        save_btn = wx.Button(panel, wx.ID_OK, "保存")
        save_btn.Bind(wx.EVT_BUTTON, self._on_save)
        btn_sizer.Add(save_btn, 0, wx.ALL, 5)
        
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "取消")
        btn_sizer.Add(cancel_btn, 0, wx.ALL, 5)
        
        reset_btn = wx.Button(panel, label="恢复默认")
        reset_btn.Bind(wx.EVT_BUTTON, self._on_reset)
        btn_sizer.Add(reset_btn, 0, wx.ALL, 5)
        
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        panel.SetSizer(main_sizer)
    
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
            index = self._etf_list.InsertItem(self._etf_list.GetItemCount(), code)
            self._etf_list.SetItem(index, 1, self._get_etf_display_name(code))
            self._etf_list.SetItem(index, 2, "")
        
        # Load refresh interval
        refresh_interval = self._config.get('refresh_interval', 5)
        self._refresh_slider.SetValue(refresh_interval)
        
        # Load rotation interval
        rotation_interval = self._config.get('rotation_interval', 3)
        self._rotation_slider.SetValue(rotation_interval)
        
        # Load rotation mode
        rotation_mode = self._config.get('rotation_mode', 'both')
        mode_map = {'timer': 0, 'change': 1, 'both': 2}
        self._rotation_mode.SetSelection(mode_map.get(rotation_mode, 2))
        
        # Load auto start
        auto_start = self._config.get('auto_start', False)
        self._auto_start_cb.SetValue(auto_start)
    
    def _on_add_etf(self, event) -> None:
        """Handle add ETF button."""
        code = self._code_input.GetValue().strip()
        
        # Validate code
        if not validate_etf_code(code):
            wx.MessageBox(
                "ETF 代码必须是6位数字",
                "输入错误",
                wx.OK | wx.ICON_ERROR
            )
            return
        
        # Check if already exists
        for i in range(self._etf_list.GetItemCount()):
            if self._etf_list.GetItemText(i, 0) == code:
                wx.MessageBox(
                    f"ETF {code} 已经存在",
                    "重复添加",
                    wx.OK | wx.ICON_WARNING
                )
                return
        
        # Fetch name from API if callback provided
        name = self._get_etf_display_name(code)
        
        # Add to list
        index = self._etf_list.InsertItem(self._etf_list.GetItemCount(), code)
        self._etf_list.SetItem(index, 1, name)
        self._etf_list.SetItem(index, 2, "")
        
        # Clear input
        self._code_input.Clear()
        
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
            self._etf_list.DeleteItem(selected)
            self._logger.info(f"Deleted ETF: {code}")
    
    def _on_clear_etf(self, event) -> None:
        """Handle clear ETF button."""
        if self._etf_list.GetItemCount() == 0:
            return
        
        if wx.MessageBox(
            "确定要清空所有 ETF 吗？",
            "确认清空",
            wx.YES_NO | wx.ICON_QUESTION
        ) == wx.YES:
            self._etf_list.DeleteAllItems()
            self._logger.info("Cleared all ETFs")
    
    def _on_save(self, event) -> None:
        """Handle save button."""
        # Collect ETF codes
        etf_codes = []
        for i in range(self._etf_list.GetItemCount()):
            code = self._etf_list.GetItemText(i, 0)
            etf_codes.append(code)
        
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
        refresh_interval = self._refresh_slider.GetValue()
        rotation_interval = self._rotation_slider.GetValue()
        
        mode_map = {0: 'timer', 1: 'change', 2: 'both'}
        rotation_mode = mode_map[self._rotation_mode.GetSelection()]
        
        auto_start = self._auto_start_cb.GetValue()
        
        # Update configuration
        self._config.set('etf_list', etf_codes)
        self._config.set('refresh_interval', refresh_interval)
        self._config.set('rotation_interval', rotation_interval)
        self._config.set('rotation_mode', rotation_mode)
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
    
    def _on_reset(self, event) -> None:
        """Handle reset button."""
        if wx.MessageBox(
            "确定要恢复默认设置吗？\n所有自选 ETF 和配置将被清空。",
            "确认恢复默认",
            wx.YES_NO | wx.ICON_QUESTION
        ) == wx.YES:
            # Clear ETF list
            self._etf_list.DeleteAllItems()
            
            # Reset sliders
            self._refresh_slider.SetValue(5)
            self._rotation_slider.SetValue(3)
            
            # Reset rotation mode
            self._rotation_mode.SetSelection(2)  # both
            
            # Reset auto start
            self._auto_start_cb.SetValue(False)
            
            self._logger.info("Settings reset to defaults")

