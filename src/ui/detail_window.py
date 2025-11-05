"""
Detail window displaying all ETF quotes in a table.

Provides comprehensive view of all monitored ETFs with sorting and real-time updates.
"""

import wx

from ..data.models import ETFQuote
from ..utils.logger import get_logger
from ..utils.helpers import format_percent


class DetailWindow(wx.Frame):
    """
    Detail window with sortable ETF list.
    
    Layout (800x400):
    - Table showing all ETF quotes
    - Columns: code, name, price, change_percent, update_time
    - Color-coded rows (green for up, red for down)
    - Click column header to sort
    - Manual refresh button
    - Auto-updates on data changes
    """
    
    def __init__(self, parent, title="ETF 监控 - 实时行情"):
        """
        Initialize detail window.
        
        Args:
            parent: Parent window
            title: Window title
        """
        super().__init__(
            parent,
            title=title,
            size=(800, 450),
            style=wx.DEFAULT_FRAME_STYLE
        )
        
        self._logger = get_logger(__name__)
        self._etf_data = {}
        self._sort_column = 0
        self._sort_ascending = True
        
        # Callback for manual refresh
        self._on_refresh_callback = None
        
        # Create UI
        self._create_ui()
        
        # Bind close event to hide instead of destroy
        self.Bind(wx.EVT_CLOSE, self._on_close)
        
        self.Centre()
    
    def _create_ui(self) -> None:
        """Create user interface."""
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
        
        # ETF List
        self._list_ctrl = wx.ListCtrl(
            panel,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN
        )
        
        # Add columns
        self._list_ctrl.InsertColumn(0, "代码", width=100)
        self._list_ctrl.InsertColumn(1, "名称", width=150)
        self._list_ctrl.InsertColumn(2, "最新价", width=100)
        self._list_ctrl.InsertColumn(3, "涨跌幅", width=120)
        self._list_ctrl.InsertColumn(4, "更新时间", width=120)
        
        # Bind column click for sorting
        self._list_ctrl.Bind(wx.EVT_LIST_COL_CLICK, self._on_column_click)
        
        main_sizer.Add(self._list_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        
        panel.SetSizer(main_sizer)
    
    def update_data(self, etf_data: dict) -> None:
        """
        Update ETF data and refresh display.
        
        Args:
            etf_data: Dictionary mapping code to ETFQuote
        """
        self._etf_data = etf_data.copy()
        self._refresh_list()
        
        # Update last update time
        if etf_data:
            # Get latest update time from quotes
            latest_time = max(
                (quote.update_time for quote in etf_data.values()),
                default="--"
            )
            self._update_time_label.SetLabel(f"最后更新: {latest_time}")
    
    def _refresh_list(self) -> None:
        """Refresh list control with current data."""
        # Clear existing items
        self._list_ctrl.DeleteAllItems()
        
        if not self._etf_data:
            return
        
        # Sort data
        sorted_quotes = self._get_sorted_quotes()
        
        # Add items
        for quote in sorted_quotes:
            index = self._list_ctrl.GetItemCount()
            
            # Insert row
            self._list_ctrl.InsertItem(index, quote.code)
            self._list_ctrl.SetItem(index, 1, quote.name)
            self._list_ctrl.SetItem(index, 2, f"{quote.price:.3f}")
            self._list_ctrl.SetItem(index, 3, format_percent(quote.change_percent))
            self._list_ctrl.SetItem(index, 4, quote.update_time)
            
            # Color-code rows based on change
            if quote.change_percent > 0:
                # Up - light green background
                self._list_ctrl.SetItemBackgroundColour(index, wx.Colour(230, 255, 230))
            elif quote.change_percent < 0:
                # Down - light red background
                self._list_ctrl.SetItemBackgroundColour(index, wx.Colour(255, 230, 230))
    
    def _get_sorted_quotes(self) -> list:
        """
        Get sorted list of quotes based on current sort settings.
        
        Returns:
            Sorted list of ETFQuote objects
        """
        quotes = list(self._etf_data.values())
        
        # Define sort keys for each column
        sort_keys = {
            0: lambda q: q.code,
            1: lambda q: q.name,
            2: lambda q: q.price,
            3: lambda q: q.change_percent,
            4: lambda q: q.update_time,
        }
        
        key_func = sort_keys.get(self._sort_column, lambda q: q.code)
        
        return sorted(quotes, key=key_func, reverse=not self._sort_ascending)
    
    def _on_column_click(self, event) -> None:
        """
        Handle column header click for sorting.
        
        Args:
            event: Column click event
        """
        column = event.GetColumn()
        
        # Toggle sort direction if same column, otherwise reset to ascending
        if column == self._sort_column:
            self._sort_ascending = not self._sort_ascending
        else:
            self._sort_column = column
            self._sort_ascending = True
        
        self._refresh_list()
        
        self._logger.debug(
            f"Sorted by column {column}, ascending={self._sort_ascending}"
        )
    
    def _on_refresh(self, event) -> None:
        """Handle manual refresh button."""
        if self._on_refresh_callback:
            self._on_refresh_callback()
    
    def _on_close(self, event) -> None:
        """Handle window close - hide instead of destroy."""
        self.Hide()
    
    def set_on_refresh(self, callback) -> None:
        """
        Set refresh callback.
        
        Args:
            callback: Callback function to invoke on refresh
        """
        self._on_refresh_callback = callback

