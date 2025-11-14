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

class StockManagerFrame(wx.Frame):
    def __init__(self, app):
        super().__init__(None, title="股票管理", size=wx.Size(800, 600))
        # Use the main logger to ensure logs appear in the log file
        self._logger = get_logger("etf_monitor")
        self._logger.info("=" * 60)
        self._logger.info("[股票管理窗口] 开始初始化")
        self._logger.info(f"[股票管理窗口] Logger name: {self._logger.name}")
        self._logger.info(f"[股票管理窗口] Logger level: {self._logger.level}")
        self._logger.info(f"[股票管理窗口] Logger handlers: {len(self._logger.handlers)}")

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

        # Build UI
        self._panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Grid setup (no toolbar with Add button)
        self._grid = gridlib.Grid(self._panel)
        self._grid.CreateGrid(0, 8)
        self._grid.SetColLabelValue(0, "代码")
        self._grid.SetColLabelValue(1, "名称")
        self._grid.SetColLabelValue(2, "当前价格")
        self._grid.SetColLabelValue(3, "上涨阈值")
        self._grid.SetColLabelValue(4, "下跌阈值")
        self._grid.SetColLabelValue(5, "弹窗秒数")
        self._grid.SetColLabelValue(6, "编辑")
        self._grid.SetColLabelValue(7, "删除")
        self._grid.EnableEditing(False)
        self._grid.SetColSize(6, 80)
        self._grid.SetColSize(7, 80)
        vbox.Add(self._grid, 1, wx.EXPAND | wx.ALL, 5)
        self._panel.SetSizer(vbox)

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
        print("=" * 80)
        print("[DEBUG] _bind() 方法被调用")
        self._logger.info("[事件绑定] 开始绑定事件处理器")

        self._grid.Bind(gridlib.EVT_GRID_CELL_LEFT_CLICK, self._on_cell_click)
        print("[DEBUG] 已绑定左键点击事件")
        self._logger.info("[事件绑定] 已绑定左键点击事件")

        self._grid.Bind(gridlib.EVT_GRID_LABEL_LEFT_CLICK, self._on_label_click)
        print("[DEBUG] 已绑定标签左键点击事件")
        self._logger.info("[事件绑定] 已绑定标签左键点击事件")

        self._grid.Bind(gridlib.EVT_GRID_CELL_RIGHT_CLICK, self._on_grid_right_click)
        print("[DEBUG] 已绑定单元格右键点击事件")
        self._logger.info("[事件绑定] 已绑定单元格右键点击事件")

        # Bind context menu to multiple targets for comprehensive coverage
        # 1. Grid window for empty cells within the grid
        grid_window = self._grid.GetGridWindow()
        print(f"[DEBUG] grid_window = {grid_window}")
        if grid_window:
            grid_window.Bind(wx.EVT_CONTEXT_MENU, self._on_grid_context_menu)
            print("[DEBUG] 已绑定网格窗口上下文菜单事件")
            self._logger.info("[事件绑定] 已绑定网格窗口上下文菜单事件")
        else:
            print("[DEBUG] 警告：无法获取网格窗口")
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
                            'up_threshold': 0.0,
                            'down_threshold': 0.0,
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
            normalized = {
                'symbol': s.get('symbol'),
                'name': s.get('name', ''),
                'up_threshold': float(s.get('up_threshold', 0.0)),
                'down_threshold': float(s.get('down_threshold', 0.0)),
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
        """Refresh grid display with current symbols data."""
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

            # Try to get price from cache first
            if cache:
                q = cache.get(code)
                if q and q.price is not None:
                    price = f"{q.price:.3f}"
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
            self._grid.SetCellValue(i, 3, str(s.get('up_threshold', '')))
            self._grid.SetCellValue(i, 4, str(s.get('down_threshold', '')))
            self._grid.SetCellValue(i, 5, str(s.get('duration_secs', '')))
            self._grid.SetCellValue(i, 6, "编辑")
            self._grid.SetCellValue(i, 7, "删除")

            # Set cell colors
            self._grid.SetCellBackgroundColour(i, 2, wx.Colour(240, 248, 255))
            self._grid.SetCellBackgroundColour(i, 6, wx.Colour(173, 216, 230))
            self._grid.SetCellBackgroundColour(i, 7, wx.Colour(255, 182, 193))

            # Set read-only cells
            self._grid.SetReadOnly(i, 0, True)
            self._grid.SetReadOnly(i, 1, True)
            self._grid.SetReadOnly(i, 2, True)
            self._grid.SetReadOnly(i, 6, True)
            self._grid.SetReadOnly(i, 7, True)

        self._logger.info(f"[刷新表格] 表格刷新完成")



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

    def _on_add(self, event):
        self._logger.info("[添加股票] 开始添加流程")

        # Check debouncer
        if not self._debouncer.allow("add", 300):
            self._logger.warning("[添加股票] 操作过于频繁，已被防抖器拦截")
            return

        self._logger.info("[添加股票] 创建输入对话框")

        # Pause floating window guard before showing dialog
        # (This is safe to call even if already paused)
        self._logger.info("[添加股票] 暂停浮动窗口守护")
        self._pause_floating_window_guard()

        try:
            # Create dialog with explicit parent and style
            dlg = wx.TextEntryDialog(
                self,
                "请输入股票代码（如 512170）",
                "添加股票",
                style=wx.OK | wx.CANCEL | wx.CENTRE
            )

            # Center dialog on parent
            dlg.CenterOnParent()

            self._logger.info("[添加股票] 显示对话框")
            result = dlg.ShowModal()
            self._logger.info(f"[添加股票] 对话框关闭，结果: {result}")

            if result == wx.ID_OK:
                self._logger.info("[添加股票] 用户点击确定")
                code = dlg.GetValue().strip()
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
                        'up_threshold': 0.0,
                        'down_threshold': 0.0,
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
        # Handle Delete button click (column 7)
        elif col == 7:
            self._on_delete_row(row)
        # Handle editable cells (columns 3, 4, 5)
        elif col in [3, 4, 5]:
            self._grid.EnableCellEditControl()

        event.Skip()

    def _on_edit_row(self, row):
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
            # Create a dialog for editing thresholds
            dlg = wx.Dialog(self, title="编辑股票配置", size=(400, 250), style=wx.DEFAULT_DIALOG_STYLE)
            dlg.CenterOnParent()

            panel = wx.Panel(dlg)
            vbox = wx.BoxSizer(wx.VERTICAL)

            # Stock info
            info_text = wx.StaticText(panel, label=f"股票: {s.get('name')} ({code})")
            vbox.Add(info_text, 0, wx.ALL, 10)

            # Up threshold
            up_box = wx.BoxSizer(wx.HORIZONTAL)
            up_box.Add(wx.StaticText(panel, label="上涨阈值(%):"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            up_ctrl = wx.TextCtrl(panel, value=str(s.get('up_threshold', 0.0)))
            up_box.Add(up_ctrl, 1, wx.EXPAND)
            vbox.Add(up_box, 0, wx.EXPAND | wx.ALL, 5)

            # Down threshold
            down_box = wx.BoxSizer(wx.HORIZONTAL)
            down_box.Add(wx.StaticText(panel, label="下跌阈值(%):"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            down_ctrl = wx.TextCtrl(panel, value=str(s.get('down_threshold', 0.0)))
            down_box.Add(down_ctrl, 1, wx.EXPAND)
            vbox.Add(down_box, 0, wx.EXPAND | wx.ALL, 5)

            # Duration
            dur_box = wx.BoxSizer(wx.HORIZONTAL)
            dur_box.Add(wx.StaticText(panel, label="弹窗秒数:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            dur_ctrl = wx.TextCtrl(panel, value=str(s.get('duration_secs', 5)))
            dur_box.Add(dur_ctrl, 1, wx.EXPAND)
            vbox.Add(dur_box, 0, wx.EXPAND | wx.ALL, 5)

            # Buttons
            btn_box = wx.BoxSizer(wx.HORIZONTAL)
            ok_btn = wx.Button(panel, wx.ID_OK, "确定")
            cancel_btn = wx.Button(panel, wx.ID_CANCEL, "取消")
            btn_box.Add(ok_btn, 0, wx.ALL, 5)
            btn_box.Add(cancel_btn, 0, wx.ALL, 5)
            vbox.Add(btn_box, 0, wx.ALIGN_CENTER | wx.ALL, 10)

            panel.SetSizer(vbox)

            self._logger.info("[编辑股票] 显示对话框")
            result = dlg.ShowModal()
            self._logger.info(f"[编辑股票] 对话框关闭，结果: {result}")

            if result == wx.ID_OK:
                try:
                    up_val = float(up_ctrl.GetValue())
                    down_val = float(down_ctrl.GetValue())
                    dur_val = int(dur_ctrl.GetValue())

                    s['up_threshold'] = up_val
                    s['down_threshold'] = down_val
                    s['duration_secs'] = dur_val
                    self._save_symbols()
                    self._refresh_grid()
                    self._info("修改成功")
                    get_logger(__name__).info(f"edit {code}")
                except ValueError:
                    self._error("请输入有效的数值")

            dlg.Destroy()
        except Exception as e:
            self._logger.error(f"[编辑股票] 对话框异常: {e}", exc_info=True)
            self._error(f"编辑失败：{e}")
        finally:
            # Resume guard after dialog is completely closed
            self._logger.info("[编辑股票] 延迟恢复浮动窗口守护（500ms后）")
            wx.CallLater(500, self._resume_floating_window_guard)

    def _on_delete_row(self, row):
        """处理表格中的“删除”点击。

        逻辑要求：
        - 点击“是”后：删除内存中的股票、保存配置、更新数据抓取列表、刷新表格
        - 点击“否”后：直接关闭对话框，不做任何修改
        """
        if not self._debouncer.allow("delete", 300):
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
