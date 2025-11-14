import wx
import time

class AlertPopup(wx.Frame):
    def __init__(self, symbol: str, name: str, price: float, change_percent: float, trigger_type: str, duration_secs: int = 5):
        style = wx.STAY_ON_TOP | wx.NO_BORDER | wx.FRAME_TOOL_WINDOW
        super().__init__(None, title="Price Alert", style=style)
        panel = wx.Panel(self)
        font = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        sizer = wx.BoxSizer(wx.VERTICAL)
        line1 = wx.StaticText(panel, label=f"{symbol} {name}")
        line2 = wx.StaticText(panel, label=f"价格 {price:.3f} 涨跌 {change_percent:+.2f}%")
        line3 = wx.StaticText(panel, label=f"触发 {trigger_type}")
        for w in (line1, line2, line3):
            w.SetFont(font)
        close_btn = wx.Button(panel, label="X")
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.AddStretchSpacer(1)
        btn_sizer.Add(close_btn, 0, wx.ALL, 0)
        sizer.Add(line1, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 8)
        sizer.Add(line2, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 4)
        sizer.Add(line3, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 4)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 0)
        panel.SetSizer(sizer)
        panel.SetBackgroundColour(wx.Colour(255, 240, 200) if trigger_type == '上涨' else wx.Colour(200, 240, 255))
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.GetSizer().Add(panel, 1, wx.EXPAND)
        self.Layout()
        self.SetSize(wx.Size(280, 120))
        sw, sh = wx.GetDisplaySize()
        self.SetPosition(wx.Point(sw - 300, sh - 180))
        close_btn.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda e: self.Close(), self._timer)
        self._timer.Start(int(max(1, duration_secs) * 1000), wx.TIMER_ONE_SHOT)


class ToastFrame(wx.Frame):
    def __init__(self, message: str, kind: str = "info", duration_ms: int = 2000):
        style = wx.STAY_ON_TOP | wx.NO_BORDER | wx.FRAME_TOOL_WINDOW
        super().__init__(None, title="", style=style)
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        icon = wx.StaticText(panel, label="")
        text = wx.StaticText(panel, label=message)
        sizer.Add(icon, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 6)
        sizer.Add(text, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 6)
        panel.SetSizer(sizer)
        bg = wx.Colour(230, 255, 230) if kind == "success" else wx.Colour(255, 230, 230) if kind == "error" else wx.Colour(240, 240, 240)
        fg = wx.Colour(0, 100, 0) if kind == "success" else wx.Colour(180, 0, 0) if kind == "error" else wx.Colour(60, 60, 60)
        panel.SetBackgroundColour(bg)
        text.SetForegroundColour(fg)
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.GetSizer().Add(panel, 1, wx.EXPAND)
        self.Fit()
        sw, sh = wx.GetDisplaySize()
        w, h = self.GetSize()
        self.SetPosition(wx.Point(sw - w - 40, sh - h - 60))
        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda e: self.Close(), self._timer)
        self._timer.Start(max(1000, int(duration_ms)), wx.TIMER_ONE_SHOT)


def show_toast(message: str, kind: str = "info", duration_ms: int = 2000):
    try:
        frm = ToastFrame(message, kind, duration_ms)
        frm.Show()
    except Exception:
        pass
