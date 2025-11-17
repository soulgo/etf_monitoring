import wx
import wx.grid as gridlib
import threading
from typing import List, Dict

from ..utils.logger import get_logger
from ..config.manager import get_config
from ..alerts.manager import AlertManager
from ..data.cache import CacheManager
from ..utils.helpers import Debouncer
from .alert_popup import show_toast
from .design_system import (
    Colors, Typography, Spacing, ComponentStyles,
    apply_button_style, get_status_color
)
from .modern_dialogs import ModernEditDialog, ModernAddDialog

class StockManagerFrame(wx.Frame):
    """
    Modern Stock Manager UI with Material Design principles.

    Features:
    - Clean, modern interface with consistent spacing
    - Color-coded status indicators
    - Responsive layout
    - Smooth interactions
    - Professional typography
    """

    def __init__(self, app):
        # Initialize with modern styling
        super().__init__(
            None,
            title="ETF 股票管理",
            size=wx.Size(1000, 700),
            style=wx.DEFAULT_FRAME_STYLE
        )

        # Use the main logger to ensure logs appear in the log file
        self._logger = get_logger("etf_monitor")
        self._logger.info("=" * 60)
        self._logger.info("[股票管理窗口] 开始初始化 - Modern UI")

        self._app = app
        self._config = get_config()

        # Load symbols (with migration from etf_list if needed)
        self._symbols = self._load_symbols()
        self._logger.info(f"[股票管理窗口] 加载了 {len(self._symbols)} 只股票")

        self._sort_key = 'symbol'
        self._sort_asc = True
        self._debouncer = Debouncer()

        # Pause floating window guard to prevent focus stealing
        self._pause_floating_window_guard()

        # Build modern UI
        self._create_ui()

        # Apply modern styling
        self._apply_modern_styling()

        # Bind events
        self._bind()

        # Initial grid refresh
        self._logger.info("[股票管理窗口] 开始初始刷新表格")
        self._refresh_grid()

        # Bind close event to resume floating window guard
        self.Bind(wx.EVT_CLOSE, self._on_close)

        self._logger.info("[股票管理窗口] 初始化完成")
        self._logger.info("=" * 60)

    def _create_ui(self):
        """Create simplified UI layout with grid only."""
        # Main panel with modern background
        self._panel = wx.Panel(self)
        self._panel.SetBackgroundColour(Colors.BG_PRIMARY)

        # Main vertical layout
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Simple toolbar with just buttons
        toolbar_sizer = self._create_simple_toolbar()
        main_sizer.Add(toolbar_sizer, 0, wx.EXPAND | wx.ALL, Spacing.SM)

        # Grid section (main content) - with minimal padding
        self._create_grid()
        main_sizer.Add(self._grid, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, Spacing.SM)

        self._panel.SetSizer(main_sizer)

    def _create_simple_toolbar(self) -> wx.BoxSizer:
        """Create simple toolbar with help text and stats."""
        toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Help text (left-aligned)
        help_text = wx.StaticText(
            self._panel,
            label="💡 提示：右键点击空白区域可快速添加股票"
        )
        help_text.SetFont(Typography.caption())
        help_text.SetForegroundColour(Colors.TEXT_HINT)
        toolbar_sizer.Add(help_text, 0, wx.ALIGN_CENTER_VERTICAL)

        # Spacer - push stats to the right
        toolbar_sizer.AddStretchSpacer(1)

        # Stats label (right-aligned)
        self._stats_label = wx.StaticText(self._panel, label="")
        self._stats_label.SetFont(Typography.caption())
        self._stats_label.SetForegroundColour(Colors.TEXT_SECONDARY)
        toolbar_sizer.Add(self._stats_label, 0, wx.ALIGN_CENTER_VERTICAL)

        return toolbar_sizer

    def _create_header(self) -> wx.BoxSizer:
        """Create header with title and description."""
        header_sizer = wx.BoxSizer(wx.VERTICAL)

        # Title
        title = wx.StaticText(self._panel, label="股票管理")
        title.SetFont(Typography.h1())
        title.SetForegroundColour(Colors.TEXT_PRIMARY)
        header_sizer.Add(title, 0, wx.BOTTOM, Spacing.SM)

        # Description
        desc = wx.StaticText(self._panel, label="管理您的 ETF 监控列表，设置价格提醒阈值")
        desc.SetFont(Typography.body())
        desc.SetForegroundColour(Colors.TEXT_SECONDARY)
        header_sizer.Add(desc, 0)

        return header_sizer

    def _create_toolbar(self) -> wx.BoxSizer:
        """Create toolbar with action buttons."""
        toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Add button (primary action)
        self._add_btn = wx.Button(self._panel, label="+ 添加股票", size=wx.Size(120, 36))
        apply_button_style(self._add_btn, ComponentStyles.button_primary())
        self._add_btn.SetFont(Typography.body())
        toolbar_sizer.Add(self._add_btn, 0, wx.RIGHT, Spacing.SM)

        # Refresh button (secondary action)
        self._refresh_btn = wx.Button(self._panel, label="🔄 刷新", size=wx.Size(100, 36))
        apply_button_style(self._refresh_btn, ComponentStyles.button_secondary())
        self._refresh_btn.SetFont(Typography.body())
        toolbar_sizer.Add(self._refresh_btn, 0, wx.RIGHT, Spacing.SM)

        # Spacer
        toolbar_sizer.AddStretchSpacer(1)

        # Stats label
        self._stats_label = wx.StaticText(self._panel, label="")
        self._stats_label.SetFont(Typography.caption())
        self._stats_label.SetForegroundColour(Colors.TEXT_SECONDARY)
        toolbar_sizer.Add(self._stats_label, 0, wx.ALIGN_CENTER_VERTICAL)

        return toolbar_sizer

    def _create_grid(self):
        """Create modern styled grid."""
        self._grid = gridlib.Grid(self._panel)
        self._grid.CreateGrid(0, 8)

        # Set column labels
        self._grid.SetColLabelValue(0, "代码")
        self._grid.SetColLabelValue(1, "名称")
        self._grid.SetColLabelValue(2, "当前价格")
        self._grid.SetColLabelValue(3, "上涨阈值 (%)")
        self._grid.SetColLabelValue(4, "下跌阈值 (%)")
        self._grid.SetColLabelValue(5, "弹窗时长 (秒)")
        self._grid.SetColLabelValue(6, "编辑")
        self._grid.SetColLabelValue(7, "删除")

        # Disable editing (use buttons instead)
        self._grid.EnableEditing(False)

        # Set column sizes
        self._grid.SetColSize(0, 100)  # Code
        self._grid.SetColSize(1, 150)  # Name
        self._grid.SetColSize(2, 120)  # Price
        self._grid.SetColSize(3, 120)  # Up threshold
        self._grid.SetColSize(4, 120)  # Down threshold
        self._grid.SetColSize(5, 120)  # Duration
        self._grid.SetColSize(6, 80)   # Edit button
        self._grid.SetColSize(7, 80)   # Delete button

    def _create_footer(self) -> wx.BoxSizer:
        """Create footer with additional info."""
        footer_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Help text
        help_text = wx.StaticText(
            self._panel,
            label="💡 提示：右键点击空白区域可快速添加股票"
        )
        help_text.SetFont(Typography.caption())
        help_text.SetForegroundColour(Colors.TEXT_HINT)
        footer_sizer.Add(help_text, 0)

        return footer_sizer

    def _apply_modern_styling(self):
        """Apply modern styling to grid and components."""
        # Grid styling
        grid_style = ComponentStyles.grid_header()

        # Header styling
        self._grid.SetLabelBackgroundColour(grid_style['bg_color'])
        self._grid.SetLabelTextColour(grid_style['fg_color'])
        self._grid.SetLabelFont(grid_style['font'])

        # Cell styling
        cell_style = ComponentStyles.grid_cell()
        self._grid.SetDefaultCellBackgroundColour(cell_style['bg_color'])
        self._grid.SetDefaultCellTextColour(cell_style['fg_color'])
        self._grid.SetDefaultCellFont(cell_style['font'])

        # Grid lines
        self._grid.SetGridLineColour(Colors.BORDER_LIGHT)

        # Selection colors
        self._grid.SetSelectionBackground(Colors.PRIMARY_50)
        self._grid.SetSelectionForeground(Colors.TEXT_PRIMARY)

        # Bind events
        self._bind()

        # Initial grid refresh
        self._logger.info("[股票管理窗口] 开始初始刷新表格")
        self._refresh_grid()

        # Bind close event to resume floating window guard
        self.Bind(wx.EVT_CLOSE, self._on_close)

        self._logger.info("[股票管理窗口] 初始化完成")
        self._logger.info("=" * 60)

    def _bind(self):
        """Bind all event handlers."""
        self._logger.info("[事件绑定] 开始绑定事件处理器")

        # Grid events
        self._grid.Bind(gridlib.EVT_GRID_CELL_LEFT_CLICK, self._on_cell_click)
        self._grid.Bind(gridlib.EVT_GRID_LABEL_LEFT_CLICK, self._on_label_click)
        self._grid.Bind(gridlib.EVT_GRID_CELL_RIGHT_CLICK, self._on_grid_right_click)

        # Context menu for empty areas
        grid_window = self._grid.GetGridWindow()
        if grid_window:
            grid_window.Bind(wx.EVT_CONTEXT_MENU, self._on_grid_context_menu)
            self._logger.info("[事件绑定] 已绑定网格窗口上下文菜单事件")
        else:
            self._logger.warning("[事件绑定] 无法获取网格窗口")

        # 2. Panel for areas outside the grid
        self._panel.Bind(wx.EVT_CONTEXT_MENU, self._on_panel_context_menu)
        print("[DEBUG] 已绑定面板上下文菜单事件")
        self._logger.info("[事件绑定] 已绑定面板上下文菜单事件")

        # 3. Frame itself as a fallback
        self.Bind(wx.EVT_CONTEXT_MENU, self._on_frame_context_menu)
        print("[DEBUG] 已绑定窗口上下文菜单事件")
        self._logger.info("[事件绑定] 已绑定窗口上下文菜单事件")

        print("[DEBUG] 所有事件绑定完成")
        print("=" * 80)
        self._logger.info("[事件绑定] 所有事件绑定完成")

    def _load_symbols(self) -> List[Dict]:
        """Load symbols from config with validation and migration from etf_list."""
        self._logger.info("[配置加载] 开始加载股票列表")
        data = self._config.get('symbols', []) or []

        # Migration: If symbols is empty but etf_list exists, migrate from etf_list
        if not data:
            etf_list = self._config.get('etf_list', []) or []
            if etf_list:
                self._logger.info(f"[配置加载] 检测到 etf_list 有 {len(etf_list)} 个代码，开始迁移到 symbols")
                # Fetch names for each code
                for code in etf_list:
                    if isinstance(code, str) and code.strip():
                        name = self._fetch_stock_name(code.strip())
                        data.append({
                            'symbol': code.strip(),
                            'name': name,
                            'up_thresholds': [],
                            'down_thresholds': [],
                            'duration_secs': 5
                        })
                        self._logger.info(f"[配置加载] 迁移股票: {code} -> {name}")

                # Save migrated data
                if data:
                    self._logger.info(f"[配置加载] 迁移完成，保存 {len(data)} 只股票到 symbols")
                    self._config.set('symbols', data)
                    self._config.save()

        # Validate and normalize each symbol
        validated_symbols = []
        for s in data:
            if not isinstance(s, dict):
                self._logger.warning(f"[配置加载] 跳过无效项（非字典）: {s}")
                continue

            if 'symbol' not in s:
                self._logger.warning(f"[配置加载] 跳过无效项（缺少symbol）: {s}")
                continue

            # Ensure all required fields exist with defaults
            # Migration: support both old (single value) and new (list) format
            up_th = s.get('up_thresholds', s.get('up_threshold', []))
            down_th = s.get('down_thresholds', s.get('down_threshold', []))
            
            # Convert single value to list for backward compatibility
            if isinstance(up_th, (int, float)):
                up_th = [float(up_th)] if up_th > 0 else []
            elif not isinstance(up_th, list):
                up_th = []
            
            if isinstance(down_th, (int, float)):
                down_th = [float(down_th)] if down_th > 0 else []
            elif not isinstance(down_th, list):
                down_th = []
            
            normalized = {
                'symbol': s.get('symbol'),
                'name': s.get('name', ''),
                'up_thresholds': up_th,
                'down_thresholds': down_th,
                'duration_secs': int(s.get('duration_secs', 5))
            }
            validated_symbols.append(normalized)
            self._logger.debug(f"[配置加载] 加载股票: {normalized}")

        self._logger.info(f"[配置加载] 成功加载 {len(validated_symbols)} 只股票")
        return validated_symbols

    def _fetch_stock_name(self, code: str) -> str:
        """Fetch stock name from API or cache."""
        try:
            # Try cache first
            cache = getattr(self._app, 'cache_manager', None)
            if cache:
                cached_quote = cache.get(code)
                if cached_quote and cached_quote.name:
                    self._logger.debug(f"[获取名称] 从缓存获取: {code} -> {cached_quote.name}")
                    return cached_quote.name

            # Fetch from API
            adapter = getattr(self._app, 'primary_adapter', None)
            if adapter:
                self._logger.debug(f"[获取名称] 从API获取: {code}")
                quote = adapter.fetch_quote(code)
                if quote and quote.name:
                    self._logger.debug(f"[获取名称] API返回: {code} -> {quote.name}")
                    return quote.name
        except Exception as e:
            self._logger.warning(f"[获取名称] 获取失败 {code}: {e}")

        # Fallback to code
        return f"股票{code}"

    def _save_symbols(self):
        """Save symbols to config with validation."""
        self._logger.info(f"[配置保存] 开始保存 {len(self._symbols)} 只股票")

        # Validate before saving
        for s in self._symbols:
            if not isinstance(s, dict) or 'symbol' not in s:
                self._logger.error(f"[配置保存] 发现无效股票数据: {s}")
                raise ValueError(f"Invalid symbol data: {s}")

        self._config.set('symbols', self._symbols)
        self._config.save()
        self._logger.info(f"[配置保存] 成功保存到配置文件")

        # Reinitialize alert manager
        try:
            self._app.alert_manager = AlertManager(self._config)
            self._logger.info("[配置保存] 重新初始化告警管理器")
        except Exception as e:
            self._logger.warning(f"[配置保存] 重新初始化告警管理器失败: {e}")

    def _get_filtered(self):
        rows = list(self._symbols)
        key = self._sort_key
        rows.sort(key=lambda x: str(x.get(key, '')).lower(), reverse=not self._sort_asc)
        return rows

    def _refresh_grid(self):
        """Refresh grid display with current symbols data and modern styling."""
        self._logger.info(f"[刷新表格] 开始刷新，当前有 {len(self._symbols)} 只股票")

        rows = self._get_filtered()
        self._logger.info(f"[刷新表格] 过滤排序后有 {len(rows)} 行")

        # Clear existing rows
        while self._grid.GetNumberRows() > 0:
            self._grid.DeleteRows(0)

        # Add new rows
        if rows:
            self._grid.AppendRows(len(rows))
            self._logger.info(f"[刷新表格] 已添加 {len(rows)} 行到表格")

        cache = getattr(self._app, 'cache_manager', None)
        adapter = getattr(self._app, 'primary_adapter', None)

        for i, s in enumerate(rows):
            code = s.get('symbol', '')
            name = s.get('name', '')
            price = ''
            price_color = Colors.TEXT_PRIMARY

            # Try to get price from cache first
            if cache:
                q = cache.get(code)
                if q and q.price is not None:
                    price = f"{q.price:.3f}"
                    # Color code based on change
                    if hasattr(q, 'change_percent'):
                        price_color = get_status_color(q.change_percent)
                    self._logger.debug(f"[刷新表格] 行{i} {code}: 从缓存获取价格 {price}")
                else:
                    self._logger.info(f"[刷新表格] 行{i} {code}: 缓存中无价格数据，尝试从API获取")
                    # If not in cache, try to fetch from API
                    if adapter:
                        try:
                            quote = adapter.fetch_quote(code)
                            if quote and quote.price is not None:
                                price = f"{quote.price:.3f}"
                                # Cache it for future use (use update() method)
                                cache.update(quote)
                                self._logger.info(f"[刷新表格] 行{i} {code}: 从API获取价格 {price}")
                            else:
                                self._logger.warning(f"[刷新表格] 行{i} {code}: API返回无效数据")
                        except Exception as e:
                            self._logger.error(f"[刷新表格] 行{i} {code}: 获取价格失败 - {e}")
                    else:
                        self._logger.warning(f"[刷新表格] 适配器不可用")
            else:
                self._logger.warning(f"[刷新表格] 缓存管理器不可用")

            # Set cell values
            self._grid.SetCellValue(i, 0, code)
            self._grid.SetCellValue(i, 1, name)
            self._grid.SetCellValue(i, 2, price)
            
            # Format thresholds as comma-separated lists
            up_thresholds = s.get('up_thresholds', [])
            down_thresholds = s.get('down_thresholds', [])
            up_str = ', '.join([str(t) for t in up_thresholds]) if up_thresholds else ''
            down_str = ', '.join([str(t) for t in down_thresholds]) if down_thresholds else ''
            
            self._grid.SetCellValue(i, 3, up_str)
            self._grid.SetCellValue(i, 4, down_str)
            self._grid.SetCellValue(i, 5, str(s.get('duration_secs', '')))
            self._grid.SetCellValue(i, 6, "✏️ 编辑")
            self._grid.SetCellValue(i, 7, "🗑️ 删除")

            # Apply modern cell styling
            # Code column - bold
            self._grid.SetCellFont(i, 0, Typography.body())
            self._grid.SetCellTextColour(i, 0, Colors.TEXT_PRIMARY)

            # Name column
            self._grid.SetCellTextColour(i, 1, Colors.TEXT_PRIMARY)

            # Price column - color coded and highlighted
            self._grid.SetCellBackgroundColour(i, 2, Colors.INFO_LIGHT)
            self._grid.SetCellTextColour(i, 2, price_color)
            self._grid.SetCellFont(i, 2, Typography.body())

            # Threshold columns
            self._grid.SetCellTextColour(i, 3, Colors.SUCCESS_DARK)
            self._grid.SetCellTextColour(i, 4, Colors.ERROR_DARK)

            # Duration column
            self._grid.SetCellTextColour(i, 5, Colors.TEXT_SECONDARY)

            # Edit button - primary color
            self._grid.SetCellBackgroundColour(i, 6, Colors.PRIMARY_100)
            self._grid.SetCellTextColour(i, 6, Colors.PRIMARY_700)
            self._grid.SetCellAlignment(i, 6, wx.ALIGN_CENTER, wx.ALIGN_CENTER)

            # Delete button - error color
            self._grid.SetCellBackgroundColour(i, 7, Colors.ERROR_LIGHT)
            self._grid.SetCellTextColour(i, 7, Colors.ERROR_DARK)
            self._grid.SetCellAlignment(i, 7, wx.ALIGN_CENTER, wx.ALIGN_CENTER)

            # Set read-only cells
            self._grid.SetReadOnly(i, 0, True)
            self._grid.SetReadOnly(i, 1, True)
            self._grid.SetReadOnly(i, 2, True)
            self._grid.SetReadOnly(i, 6, True)
            self._grid.SetReadOnly(i, 7, True)

        # Update stats label
        self._update_stats_label()

        self._logger.info(f"[刷新表格] 表格刷新完成")

    def _update_stats_label(self):
        """Update the stats label with current information."""
        total = len(self._symbols)
        cache = getattr(self._app, 'cache_manager', None)

        if cache:
            stats = cache.get_cache_stats()
            hit_rate = stats.get('hit_rate', 0)
            self._stats_label.SetLabel(
                f"总计: {total} 只股票 | 缓存命中率: {hit_rate:.1f}%"
            )
        else:
            self._stats_label.SetLabel(f"总计: {total} 只股票")



    def _on_label_click(self, event):
        col = event.GetCol()
        mapping = {0: 'symbol', 1: 'name'}
        if col in mapping:
            key = mapping[col]
            if self._sort_key == key:
                self._sort_asc = not self._sort_asc
            else:
                self._sort_key = key
                self._sort_asc = True
            self._refresh_grid()
        event.Skip()

    def _on_grid_right_click(self, event):
        """Handle right-click on grid cells."""
        try:
            print("\n" + "=" * 80)
            print("[DEBUG] _on_grid_right_click() 被调用！")
            print(f"[DEBUG] 事件类型: {event.GetEventType()}")
            print(f"[DEBUG] 行: {event.GetRow()}, 列: {event.GetCol()}")

            self._logger.info("=" * 60)
            self._logger.info("[右键菜单] 单元格右键点击事件触发")
            self._logger.info(f"[右键菜单] 事件类型: {event.GetEventType()}")
            self._logger.info(f"[右键菜单] 行: {event.GetRow()}, 列: {event.GetCol()}")

            # Pause floating window guard to prevent interference
            print("[DEBUG] 暂停浮动窗口守护...")
            self._pause_floating_window_guard()

            # Show context menu
            print("[DEBUG] 调用 _show_context_menu()...")
            self._show_context_menu()

            print("[DEBUG] 单元格右键处理完成")
            print("=" * 80 + "\n")
            self._logger.info("[右键菜单] 单元格右键处理完成")
        except Exception as e:
            print(f"[DEBUG] 异常！{e}")
            import traceback
            traceback.print_exc()
            self._logger.error(f"[右键菜单] 单元格右键处理异常: {e}", exc_info=True)

    def _on_grid_context_menu(self, event):
        """Handle context menu event on empty grid space."""
        try:
            print("\n" + "=" * 80)
            print("[DEBUG] _on_grid_context_menu() 被调用！")
            print(f"[DEBUG] 事件类型: {event.GetEventType()}")

            self._logger.info("=" * 60)
            self._logger.info("[右键菜单] 网格空白区域上下文菜单事件触发")
            self._logger.info(f"[右键菜单] 事件类型: {event.GetEventType()}")

            # Pause floating window guard to prevent interference
            print("[DEBUG] 暂停浮动窗口守护...")
            self._pause_floating_window_guard()

            # Show context menu
            print("[DEBUG] 调用 _show_context_menu()...")
            self._show_context_menu()

            print("[DEBUG] 网格空白区域右键处理完成")
            print("=" * 80 + "\n")
            self._logger.info("[右键菜单] 网格空白区域右键处理完成")
        except Exception as e:
            print(f"[DEBUG] 异常！{e}")
            import traceback
            traceback.print_exc()
            self._logger.error(f"[右键菜单] 网格空白区域右键处理异常: {e}", exc_info=True)

    def _on_panel_context_menu(self, event):
        """Handle context menu event on panel."""
        try:
            print("\n" + "=" * 80)
            print("[DEBUG] _on_panel_context_menu() 被调用！")
            print(f"[DEBUG] 事件类型: {event.GetEventType()}")

            self._logger.info("=" * 60)
            self._logger.info("[右键菜单] 面板上下文菜单事件触发")
            self._logger.info(f"[右键菜单] 事件类型: {event.GetEventType()}")

            # Pause floating window guard to prevent interference
            print("[DEBUG] 暂停浮动窗口守护...")
            self._pause_floating_window_guard()

            # Show context menu
            print("[DEBUG] 调用 _show_context_menu()...")
            self._show_context_menu()

            print("[DEBUG] 面板右键处理完成")
            print("=" * 80 + "\n")
            self._logger.info("[右键菜单] 面板右键处理完成")
        except Exception as e:
            print(f"[DEBUG] 异常！{e}")
            import traceback
            traceback.print_exc()
            self._logger.error(f"[右键菜单] 面板右键处理异常: {e}", exc_info=True)

    def _on_frame_context_menu(self, event):
        """Handle context menu event on frame."""
        try:
            print("\n" + "=" * 80)
            print("[DEBUG] _on_frame_context_menu() 被调用！")
            print(f"[DEBUG] 事件类型: {event.GetEventType()}")

            self._logger.info("=" * 60)
            self._logger.info("[右键菜单] 窗口上下文菜单事件触发")
            self._logger.info(f"[右键菜单] 事件类型: {event.GetEventType()}")

            # Pause floating window guard to prevent interference
            print("[DEBUG] 暂停浮动窗口守护...")
            self._pause_floating_window_guard()

            # Show context menu
            print("[DEBUG] 调用 _show_context_menu()...")
            self._show_context_menu()

            print("[DEBUG] 窗口右键处理完成")
            print("=" * 80 + "\n")
            self._logger.info("[右键菜单] 窗口右键处理完成")
        except Exception as e:
            print(f"[DEBUG] 异常！{e}")
            import traceback
            traceback.print_exc()
            self._logger.error(f"[右键菜单] 窗口右键处理异常: {e}", exc_info=True)

    def _show_context_menu(self):
        """Show context menu with Add Stock option."""
        # Track if a menu item was clicked to open a dialog
        self._menu_item_clicked = False

        try:
            print("[DEBUG] _show_context_menu() 开始执行")
            self._logger.info("[右键菜单] 开始创建上下文菜单")

            # Create menu
            print("[DEBUG] 创建 wx.Menu()...")
            menu = wx.Menu()
            print(f"[DEBUG] 菜单对象已创建: {menu}")
            self._logger.info("[右键菜单] 菜单对象已创建")

            # Add menu item
            print("[DEBUG] 添加菜单项...")
            add_item = menu.Append(wx.ID_ANY, "添加股票")
            print(f"[DEBUG] 菜单项已添加，ID: {add_item.GetId()}")
            self._logger.info(f"[右键菜单] 菜单项已添加，ID: {add_item.GetId()}")

            # Bind menu item event
            print("[DEBUG] 绑定菜单项事件...")
            self.Bind(wx.EVT_MENU, self._on_add_from_menu, add_item)
            print("[DEBUG] 菜单项事件已绑定")
            self._logger.info("[右键菜单] 菜单项事件已绑定")

            # Show menu at cursor position
            print("[DEBUG] 准备显示菜单...")
            self._logger.info("[右键菜单] 准备显示菜单...")
            self.PopupMenu(menu)
            print("[DEBUG] PopupMenu 调用完成")
            self._logger.info("[右键菜单] PopupMenu 调用完成")

            # Destroy menu after it's closed
            menu.Destroy()
            print("[DEBUG] 菜单已销毁")
            self._logger.info("[右键菜单] 菜单已销毁")

            # Resume guard after menu closes, but only if no dialog will be shown
            # If user clicked "添加股票", _on_add() will manage the guard lifecycle
            # Use a short delay to allow menu item handler to set the flag
            def _check_and_resume():
                if not self._menu_item_clicked:
                    self._logger.info("[右键菜单] 菜单关闭且无对话框，恢复浮动窗口守护")
                    self._resume_floating_window_guard()
                else:
                    self._logger.info("[右键菜单] 菜单关闭但将显示对话框，守护恢复由对话框处理")

            wx.CallLater(100, _check_and_resume)

        except Exception as e:
            print(f"[DEBUG] _show_context_menu() 异常！{e}")
            import traceback
            traceback.print_exc()
            self._logger.error(f"[右键菜单] 显示菜单异常: {e}", exc_info=True)
            # On error, resume guard to be safe
            wx.CallLater(500, self._resume_floating_window_guard)

    def _on_add_from_menu(self, event):
        """Handle add stock from context menu."""
        try:
            self._logger.info("[右键菜单] 点击了'添加股票'菜单项")
            # Set flag to indicate a dialog will be shown
            self._menu_item_clicked = True
            self._on_add(event)
        except Exception as e:
            self._logger.error(f"[右键菜单] 处理菜单点击异常: {e}", exc_info=True)

    def _pause_floating_window_guard(self):
        """Pause floating window guard to prevent focus stealing."""
        try:
            if hasattr(self._app, 'floating_window') and self._app.floating_window:
                self._app.floating_window.pause_guard()
                self._logger.info("[股票管理] 已暂停浮动窗口守护")
        except Exception as e:
            self._logger.warning(f"[股票管理] 暂停浮动窗口守护失败: {e}")

    def _resume_floating_window_guard(self):
        """Resume floating window guard."""
        try:
            if hasattr(self._app, 'floating_window') and self._app.floating_window:
                self._app.floating_window.resume_guard()
                self._logger.info("[股票管理] 已恢复浮动窗口守护")
        except Exception as e:
            self._logger.warning(f"[股票管理] 恢复浮动窗口守护失败: {e}")

    def _on_close(self, event):
        """Handle window close event."""
        self._logger.info("[股票管理] 关闭窗口")
        self._resume_floating_window_guard()
        self.Destroy()

    def _on_refresh_click(self, event):
        """Handle refresh button click."""
        self._logger.info("[刷新] 手动刷新表格")
        self._refresh_grid()
        show_toast("✅ 刷新完成", "success", 2000)

    def _on_add(self, event):
        self._logger.info("[添加股票] 按钮被点击，开始添加流程")

        # Check debouncer - reduced to 500ms for better responsiveness
        if not self._debouncer.allow("add", 500):
            self._logger.warning("[添加股票] 操作过于频繁，已被防抖器拦截")
            return

        self._logger.info("[添加股票] 通过防抖检查，创建现代输入对话框")

        # Pause floating window guard before showing dialog
        self._logger.info("[添加股票] 暂停浮动窗口守护")
        self._pause_floating_window_guard()

        try:
            # Create modern dialog
            dlg = ModernAddDialog(self)

            self._logger.info("[添加股票] 显示对话框")
            result = dlg.ShowModal()
            self._logger.info(f"[添加股票] 对话框关闭，结果: {result}")

            if result == wx.ID_OK:
                self._logger.info("[添加股票] 用户点击确定")
                code = dlg.get_code()
                dlg.Destroy()

                self._logger.info(f"[添加股票] 获取到股票代码: {code}")

                # Validate input
                if not code:
                    self._logger.warning("[添加股票] 股票代码为空")
                    self._error("代码不能为空")
                    return

                # Check duplicate
                if any(s.get('symbol') == code for s in self._symbols):
                    self._logger.warning(f"[添加股票] 股票代码已存在: {code}")
                    self._error("代码已存在")
                    return

                self._logger.info(f"[添加股票] 开始验证股票代码: {code}")

                # Define add operation
                def do_add():
                    self._logger.info(f"[添加股票] 执行添加操作: {code}")
                    adapter = getattr(self._app, 'primary_adapter', None)
                    if adapter is None:
                        self._logger.error("[添加股票] 适配器未初始化")
                        raise Exception("适配器未初始化")

                    self._logger.info(f"[添加股票] 调用API获取股票信息: {code}")
                    quote = adapter.fetch_quote(code)

                    if not quote:
                        self._logger.error(f"[添加股票] 股票代码不存在: {code}")
                        raise Exception("股票代码不存在，请重新输入")

                    name = quote.name
                    price = quote.price if quote.price is not None else 0.0
                    self._logger.info(f"[添加股票] 获取到股票信息: {name}, 价格: {price}")

                    # Cache the quote immediately so it shows in the grid (use update() method)
                    cache = getattr(self._app, 'cache_manager', None)
                    if cache:
                        cache.update(quote)
                        self._logger.info(f"[添加股票] 已缓存股票数据: {code}")
                    else:
                        self._logger.warning(f"[添加股票] 缓存管理器不可用，价格可能不显示")

                    # Add to symbols list
                    new_symbol = {
                        'symbol': code,
                        'name': name,
                        'up_thresholds': [],
                        'down_thresholds': [],
                        'duration_secs': 5
                    }
                    self._symbols.append(new_symbol)
                    self._logger.info(f"[添加股票] 添加到内存列表: {new_symbol}")

                    # Save to config
                    self._save_symbols()
                    self._logger.info(f"[添加股票] 保存到配置文件")

                    # Update data fetcher with all symbol codes
                    symbol_codes = [s.get('symbol') for s in self._symbols]
                    self._app.data_fetcher.update_etf_list(symbol_codes)
                    self._logger.info(f"[添加股票] 更新数据获取器，共 {len(symbol_codes)} 只股票")

                    # Refresh grid to show the new stock with price
                    wx.CallAfter(self._refresh_grid)
                    self._logger.info(f"[添加股票] 刷新界面")

                # Execute in background thread
                import threading
                def _runner():
                    err = None
                    try:
                        do_add()
                    except Exception as e:
                        err = e
                        self._logger.error(f"[添加股票] 执行失败: {e}", exc_info=True)

                    def _finish():
                        if err is None:
                            self._info("添加成功")
                        else:
                            self._error(f"添加失败：{err}")

                    wx.CallAfter(_finish)

                threading.Thread(target=_runner, daemon=True).start()
            else:
                self._logger.info("[添加股票] 用户取消操作")
                dlg.Destroy()

        except Exception as e:
            self._logger.error(f"[添加股票] 对话框异常: {e}", exc_info=True)
            self._error(f"对话框错误：{e}")
        finally:
            # CRITICAL: Resume guard AFTER dialog is completely closed
            # Use CallLater to ensure dialog is fully destroyed before resuming
            self._logger.info("[添加股票] 延迟恢复浮动窗口守护（500ms后）")
            wx.CallLater(500, self._resume_floating_window_guard)

    def _on_cell_click(self, event):
        row = event.GetRow()
        col = event.GetCol()

        # Handle Edit button click (column 6)
        if col == 6:
            self._on_edit_row(row)
            # Don't skip event for button clicks to prevent duplicate triggers
            return
        # Handle Delete button click (column 7)
        elif col == 7:
            self._on_delete_row(row)
            # Don't skip event for button clicks to prevent duplicate triggers
            return
        # Handle editable cells (columns 3, 4, 5)
        elif col in [3, 4, 5]:
            self._grid.EnableCellEditControl()

        event.Skip()

    def _on_edit_row(self, row):
        """Handle edit row action with modern dialog."""
        if not self._debouncer.allow("edit", 300):
            return

        code = self._grid.GetCellValue(row, 0)
        s = next((x for x in self._symbols if x.get('symbol') == code), None)
        if not s:
            return

        # Pause floating window guard before showing dialog
        self._logger.info("[编辑股票] 暂停浮动窗口守护")
        self._pause_floating_window_guard()

        try:
            # Create modern edit dialog
            dlg = ModernEditDialog(self, s)

            self._logger.info("[编辑股票] 显示对话框")
            result = dlg.ShowModal()

            if result == wx.ID_OK:
                # Get validated values
                values = dlg.get_values()

                # Update symbol data
                s['up_thresholds'] = values['up_thresholds']
                s['down_thresholds'] = values['down_thresholds']
                s['duration_secs'] = values['duration_secs']

                self._logger.info(f"[编辑股票] 更新配置: {code} -> {values}")

                # Save and refresh
                self._save_symbols()
                self._refresh_grid()

                show_toast("✅ 配置已保存", "success", 2000)

            dlg.Destroy()
        except Exception as e:
            self._logger.error(f"[编辑股票] 对话框异常: {e}", exc_info=True)
            self._error(f"编辑失败：{e}")
        finally:
            # Resume guard after dialog is completely closed
            self._logger.info("[编辑股票] 延迟恢复浮动窗口守护（500ms后）")
            wx.CallLater(500, self._resume_floating_window_guard)

    def _on_delete_row(self, row):
        """处理表格中的"删除"点击。

        逻辑要求：
        - 点击"是"后：删除内存中的股票、保存配置、更新数据抓取列表、刷新表格
        - 点击"否"后：直接关闭对话框，不做任何修改
        """
        # Use a unique key for each delete operation to prevent race conditions
        delete_key = f"delete_{row}"
        if not self._debouncer.allow(delete_key, 1000):
            self._logger.warning(f"[删除股票] 防抖拦截: 行 {row}")
            return

        code = self._grid.GetCellValue(row, 0)
        name = self._grid.GetCellValue(row, 1)

        # Pause floating window guard before showing dialog
        self._logger.info("[删除股票] 暂停浮动窗口守护")
        self._pause_floating_window_guard()

        try:
            self._logger.info(f"[删除股票] 准备删除: {name} ({code})")
            # 同步确认对话框，在主线程执行
            if not self._confirm(f"确认删除股票 {name} ({code})?"):
                self._logger.info("[删除股票] 用户取消删除")
                # Resume guard immediately if user cancels
                wx.CallLater(100, self._resume_floating_window_guard)
                return

            # 真正执行删除逻辑（同步执行即可，数据量很小）
            self._symbols = [s for s in self._symbols if s.get('symbol') != code]
            self._save_symbols()

            # 更新数据抓取器监控的代码列表
            try:
                if hasattr(self._app, "data_fetcher") and self._app.data_fetcher:
                    symbol_codes = [x.get('symbol') for x in self._symbols]
                    self._app.data_fetcher.update_etf_list(symbol_codes)
            except Exception as e:
                # 更新失败不影响配置保存和界面刷新，只做日志记录
                self._logger.warning(f"[删除股票] 更新数据抓取器失败: {e}")

            # 刷新表格
            self._refresh_grid()

            self._info("删除成功")
            get_logger(__name__).info(f"delete {code}")
        except Exception as e:
            self._logger.error(f"[删除股票] 执行失败: {e}", exc_info=True)
            self._error(f"删除失败：{e}")
        finally:
            # Resume guard after dialog is completely closed
            self._logger.info("[删除股票] 延迟恢复浮动窗口守护（500ms后）")
            wx.CallLater(500, self._resume_floating_window_guard)

    # 统一提示/加载态
    def _info(self, msg: str, title: str = "提示"):
        show_toast(msg, "success", 2500)

    def _error(self, msg: str, title: str = "错误"):
        show_toast(msg, "error", 2500)

    def _confirm(self, msg: str, title: str = "确认") -> bool:
        dlg = wx.MessageDialog(self, msg, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
        res = dlg.ShowModal()
        dlg.Destroy()
        return res == wx.ID_YES
