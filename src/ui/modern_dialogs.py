"""
Modern dialog components with real-time validation and smooth interactions.
"""

import wx
import re
from typing import Optional, Callable
from .design_system import (
    Colors, Typography, Spacing, ComponentStyles,
    apply_button_style, apply_text_style
)


class ModernEditDialog(wx.Dialog):
    """
    Modern edit dialog with real-time validation and smooth interactions.
    
    Features:
    - Real-time input validation
    - Visual feedback for errors
    - Smooth transitions
    - Modern styling
    """
    
    def __init__(self, parent, stock_data: dict):
        super().__init__(
            parent,
            title="编辑股票配置",
            size=(500, 520),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        
        self.stock_data = stock_data
        self.validation_errors = {}
        
        # Set modern background
        self.SetBackgroundColour(Colors.BG_PRIMARY)
        
        # Create UI
        self._create_ui()
        
        # Set minimum size to ensure all fields are visible
        self.SetMinSize((500, 520))
        
        # Center on parent
        self.CenterOnParent()
    
    def _create_ui(self):
        """Create modern dialog UI."""
        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour(Colors.BG_PRIMARY)
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Header section
        header_sizer = self._create_header(self.panel)
        main_sizer.Add(header_sizer, 0, wx.EXPAND | wx.ALL, Spacing.LG)
        
        # Form section
        form_sizer = self._create_form(self.panel)
        main_sizer.Add(form_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, Spacing.LG)
        
        # Button section
        button_sizer = self._create_buttons(self.panel)
        main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, Spacing.LG)
        
        self.panel.SetSizer(main_sizer)
    
    def _create_header(self, parent) -> wx.BoxSizer:
        """Create dialog header."""
        header_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(parent, label="编辑股票配置")
        title.SetFont(Typography.h2())
        title.SetForegroundColour(Colors.TEXT_PRIMARY)
        header_sizer.Add(title, 0, wx.BOTTOM, Spacing.SM)
        
        # Stock info
        code = self.stock_data.get('symbol', '')
        name = self.stock_data.get('name', '')
        info = wx.StaticText(parent, label=f"{name} ({code})")
        info.SetFont(Typography.body())
        info.SetForegroundColour(Colors.TEXT_SECONDARY)
        header_sizer.Add(info, 0)
        
        return header_sizer
    
    def _create_form(self, parent) -> wx.BoxSizer:
        """Create form with validation."""
        form_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Up threshold field
        up_sizer, self.up_ctrl, self.up_error = self._create_field(
            parent,
            "上涨阈值 (%)",
            str(self.stock_data.get('up_threshold', 0.0)),
            "当价格上涨超过此百分比时触发提醒"
        )
        form_sizer.Add(up_sizer, 0, wx.EXPAND | wx.BOTTOM, Spacing.MD)
        
        # Down threshold field
        down_sizer, self.down_ctrl, self.down_error = self._create_field(
            parent,
            "下跌阈值 (%)",
            str(self.stock_data.get('down_threshold', 0.0)),
            "当价格下跌超过此百分比时触发提醒"
        )
        form_sizer.Add(down_sizer, 0, wx.EXPAND | wx.BOTTOM, Spacing.MD)
        
        # Duration field
        dur_sizer, self.dur_ctrl, self.dur_error = self._create_field(
            parent,
            "弹窗时长 (秒)",
            str(self.stock_data.get('duration_secs', 5)),
            "提醒弹窗显示的时长"
        )
        form_sizer.Add(dur_sizer, 0, wx.EXPAND)
        
        # Bind validation events
        self.up_ctrl.Bind(wx.EVT_TEXT, self._on_up_change)
        self.down_ctrl.Bind(wx.EVT_TEXT, self._on_down_change)
        self.dur_ctrl.Bind(wx.EVT_TEXT, self._on_dur_change)
        
        return form_sizer
    
    def _create_field(self, parent, label: str, value: str, hint: str) -> tuple:
        """Create a form field with label, input, and error message."""
        field_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Label
        label_text = wx.StaticText(parent, label=label)
        label_text.SetFont(Typography.body())
        label_text.SetForegroundColour(Colors.TEXT_PRIMARY)
        field_sizer.Add(label_text, 0, wx.BOTTOM, Spacing.XS)
        
        # Input
        input_ctrl = wx.TextCtrl(parent, value=value, size=(-1, 36))
        input_style = ComponentStyles.input_field()
        apply_text_style(input_ctrl, input_style)
        field_sizer.Add(input_ctrl, 0, wx.EXPAND | wx.BOTTOM, Spacing.XS)
        
        # Hint text
        hint_text = wx.StaticText(parent, label=hint)
        hint_text.SetFont(Typography.caption())
        hint_text.SetForegroundColour(Colors.TEXT_HINT)
        field_sizer.Add(hint_text, 0, wx.BOTTOM, Spacing.XS)
        
        # Error message (initially hidden)
        error_text = wx.StaticText(parent, label="")
        error_text.SetFont(Typography.caption())
        error_text.SetForegroundColour(Colors.ERROR)
        error_text.Hide()
        field_sizer.Add(error_text, 0)
        
        return field_sizer, input_ctrl, error_text

    def _create_buttons(self, parent) -> wx.BoxSizer:
        """Create dialog buttons."""
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Spacer
        button_sizer.AddStretchSpacer(1)

        # Cancel button
        self.cancel_btn = wx.Button(parent, wx.ID_CANCEL, "取消", size=(100, 36))
        apply_button_style(self.cancel_btn, ComponentStyles.button_secondary())
        button_sizer.Add(self.cancel_btn, 0, wx.RIGHT, Spacing.SM)

        # OK button
        self.ok_btn = wx.Button(parent, wx.ID_OK, "保存", size=(100, 36))
        apply_button_style(self.ok_btn, ComponentStyles.button_primary())
        button_sizer.Add(self.ok_btn, 0)

        # Bind button events
        self.ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)

        return button_sizer

    def _on_up_change(self, event):
        """Validate up threshold in real-time."""
        value = self.up_ctrl.GetValue()
        error = self._validate_threshold(value, "up_threshold")
        self._show_error(self.up_ctrl, self.up_error, error)

    def _on_down_change(self, event):
        """Validate down threshold in real-time."""
        value = self.down_ctrl.GetValue()
        error = self._validate_threshold(value, "down_threshold")
        self._show_error(self.down_ctrl, self.down_error, error)

    def _on_dur_change(self, event):
        """Validate duration in real-time."""
        value = self.dur_ctrl.GetValue()
        error = self._validate_duration(value)
        self._show_error(self.dur_ctrl, self.dur_error, error)

    def _validate_threshold(self, value: str, field_name: str) -> Optional[str]:
        """
        Validate threshold value.

        Returns:
            Error message if invalid, None if valid
        """
        if not value.strip():
            return "此字段不能为空"

        try:
            num = float(value)
            if num < 0:
                return "阈值不能为负数"
            if num > 100:
                return "阈值不能超过 100%"
            # Clear error
            if field_name in self.validation_errors:
                del self.validation_errors[field_name]
            return None
        except ValueError:
            return "请输入有效的数字"

    def _validate_duration(self, value: str) -> Optional[str]:
        """
        Validate duration value.

        Returns:
            Error message if invalid, None if valid
        """
        if not value.strip():
            return "此字段不能为空"

        try:
            num = int(value)
            if num < 1:
                return "时长至少为 1 秒"
            if num > 60:
                return "时长不能超过 60 秒"
            # Clear error
            if 'duration_secs' in self.validation_errors:
                del self.validation_errors['duration_secs']
            return None
        except ValueError:
            return "请输入有效的整数"

    def _show_error(self, ctrl: wx.TextCtrl, error_label: wx.StaticText, error: Optional[str]):
        """Show or hide error message with visual feedback."""
        if error:
            # Show error
            error_label.SetLabel(error)
            error_label.Show()
            ctrl.SetBackgroundColour(Colors.ERROR_LIGHT)
            ctrl.SetForegroundColour(Colors.ERROR_DARK)
        else:
            # Hide error
            error_label.Hide()
            ctrl.SetBackgroundColour(Colors.WHITE)
            ctrl.SetForegroundColour(Colors.TEXT_PRIMARY)

        # Refresh layout
        ctrl.Refresh()
        self.Layout()

    def _on_ok(self, event):
        """Handle OK button click with validation."""
        # Validate all fields
        up_error = self._validate_threshold(self.up_ctrl.GetValue(), "up_threshold")
        down_error = self._validate_threshold(self.down_ctrl.GetValue(), "down_threshold")
        dur_error = self._validate_duration(self.dur_ctrl.GetValue())

        # Show errors if any
        self._show_error(self.up_ctrl, self.up_error, up_error)
        self._show_error(self.down_ctrl, self.down_error, down_error)
        self._show_error(self.dur_ctrl, self.dur_error, dur_error)

        # If any errors, don't close
        if up_error or down_error or dur_error:
            wx.MessageBox(
                "请修正表单中的错误后再保存",
                "验证失败",
                wx.OK | wx.ICON_WARNING,
                self
            )
            return

        # All valid, close with OK
        self.EndModal(wx.ID_OK)

    def get_values(self) -> dict:
        """Get validated form values."""
        return {
            'up_threshold': float(self.up_ctrl.GetValue()),
            'down_threshold': float(self.down_ctrl.GetValue()),
            'duration_secs': int(self.dur_ctrl.GetValue())
        }


