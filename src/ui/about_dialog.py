"""
About dialog displaying application information.
"""

import wx
class AboutDialog(wx.Dialog):
    """
    Simple about dialog with version and developer information.
    """
    
    def __init__(self, parent):
        """
        Initialize about dialog.
        
        Args:
            parent: Parent window
        """
        super().__init__(
            parent,
            title="关于 ETF 监控工具",
            size=(400, 300),
            style=wx.DEFAULT_DIALOG_STYLE
        )
        
        self._create_ui()
        self.Centre()
    
    def _create_ui(self) -> None:
        """Create user interface."""
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        font = app_name.GetFont()
        font.PointSize = 16
        font = font.Bold()
        app_name.SetFont(font)
        sizer.Add(app_name, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        
        # Version
        version = wx.StaticText(panel, label="版本 1.2.0")
        sizer.Add(version, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        
        # Description
        desc = wx.StaticText(
            panel,
            label="实时监控 ETF 价格和涨跌幅\n智能轮播 · 四接口架构 · 闭市智能控制"
        )
        desc.Wrap(350)
        sizer.Add(desc, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        
        # Separator
        sizer.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.ALL, 10)
        
        # Copyright
        copyright_text = wx.StaticText(
            panel,
            label="© 2023 ETF Monitor Team\n\n"
                  "采用 wxPython + httpx 构建\n"
                  "支持东方财富、腾讯等多数据源\n\n"
                  "开源许可：MIT License"
        )
        sizer.Add(copyright_text, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        
        # Close button
        close_btn = wx.Button(panel, wx.ID_OK, "关闭")
        sizer.Add(close_btn, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        
        panel.SetSizer(sizer)
        close_btn = wx.Button(panel, wx.ID_OK, "关闭")
