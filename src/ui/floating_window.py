"""
右下角悬浮窗，在屏幕右下角显示 ETF 信息。

提供类似时钟的显示效果，固定在任务栏时钟上方。
"""

import wx
from typing import Dict, Optional, Tuple
from ..data.models import ETFQuote
from ..utils.logger import get_logger

class FloatingWindow(wx.Frame):
    """
    右下角悬浮窗，显示 ETF 轮播信息。
    
    特性：
    - 固定在屏幕右下角（时钟上方）
    - 大号清晰文字
    - 无边框、半透明
    - 始终置顶
    - 自动轮播
    """
    
    def __init__(
        self,
        parent=None,
        position=None,  # 忽略，自动计算右下角位置
        window_size: Optional[Tuple[int, int]] = None,
        font_size=18,
        transparency=200,
        rotation_interval=3
    ):
        """
        初始化悬浮窗。
        
        Args:
            parent: 父窗口
            position: 位置参数（忽略，自动定位）
            font_size: 字体大小
            transparency: 透明度 (0-255, 255为不透明)
            rotation_interval: 轮播间隔（秒）
        """
        # 创建无边框、置顶的工具窗口
        # 使用 FRAME_TOOL_WINDOW 代替 FRAME_NO_TASKBAR，避免系统菜单导致窗口消失
        style = (
            wx.FRAME_TOOL_WINDOW |  # 工具窗口，不在任务栏显示，更稳定
            wx.STAY_ON_TOP |
            wx.NO_BORDER
        )
        
        # 尺寸与缩放配置
        self._base_default_size = (350, 60)
        self._min_width = 1
        self._min_height = 1
        initial_width, initial_height = self._base_default_size
        if window_size and isinstance(window_size, (list, tuple)) and len(window_size) == 2:
            initial_width = max(int(window_size[0]), self._min_width)
            initial_height = max(int(window_size[1]), self._min_height)
        self._window_width = initial_width
        self._window_height = initial_height
        
        super().__init__(
            parent,
            title="ETF Monitor",
            size=wx.Size(self._window_width, self._window_height),
            style=style
        )
        self.SetMinSize(wx.Size(self._min_width, self._min_height))
        
        self._logger = get_logger(__name__)
        self._font_size = font_size
        self._transparency = transparency
        self._rotation_interval = rotation_interval
        
        # 数据
        self._etf_data: Dict[str, ETFQuote] = {}
        self._etf_codes: list = []
        self._changed_etf_codes: list = []  # 只存储有变化的ETF代码
        self._current_index = 0
        
        # 窗口状态追踪
        self._user_hidden = False  # 是否由用户主动隐藏
        self._guard_paused = False  # 守护是否暂停（用于托盘菜单等场景）
        
        # 拖动相关
        self._dragging = False
        self._drag_start_pos = None
        self._window_start_pos = None
        self._resizing = False
        self._resize_direction = ''  # 调整方向：N, S, E, W, NE, NW, SE, SW
        self._resize_start_pos = None
        self._window_start_size = None
        self._window_start_pos_for_resize = None  # 调整大小时的起始位置
        self._resize_margin = 12
        self._cursor_cache: Dict[int, wx.Cursor] = {}
        self._text_sizer_item = None
        self._current_padding = 10

        dpi = wx.Display().GetPPI().GetHeight() or 96
        self._min_point_size = max(8, int(round(10 * 72 / dpi)))

        # 创建UI
        self._create_ui()
        
        # 设置透明度
        self.SetTransparent(self._transparency)
        
        # 自动定位到右下角
        self._position_bottom_right()
        
        # 确保窗口始终置顶
        self._ensure_always_on_top()
        
        # 绑定事件
        self._bind_events()
        
        # 轮播定时器
        self._rotation_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_rotation_timer, self._rotation_timer)
        
        # 数据加载超时检测定时器（10秒）
        self._timeout_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_timeout_check, self._timeout_timer)
        
        # 窗口可见性守护定时器（每100ms检查一次，更快响应）
        self._visibility_guard_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_visibility_guard, self._visibility_guard_timer)
        self._visibility_guard_timer.Start(100)  # 每100ms检查一次，确保快速恢复
        
        # 检查是否在交易时间，如果闭市则不启动超时检测
        from ..utils.helpers import is_trading_time
        if is_trading_time():
            self._timeout_timer.Start(10000, wx.TIMER_ONE_SHOT)  # 10秒后触发一次
        self._data_loaded = False
        
        # 立即刷新显示，确保初始状态可见
        self._update_display()
        
        self._logger.info("Floating window initialized at bottom-right corner")
    
    def _create_ui(self):
        self._panel = wx.Panel(self, style=wx.BORDER_SIMPLE)

        self._font_size = self._calculate_font_size(self._window_height)
        base_font = wx.Font(self._font_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)

        self._line_label = wx.StaticText(self._panel, label="正在加载 ETF 数据...", style=wx.ALIGN_CENTER)
        self._line_label.SetFont(base_font)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self._line_label, 1, wx.ALIGN_CENTER | wx.ALL, 10)

        self._panel.SetSizer(vbox)

        self._panel.SetBackgroundColour(wx.Colour(240, 248, 255))
        self._line_label.SetForegroundColour(wx.Colour(0, 0, 0))

        self._panel.SetMinSize(wx.Size(self._min_width, self._min_height))
        frame_sizer = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Add(self._panel, 1, wx.EXPAND)
        self.SetSizer(frame_sizer)
        self.Layout()
        self._sync_window_size()
    
    def _get_client_position(self, event) -> wx.Point:
        """获取事件相对于窗口客户区的位置。"""
        obj = event.GetEventObject()
        if isinstance(obj, wx.Window):
            screen_pos = obj.ClientToScreen(event.GetPosition())
            return self.ScreenToClient(screen_pos)
        return event.GetPosition()

    def _get_screen_position(self, event) -> wx.Point:
        """获取事件的屏幕坐标。"""
        obj = event.GetEventObject()
        if isinstance(obj, wx.Window):
            return obj.ClientToScreen(event.GetPosition())
        return self.ClientToScreen(event.GetPosition())

    def _get_resize_direction(self, client_pos: wx.Point) -> str:
        """
        判断鼠标位置对应的调整方向。
        
        Returns:
            方向字符串: 'N', 'S', 'E', 'W', 'NE', 'NW', 'SE', 'SW', 或空字符串
        """
        client_width, client_height = self.GetClientSize()
        x, y = client_pos.x, client_pos.y
        margin = self._resize_margin
        
        # 判断是否在边缘区域
        at_left = x <= margin
        at_right = x >= client_width - margin
        at_top = y <= margin
        at_bottom = y >= client_height - margin
        
        # 角优先（同时在两个边缘）
        if at_top and at_left:
            return 'NW'
        elif at_top and at_right:
            return 'NE'
        elif at_bottom and at_left:
            return 'SW'
        elif at_bottom and at_right:
            return 'SE'
        # 边
        elif at_top:
            return 'N'
        elif at_bottom:
            return 'S'
        elif at_left:
            return 'W'
        elif at_right:
            return 'E'
        
        return ''
    
    def _get_cursor_type_for_direction(self, direction: str) -> int:
        """根据调整方向获取对应的鼠标光标类型。"""
        cursor_map = {
            'N': wx.CURSOR_SIZENS,
            'S': wx.CURSOR_SIZENS,
            'E': wx.CURSOR_SIZEWE,
            'W': wx.CURSOR_SIZEWE,
            'NE': wx.CURSOR_SIZENESW,
            'SW': wx.CURSOR_SIZENESW,
            'NW': wx.CURSOR_SIZENWSE,
            'SE': wx.CURSOR_SIZENWSE,
        }
        return cursor_map.get(direction, wx.CURSOR_ARROW)

    def _set_cursor(self, cursor_type: int) -> None:
        """同步设置窗口及子控件的鼠标光标。"""
        cursor = self._cursor_cache.get(cursor_type)
        if cursor is None:
            cursor = wx.Cursor(cursor_type)
            self._cursor_cache[cursor_type] = cursor
        for target in (self, getattr(self, '_panel', None), getattr(self, '_name_label', None), getattr(self, '_price_label', None), getattr(self, '_percent_label', None)):
            if isinstance(target, wx.Window):
                target.SetCursor(cursor)

    def _set_cursor_for_direction(self, direction: str) -> None:
        cursor_type = self._get_cursor_type_for_direction(direction)
        self._set_cursor(cursor_type)

    def _calculate_font_size(self, window_height: int) -> int:
        font_size = int(max(window_height, 1) * 0.45)
        lower = getattr(self, '_min_point_size', 8)
        return max(lower, min(32, font_size))
    
    def _update_font_size(self) -> None:
        new_font_size = self._calculate_font_size(self._window_height)
        if new_font_size != self._font_size:
            self._font_size = new_font_size
            font = wx.Font(self._font_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
            if hasattr(self, '_line_label'):
                self._line_label.SetFont(font)

    def _update_layout_metrics(self) -> None:
        padding = max(2, min(10, int(max(self._window_height, 1) * 0.15)))
        self._current_padding = padding
        sizer = self._panel.GetSizer()
        if sizer:
            # 通过调整 sizer 中各项的边距确保不贴边
            for i in range(sizer.GetItemCount()):
                item = sizer.GetItem(i)
                if item:
                    item.SetBorder(padding)
            sizer.Layout()

    def _ensure_text_fits(self) -> None:
        """确保文本在当前窗口尺寸下完整显示。"""
        if not hasattr(self, '_line_label'):
            return
        panel_size = self._panel.GetClientSize()
        avail_w = max(1, panel_size.GetWidth() - self._current_padding * 2)
        avail_h = max(1, panel_size.GetHeight() - self._current_padding * 2)
        dc = wx.ClientDC(self._panel)
        base_font = wx.Font(self._font_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        dc.SetFont(base_font)

        def fit_label(label: wx.StaticText, text: str, max_w: int, max_h: int, min_pt: int) -> int:
            size_pt = self._font_size
            dc.SetFont(wx.Font(size_pt, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            w, h = dc.GetTextExtent(text)
            while (w > max_w or h > max_h) and size_pt > min_pt:
                size_pt -= 1
                dc.SetFont(wx.Font(size_pt, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                w, h = dc.GetTextExtent(text)
            label.SetFont(wx.Font(size_pt, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            return size_pt

        min_pt = self._min_point_size

        line_text = self._line_label.GetLabel() or ""
        self._line_label.Wrap(-1)
        line_pt = fit_label(self._line_label, line_text, avail_w, avail_h, min_pt)
        self._font_size = line_pt
        sizer = self._panel.GetSizer()
        if sizer:
            sizer.Layout()

    def _relayout_components(self) -> None:
        self._update_font_size()
        self._update_layout_metrics()
        self._ensure_text_fits()
    
    def _apply_size(self, width: int, height: int, reposition: bool = False) -> None:
        """应用窗口尺寸并刷新布局。"""
        width = max(self._min_width, int(width))
        height = max(self._min_height, int(height))
        self.SetSize(wx.Size(width, height))
        self._sync_window_size()
        # 更新字体大小
        self._update_font_size()
        self._update_layout_metrics()
        self._ensure_text_fits()
        self.Layout()
        if reposition:
            self._position_bottom_right()

    def _reset_position(self):
        """重置窗口到右下角。"""
        self._position_bottom_right()
        self._logger.info("Window position reset to bottom-right corner")
    
    def _position_bottom_right(self):
        """定位窗口到屏幕右下角（时钟上方）。"""
        screen_width, screen_height = wx.GetDisplaySize()
        width, height = self.GetSize()
        
        # 计算右下角坐标（留出边距）
        x = screen_width - width - 10
        y = screen_height - height - 10
        
        self.SetPosition(wx.Point(int(x), int(y)))
    
    def _reset_size(self):
        """重置窗口尺寸。"""
        width, height = self._base_default_size
        self.SetSize(wx.Size(width, height))
        self._window_width = width
        self._window_height = height
        self._sync_window_size()
        self._logger.info(f"Window size reset to {width}x{height}")
    
    def _sync_window_size(self):
        """同步窗口尺寸到内部变量。"""
        size = self.GetSize()
        self._window_width = size.width
        self._window_height = size.height

    def _ensure_always_on_top(self):
        """确保窗口始终置顶（使用多种方法组合）。"""
        try:
            # 方法1: 使用 Raise() 提升窗口
            self.Raise()
            
            # 方法2: 重新设置窗口样式（强制应用STAY_ON_TOP）
            current_style = self.GetWindowStyle()
            # 先移除STAY_ON_TOP，再重新添加（强制刷新）
            if current_style & wx.STAY_ON_TOP:
                self.SetWindowStyle(current_style & ~wx.STAY_ON_TOP)
            self.SetWindowStyle(current_style | wx.STAY_ON_TOP)
            
            # 方法3: 再次调用Raise()确保生效
            self.Raise()
            
            self._logger.debug("Window raised to always on top")
        except Exception as e:
            self._logger.warning(f"Failed to ensure always on top: {e}")
    
    def _bind_events(self):
        """绑定事件。"""
        # 鼠标拖动/缩放事件绑定到窗口及子控件
        for widget in (self, self._panel, getattr(self, '_line_label', None)):
            widget.Bind(wx.EVT_LEFT_DOWN, self._on_left_down)
            widget.Bind(wx.EVT_LEFT_UP, self._on_left_up)
            widget.Bind(wx.EVT_MOTION, self._on_mouse_move)
            widget.Bind(wx.EVT_LEAVE_WINDOW, self._on_mouse_leave)
            widget.Bind(wx.EVT_ENTER_WINDOW, self._on_mouse_enter)  # 鼠标进入时置顶

        # 鼠标捕获丢失
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self._on_capture_lost)
        self._panel.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self._on_capture_lost)
        if hasattr(self, '_line_label'):
            self._line_label.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self._on_capture_lost)
        
        # 右键菜单
        self._panel.Bind(wx.EVT_RIGHT_DOWN, self._on_right_click)
        if hasattr(self, '_line_label'):
            self._line_label.Bind(wx.EVT_RIGHT_DOWN, self._on_right_click)
        
        # 双击隐藏
        self._panel.Bind(wx.EVT_LEFT_DCLICK, self._on_double_click)
        if hasattr(self, '_line_label'):
            self._line_label.Bind(wx.EVT_LEFT_DCLICK, self._on_double_click)
        
        # 绑定关闭事件，阻止销毁，改为隐藏
        self.Bind(wx.EVT_CLOSE, self._on_close)
        
        # 监听窗口显示/隐藏事件，防止意外隐藏
        self.Bind(wx.EVT_SHOW, self._on_show_event)
        self.Bind(wx.EVT_SIZE, lambda e: (self._relayout_components(), e.Skip()))
    
    def update_data(self, etf_data: Dict[str, ETFQuote], changed_codes: Optional[list] = None):
        """
        更新 ETF 数据。
        
        Args:
            etf_data: ETF 数据字典
            changed_codes: 价格有变化的ETF代码列表（可选）
        """
        self._etf_data = etf_data.copy()
        self._etf_codes = list(etf_data.keys())
        
        # 如果提供了变化列表，只轮播有变化的ETF
        if changed_codes:
            self._changed_etf_codes = [code for code in changed_codes if code in etf_data]
            self._logger.info(f"[智能轮播] 接收到 {len(self._etf_codes)} 个ETF，其中 {len(self._changed_etf_codes)} 个有变化")
            if self._changed_etf_codes:
                self._logger.info(f"[智能轮播] 有变化的ETF: {', '.join(self._changed_etf_codes)}")
        else:
            # 否则轮播所有ETF
            self._changed_etf_codes = list(etf_data.keys())
            self._logger.debug(f"[智能轮播] 未提供变化列表，轮播所有 {len(self._changed_etf_codes)} 个ETF")
        
        # 如果当前轮播列表为空，回退到全部
        if not self._changed_etf_codes:
            self._changed_etf_codes = list(etf_data.keys())
            self._logger.warning(f"[智能轮播] 无变化ETF，回退到轮播全部 {len(self._changed_etf_codes)} 个")
        
        # 标记数据已加载
        if not self._data_loaded and etf_data:
            self._data_loaded = True
            if self._timeout_timer is not None:
                self._timeout_timer.Stop()  # 停止超时检测
            self._logger.info(f"[数据加载] 悬浮窗首次数据加载成功: {len(self._etf_codes)} 个ETF")
        
        # 更新显示
        self._update_display()
    
    def start_rotation(self):
        """开始轮播。"""
        if self._rotation_timer is not None and not self._rotation_timer.IsRunning():
            self._rotation_timer.Start(self._rotation_interval * 1000)
            self._logger.info(f"Rotation started: {self._rotation_interval}s interval")
    
    def stop_rotation(self):
        """停止轮播。"""
        if self._rotation_timer is not None and self._rotation_timer.IsRunning():
            self._rotation_timer.Stop()
            self._logger.info("Rotation stopped")
    
    def _on_rotation_timer(self, event):
        """轮播定时器触发。"""
        from ..utils.helpers import is_trading_time
        
        # 闭市时停止轮播
        if not is_trading_time():
            self._logger.debug(f"[轮播控制] 闭市时段，停止轮播")
            return
        
        if self._changed_etf_codes:
            old_index = self._current_index
            self._current_index = (self._current_index + 1) % len(self._changed_etf_codes)
            code = self._changed_etf_codes[self._current_index]
            self._logger.debug(f"[轮播控制] 索引 {old_index} → {self._current_index}，显示 {code}")
            self._update_display()
    
    def _on_timeout_check(self, event):
        """数据加载超时检查。"""
        if not self._data_loaded:
            self._logger.warning("Data loading timeout - no data received after 10 seconds")
            self._line_label.SetLabel("数据加载超时 请检查网络连接")
            self._panel.SetBackgroundColour(wx.Colour(255, 200, 150))
            self._line_label.SetForegroundColour(wx.Colour(139, 0, 0))
            self._panel.Refresh()
    
    def _on_visibility_guard(self, event):
        """窗口可见性和层级守护，防止意外隐藏或被遮挡。"""
        try:
            # 如果守护被暂停（如托盘菜单显示时），跳过守护
            if self._guard_paused:
                return
            
            # 检查1: 如果窗口不可见且不是用户主动隐藏的，自动恢复显示
            if not self.IsShown() and not self._user_hidden:
                self._logger.warning("[窗口守护] 窗口意外隐藏，正在恢复显示")
                self.Show(True)
                self._ensure_always_on_top()
            
            # 检查2: 如果窗口可见但不是用户主动隐藏，强制保持在最顶层
            # 使用强力方法对抗任务栏等系统窗口
            elif self.IsShown() and not self._user_hidden:
                # 每次都强制提升（对抗工具栏右键菜单）
                self.Raise()
                
                # 每10次守护（约1秒）重新设置一次窗口样式，确保STAY_ON_TOP生效
                if not hasattr(self, '_guard_counter'):
                    self._guard_counter = 0
                self._guard_counter += 1
                
                if self._guard_counter >= 10:  # 每1秒
                    self._guard_counter = 0
                    current_style = self.GetWindowStyle()
                    if current_style & wx.STAY_ON_TOP:
                        # 强制刷新STAY_ON_TOP样式
                        self.SetWindowStyle(current_style & ~wx.STAY_ON_TOP)
                        self.SetWindowStyle(current_style | wx.STAY_ON_TOP)
                        self.Raise()
                        self._logger.debug("[窗口守护] 强制刷新STAY_ON_TOP样式")
                
        except Exception as e:
            self._logger.error(f"[窗口守护] 守护定时器异常: {e}")
    
    def _update_display(self):
        """更新显示内容。"""
        # 在开头添加闭市检测
        from ..utils.helpers import is_trading_time, get_next_trading_time
        
        if not is_trading_time():
            trading_status = get_next_trading_time()
            self._line_label.SetLabel("已收盘")
            self._panel.SetBackgroundColour(wx.Colour(200, 200, 200))
            self._line_label.SetForegroundColour(wx.Colour(80, 80, 80))
            self._panel.Refresh()
            self._relayout_components()
            self._logger.debug(f"[显示更新] 闭市状态: {trading_status}")
            return
        
        if not self._changed_etf_codes or not self._etf_data:
            # 显示更明显的加载提示
            self._line_label.SetLabel("正在获取数据...")
            self._panel.SetBackgroundColour(wx.Colour(255, 250, 205))
            self._line_label.SetForegroundColour(wx.Colour(0, 0, 0))
            self._panel.Refresh()
            self._relayout_components()
            self._logger.debug("No data available yet")
            return
        
        # 确保索引有效
        if self._current_index >= len(self._changed_etf_codes):
            self._current_index = 0
        
        code = self._changed_etf_codes[self._current_index]  # 改用变化列表
        quote = self._etf_data.get(code)
        
        if not quote:
            # 数据项不存在，显示错误提示
            self._line_label.SetLabel(f"数据错误: {code}")
            self._panel.SetBackgroundColour(wx.Colour(255, 230, 230))
            self._line_label.SetForegroundColour(wx.Colour(180, 0, 0))
            self._panel.Refresh()
            self._logger.warning(f"Quote data not found for {code}")
            return
        
        try:
            p = quote.change_percent or 0.0
            percent_text = (f"+{p:.2f}%" if p > 0 else (f"-{abs(p):.2f}%" if p < 0 else "0.00%"))
            price_text = f"{quote.price:.2f}"

            self._line_label.SetLabel(f"{quote.name} {price_text} {percent_text}")
            self._relayout_components()
            
            # 根据涨跌设置颜色（更鲜明的颜色）
            if quote.change_percent > 0:
                self._panel.SetBackgroundColour(wx.Colour(255, 200, 200))
                fg = wx.Colour(180, 0, 0)
            elif quote.change_percent < 0:
                self._panel.SetBackgroundColour(wx.Colour(200, 255, 200))
                fg = wx.Colour(0, 100, 0)
            else:
                self._panel.SetBackgroundColour(wx.Colour(255, 255, 255))
                fg = wx.Colour(0, 0, 0)
            self._line_label.SetForegroundColour(fg)
            
            # 强制刷新显示
            self._panel.Refresh()
            self._panel.Update()
            
            # 确保窗口保持在最顶层
            self.Raise()
            
            self._logger.debug("Display updated")
            
        except Exception as e:
            self._logger.error(f"Error updating display: {e}", exc_info=True)
            self._line_label.SetLabel("显示错误")
            self._panel.SetBackgroundColour(wx.Colour(255, 230, 230))
            self._line_label.SetForegroundColour(wx.Colour(180, 0, 0))
            self._panel.Refresh()
    
    def _on_left_down(self, event):
        """鼠标左键按下 - 开始拖动或缩放。"""
        client_pos = self._get_client_position(event)
        screen_pos = self._get_screen_position(event)
        direction = self._get_resize_direction(client_pos)
        
        if direction:
            # 开始调整大小
            self._resizing = True
            self._resize_direction = direction
            self._resize_start_pos = screen_pos
            self._window_start_size = self.GetSize()
            self._window_start_pos_for_resize = self.GetPosition()
            self._set_cursor_for_direction(direction)
        else:
            # 开始拖动
            self._dragging = True
            self._drag_start_pos = screen_pos
            self._window_start_pos = self.GetPosition()
            self._set_cursor(wx.CURSOR_HAND)
        
        if not self.HasCapture():
            self.CaptureMouse()
        event.Skip()
    
    def _on_left_up(self, event):
        """鼠标左键释放 - 结束拖动/缩放。"""
        if self._dragging or self._resizing:
            self._dragging = False
            self._resizing = False
            self._drag_start_pos = None
            self._window_start_pos = None
            self._resize_direction = ''
            self._resize_start_pos = None
            self._window_start_size = None
            self._window_start_pos_for_resize = None
            self._set_cursor(wx.CURSOR_ARROW)
            if self.HasCapture():
                self.ReleaseMouse()
        event.Skip()
    
    def _on_mouse_move(self, event):
        """鼠标移动 - 拖动或缩放窗口。"""
        client_pos = self._get_client_position(event)
        
        if self._resizing and self._window_start_size and self._resize_start_pos:
            # 调整大小模式
            current_screen_pos = self._get_screen_position(event)
            if current_screen_pos and self._resize_start_pos:
                delta_x = current_screen_pos.x - self._resize_start_pos.x
                delta_y = current_screen_pos.y - self._resize_start_pos.y
                
                # 获取起始尺寸和位置
                start_width, start_height = self._window_start_size
                start_x, start_y = self._window_start_pos_for_resize or (0, 0)
                
                # 根据调整方向计算新尺寸和位置
                new_width = start_width
                new_height = start_height
                new_x = start_x
                new_y = start_y
                
                # 水平调整
                if 'E' in self._resize_direction:
                    new_width = max(self._min_width, start_width + delta_x)
                elif 'W' in self._resize_direction:
                    new_width = max(self._min_width, start_width - delta_x)
                    new_x = start_x + delta_x
                
                # 垂直调整
                if 'S' in self._resize_direction:
                    new_height = max(self._min_height, start_height + delta_y)
                elif 'N' in self._resize_direction:
                    new_height = max(self._min_height, start_height - delta_y)
                    new_y = start_y + delta_y
                
                # 应用新尺寸和位置
                self.SetSize(wx.Size(int(new_width), int(new_height)))
                self.SetPosition(wx.Point(int(new_x), int(new_y)))
                
                # 更新内部尺寸变量
                self._window_width = int(new_width)
                self._window_height = int(new_height)
                
                # 重新计算字体大小和内边距
                self._font_size = self._calculate_font_size(self._window_height)
                self._current_padding = max(2, min(10, int(self._window_height * 0.15)))
                
                # 更新字体
                font = wx.Font(self._font_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
                if hasattr(self, '_line_label'):
                    self._line_label.SetFont(font)
                
                # 更新布局
                self._panel.Layout()
                self.Layout()
                self._relayout_components()
            
        elif self._dragging and self._drag_start_pos and self._window_start_pos:
            # 拖动模式
            current_screen_pos = self._get_screen_position(event)
            if current_screen_pos and self._drag_start_pos:
                delta_x = current_screen_pos.x - self._drag_start_pos.x
                delta_y = current_screen_pos.y - self._drag_start_pos.y
                
                new_x = self._window_start_pos.x + delta_x
                new_y = self._window_start_pos.y + delta_y
                
                # 限制窗口位置在屏幕范围内
                screen_width, screen_height = wx.GetDisplaySize()
                window_width, window_height = self.GetSize()
                
                new_x = max(0, min(new_x, screen_width - window_width))
                new_y = max(0, min(new_y, screen_height - window_height))
                
                self.SetPosition(wx.Point(int(new_x), int(new_y)))
        
        else:
            # 正常鼠标移动 - 显示相应光标
            direction = self._get_resize_direction(client_pos)
            if direction:
                self._set_cursor_for_direction(direction)
            else:
                self._set_cursor(wx.CURSOR_ARROW)
        
        event.Skip()

    def _on_mouse_enter(self, event):
        """鼠标进入窗口区域 - 确保窗口置顶。"""
        # 鼠标进入时，确保窗口在最顶层（防止被任务栏遮挡）
        if not self._user_hidden:
            self.Raise()
        event.Skip()
    
    def _on_mouse_leave(self, event):
        """鼠标离开窗口区域。"""
        if not self._dragging and not self._resizing:
            self._set_cursor(wx.CURSOR_ARROW)
        event.Skip()

    def _on_capture_lost(self, event):
        """鼠标捕获丢失时重置状态。"""
        self._logger.debug("Mouse capture lost")
        self._dragging = False
        self._resizing = False
        self._resize_direction = ''
        self._resize_start_pos = None
        self._window_start_size = None
        self._window_start_pos_for_resize = None
        if self.HasCapture():
            try:
                self.ReleaseMouse()
            except Exception:
                pass
        self._set_cursor(wx.CURSOR_ARROW)
        event.Skip()
    
    def _on_double_click(self, event):
        """双击隐藏窗口。"""
        self._user_hidden = True  # 标记为用户主动隐藏
        self.Hide()
        self._logger.info("Floating window hidden by double-click")
    
    def _on_close(self, event):
        """Handle window close - hide instead of destroy."""
        self._user_hidden = True  # 标记为用户主动隐藏
        self.Hide()
        self._logger.info("Floating window closed, hiding instead of destroying")
    
    def _on_show_event(self, event):
        """监听窗口显示/隐藏事件。"""
        is_shown = event.IsShown()
        
        if not is_shown and not self._user_hidden:
            # 窗口被意外隐藏（不是用户主动隐藏）
            self._logger.warning("Floating window unexpectedly hidden (possibly by system event)")
        
        # 事件必须Skip，否则会影响正常显示逻辑
        event.Skip()
    
    def _on_right_click(self, event):
        """右键菜单。"""
        menu = wx.Menu()
        
        # 重置到右下角
        reset_item = menu.Append(wx.ID_ANY, "重置到右下角")
        menu.Bind(wx.EVT_MENU, lambda e: self._position_bottom_right(), reset_item)
        # 重置尺寸
        reset_size_item = menu.Append(wx.ID_ANY, "重置尺寸")
        menu.Bind(wx.EVT_MENU, lambda e: self._reset_size(), reset_size_item)
        
        menu.AppendSeparator()
        
        # 透明度
        transparency_menu = wx.Menu()
        for value, label in [(255, "不透明"), (230, "轻微透明"), (200, "半透明"), (150, "透明")]:
            item = transparency_menu.Append(wx.ID_ANY, label)
            menu.Bind(wx.EVT_MENU, lambda e, v=value: self._set_transparency(v), item)
        menu.AppendSubMenu(transparency_menu, "透明度")
        
        menu.AppendSeparator()
        
        # 隐藏
        hide_item = menu.Append(wx.ID_ANY, "隐藏悬浮窗")
        menu.Bind(wx.EVT_MENU, self._on_menu_hide, hide_item)
        
        # 显示菜单
        self._panel.PopupMenu(menu)
        menu.Destroy()
    
    def _on_menu_hide(self, event):
        """从菜单隐藏窗口。"""
        self._user_hidden = True  # 标记为用户主动隐藏
        self.Hide()
        self._logger.info("Floating window hidden from menu")
    
    def _set_transparency(self, value):
        """设置透明度。"""
        self._transparency = value
        self.SetTransparent(value)
        self._logger.info(f"Transparency set to {value}")
    
    def update_settings(self, font_size=None, transparency=None, rotation_interval=None):
        """
        更新设置。
        
        Args:
            font_size: 字体大小
            transparency: 透明度
            rotation_interval: 轮播间隔
        """
        if font_size is not None and font_size != self._font_size:
            self._font_size = font_size
            font = wx.Font(font_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
            if hasattr(self, '_line_label'):
                self._line_label.SetFont(font)
            self._panel.Layout()
            self._relayout_components()
        
        if transparency is not None:
            self._set_transparency(transparency)
        
        if rotation_interval is not None and rotation_interval != self._rotation_interval:
            self._rotation_interval = rotation_interval
            if self._rotation_timer is not None and self._rotation_timer.IsRunning():
                self.stop_rotation()
                self.start_rotation()
    
    def get_position_config(self):
        """
        获取当前位置配置。
        
        Returns:
            位置元组 (x, y)
        """
        pos = self.GetPosition()
        return (pos.x, pos.y)
    
    def get_size_config(self) -> Tuple[int, int]:
        """获取当前尺寸配置。"""
        self._sync_window_size()
        return (self._window_width, self._window_height)
    
    def Show(self, show=True):
        """重写 Show 方法，确保显示时置顶。"""
        if show:
            # 显示窗口时重置隐藏标志
            self._user_hidden = False
        
        result = super().Show(show)
        if show:
            # 显示窗口时确保置顶
            self._ensure_always_on_top()
        return result
    
    def pause_guard(self):
        """暂停窗口守护（用于显示菜单等场景，避免抢占焦点）。"""
        self._guard_paused = True
        self._logger.info("[窗口守护] 守护已暂停（托盘菜单打开）")
    
    def resume_guard(self):
        """恢复窗口守护。"""
        self._guard_paused = False
        self._logger.info("[窗口守护] 守护已恢复（托盘菜单关闭）")
    
    def cleanup(self):
        """清理资源。"""
        self.stop_rotation()
        if self._timeout_timer is not None and self._timeout_timer.IsRunning():
            self._timeout_timer.Stop()
        if self._visibility_guard_timer is not None and self._visibility_guard_timer.IsRunning():
            self._visibility_guard_timer.Stop()
        if self.HasCapture():
            self.ReleaseMouse()
        
        # 清理所有定时器引用
        self._rotation_timer = None
        self._timeout_timer = None
        self._visibility_guard_timer = None
    
    def Destroy(self):
        """重写Destroy方法确保资源被正确释放。"""
        try:
            # 先清理所有定时器
            self.cleanup()
            
            # 停止所有可能仍在运行的定时器
            import wx
            wx.Yield()  # 处理所有待处理的事件
        except:
            pass
            
        # 调用父类的Destroy方法
        return super().Destroy()
