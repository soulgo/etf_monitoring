"""
Detail window displaying all ETF quotes in a table.

Provides a simple, stable list view with sorting and manual refresh.
"""

import wx

from ..utils.logger import get_logger
from ..utils.helpers import format_percent


class DetailWindow(wx.Frame):
    """Detail window with sortable ETF list."""

    def __init__(self, parent, title="ETF 监控 - 实时行情"):
        super().__init__(parent, title=title, size=(800, 450), style=wx.DEFAULT_FRAME_STYLE)

        self._logger = get_logger(__name__)
        self._etf_data = {}
        self._sort_column = 0
        self._sort_ascending = True
        self._on_refresh_callback = None

        self._create_ui()
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Centre()

    def _create_ui(self) -> None:
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Toolbar
        toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._update_time_label = wx.StaticText(panel, label="最后更新: --")
        toolbar_sizer.Add(self._update_time_label, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        refresh_btn = wx.Button(panel, label="手动刷新")
        refresh_btn.Bind(wx.EVT_BUTTON, self._on_refresh)
        toolbar_sizer.Add(refresh_btn, 0, wx.ALL, 5)
        main_sizer.Add(toolbar_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # List
        self._list_ctrl = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.BORDER_SIMPLE)
        self._list_ctrl.InsertColumn(0, "代码", width=100)
        self._list_ctrl.InsertColumn(1, "名称", width=150)
        self._list_ctrl.InsertColumn(2, "最新价", width=100)
        self._list_ctrl.InsertColumn(3, "涨跌幅", width=120)
        self._list_ctrl.InsertColumn(4, "更新时间", width=120)
        self._list_ctrl.Bind(wx.EVT_LIST_COL_CLICK, self._on_column_click)
        main_sizer.Add(self._list_ctrl, 1, wx.EXPAND | wx.ALL, 5)

        panel.SetSizer(main_sizer)

    def update_data(self, etf_data: dict) -> None:
        """Update ETF data and refresh display."""
        self._etf_data = etf_data or {}
        # Update last update time
        latest_time = "--"
        if self._etf_data:
            try:
                latest_time = max((q.update_time for q in self._etf_data.values()), default="--")
            except Exception:
                latest_time = "--"
        self._update_time_label.SetLabel(f"最后更新: {latest_time}")

        # Refresh list contents
        self._list_ctrl.DeleteAllItems()
        for quote in self._get_sorted_quotes():
            index = self._list_ctrl.GetItemCount()
            self._list_ctrl.InsertItem(index, getattr(quote, 'code', ''))
            self._list_ctrl.SetItem(index, 1, getattr(quote, 'name', ''))
            price = getattr(quote, 'price', 0.0)
            self._list_ctrl.SetItem(index, 2, f"{price:.3f}")
            change_percent = getattr(quote, 'change_percent', 0.0)
            self._list_ctrl.SetItem(index, 3, format_percent(change_percent))
            self._list_ctrl.SetItem(index, 4, getattr(quote, 'update_time', '--'))

            # Row color by change
            try:
                if change_percent > 0:
                    self._list_ctrl.SetItemBackgroundColour(index, wx.Colour(230, 255, 230))
                elif change_percent < 0:
                    self._list_ctrl.SetItemBackgroundColour(index, wx.Colour(255, 230, 230))
            except Exception:
                pass

    def _get_sorted_quotes(self) -> list:
        quotes = list(self._etf_data.values())
        sort_map = {
            0: lambda q: getattr(q, 'code', ''),
            1: lambda q: getattr(q, 'name', ''),
            2: lambda q: getattr(q, 'price', 0.0),
            3: lambda q: getattr(q, 'change_percent', 0.0),
            4: lambda q: getattr(q, 'update_time', ''),
        }
        key = sort_map.get(self._sort_column, sort_map[0])
        try:
            return sorted(quotes, key=key, reverse=not self._sort_ascending)
        except Exception:
            return quotes

    def _on_column_click(self, event) -> None:
        col = event.GetColumn()
        if col == self._sort_column:
            self._sort_ascending = not self._sort_ascending
        else:
            self._sort_column = col
            self._sort_ascending = True
        self.update_data(self._etf_data)

    def _on_refresh(self, event) -> None:
        if self._on_refresh_callback:
            try:
                self._on_refresh_callback()
            except Exception:
                pass

    def _on_close(self, event) -> None:
        self.Hide()

    def set_on_refresh(self, callback) -> None:
        self._on_refresh_callback = callback