class ModernAddDialog(wx.Dialog):
    """
    Modern add stock dialog with clean, simple design.
    """

    def __init__(self, parent):
        super().__init__(
            parent,
            title="添加股票",
            size=(500, 250),
            style=wx.DEFAULT_DIALOG_STYLE
        )

        self.SetBackgroundColour(Colors.BG_PRIMARY)
        self._create_ui()
        self.CenterOnParent()

    def _create_ui(self):
        """Create clean dialog UI."""
        panel = wx.Panel(self)
        panel.SetBackgroundColour(Colors.BG_PRIMARY)
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Simple label
        label = wx.StaticText(panel, label="添加股票代码")
        label.SetFont(Typography.h3())
        label.SetForegroundColour(Colors.TEXT_PRIMARY)
        main_sizer.Add(label, 0, wx.ALL, Spacing.LG)

        # Input field with placeholder hint
        self.code_ctrl = wx.TextCtrl(panel, value="", size=(-1, 40))
        self.code_ctrl.SetHint("例如: 512170, 159915")
        apply_text_style(self.code_ctrl, ComponentStyles.input_field())
        main_sizer.Add(self.code_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, Spacing.LG)

        # Add some spacing before buttons
        main_sizer.AddSpacer(Spacing.MD)

        # Buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.AddStretchSpacer(1)

        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "取消", size=(100, 36))
        apply_button_style(cancel_btn, ComponentStyles.button_secondary())
        button_sizer.Add(cancel_btn, 0, wx.RIGHT, Spacing.SM)

        ok_btn = wx.Button(panel, wx.ID_OK, "确定", size=(100, 36))
        apply_button_style(ok_btn, ComponentStyles.button_primary())
        button_sizer.Add(ok_btn, 0)

        main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, Spacing.LG)

        panel.SetSizer(main_sizer)
        
        # Set minimum size to ensure buttons are visible
        self.SetMinSize((500, 250))

        # Set focus to input field
        self.code_ctrl.SetFocus()

    def get_code(self) -> str:
        """Get entered stock code."""
        return self.code_ctrl.GetValue().strip()

