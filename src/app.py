"""
Main application class orchestrating all components.

Manages application lifecycle, component initialization, and graceful shutdown.
"""

import sys
import wx

from .config.manager import get_config
from .data.api_adapter import APIAdapterFactory
from .data.fetcher import DataFetcher
from .data.cache import CacheManager
from .ui.tray_icon import ETFTrayIcon
from .ui.settings_dialog import SettingsDialog
from .ui.detail_window import DetailWindow
from .ui.about_dialog import AboutDialog
from .ui.floating_window import FloatingWindow
from .utils.logger import setup_logger, get_logger


class ETFMonitorApp(wx.App):
    """
    Main application class.
    
    Responsibilities:
    - Initialize all components
    - Manage component lifecycle
    - Handle inter-component communication
    - Graceful shutdown
    """
    
    def OnInit(self):
        """
        Initialize application.
        
        Returns:
            True if initialization successful
        """
        # Setup logging first
        config = get_config()
        log_level = config.get('log_level', 'INFO')
        self.logger = setup_logger(log_level=getattr(__import__('logging'), log_level))
        
        self.logger.info("=" * 60)
        self.logger.info("ETF Monitor v1.2.0 Starting")
        self.logger.info("=" * 60)
        
        # Check single instance
        if config.get('advanced.single_instance', True):
            self.instance_checker = wx.SingleInstanceChecker("ETFMonitor")
            if self.instance_checker.IsAnotherRunning():
                wx.MessageBox(
                    "ETF 监控工具已经在运行中",
                    "程序已运行",
                    wx.OK | wx.ICON_WARNING
                )
                return False
        
        # Initialize components
        try:
            self._init_components()
        except Exception as e:
            self.logger.critical(f"Failed to initialize components: {e}", exc_info=True)
            wx.MessageBox(
                f"初始化失败：{e}\n请查看日志文件",
                "启动失败",
                wx.OK | wx.ICON_ERROR
            )
            return False
        
        # Start background services
        self._start_services()
        
        self.logger.info("Application initialized successfully")
        return True
    
    def _init_components(self) -> None:
        """Initialize all application components."""
        # Get configuration
        self.config = get_config()
        
        # Initialize cache manager
        cache_expire = self.config.get('advanced.data_cache_expire', 300)
        self.cache_manager = CacheManager(cache_expire_seconds=cache_expire)
        self.logger.info("Cache manager initialized")
        
        # Initialize API adapters
        api_config = self.config.get('api_config', {})
        
        # Primary adapter
        primary_config = api_config.get('primary', {})
        self.primary_adapter = APIAdapterFactory.create(
            primary_config.get('name', 'eastmoney'),
            primary_config.get('base_url', ''),
            primary_config.get('timeout', 5)
        )
        
        # Backup adapters
        self.backup_adapters = []
        for backup_config in api_config.get('backup', []):
            if backup_config.get('enabled', True):
                adapter = APIAdapterFactory.create(
                    backup_config.get('name', ''),
                    backup_config.get('base_url', ''),
                    backup_config.get('timeout', 5)
                )
                if adapter:
                    self.backup_adapters.append(adapter)
        
        self.logger.info(
            f"API adapters initialized: 1 primary, {len(self.backup_adapters)} backup"
        )
        
        # Initialize data fetcher
        etf_list = self.config.get('etf_list', [])
        refresh_interval = self.config.get('refresh_interval', 5)
        retry_count = api_config.get('retry_count', 3)
        retry_interval = api_config.get('retry_interval', 1)
        failover_threshold = api_config.get('failover_threshold', 3)
        
        # 确保primary_adapter不为None
        if self.primary_adapter is None:
            raise RuntimeError("Failed to initialize primary API adapter")
        
        self.data_fetcher = DataFetcher(
            etf_codes=etf_list,
            primary_adapter=self.primary_adapter,
            backup_adapters=self.backup_adapters,
            cache_manager=self.cache_manager,
            refresh_interval=refresh_interval,
            retry_count=retry_count,
            retry_interval=retry_interval,
            failover_threshold=failover_threshold,
            data_callback=self._on_data_updated
        )
        self.logger.info(f"Data fetcher initialized: {len(etf_list)} ETFs")
        
        # Initialize tray icon
        display_config = self.config.get('display_config', {})
        self.tray_icon = ETFTrayIcon(
            icon_path="resources/icons/tray.ico",
            tooltip_format=display_config.get('tooltip_format', ''),
            rotation_interval=self.config.get('rotation_interval', 3),
            rotation_mode=self.config.get('rotation_mode', 'both')
        )
        
        # Set tray icon callbacks
        self.tray_icon.set_on_settings(self._on_show_settings)
        self.tray_icon.set_on_detail(self._on_show_detail)
        self.tray_icon.set_on_about(self._on_show_about)
        self.tray_icon.set_on_refresh(self._on_manual_refresh)
        self.tray_icon.set_on_pause(self._on_pause_toggle)
        self.tray_icon.set_on_auto_start(self._on_auto_start_toggle)
        self.tray_icon.set_on_exit(self._on_exit)
        self.tray_icon.set_on_menu_open(self._on_tray_menu_open)
        self.tray_icon.set_on_menu_close(self._on_tray_menu_close)
        
        self.logger.info("Tray icon initialized")
        
        # Initialize windows (but don't show)
        self.detail_window = None
        self.settings_dialog = None
        
        # Initialize floating window
        floating_config = self.config.get('floating_window', {})
        if floating_config.get('enabled', True):
            position = tuple(floating_config.get('position', [100, 100]))
            window_size = tuple(floating_config.get('size', [350, 60]))
            font_size = floating_config.get('font_size', 18)
            transparency = floating_config.get('transparency', 200)
            
            self.floating_window = FloatingWindow(
                position=position,
                window_size=window_size,
                font_size=font_size,
                transparency=transparency,
                rotation_interval=self.config.get('rotation_interval', 3)
            )
            self.floating_window.Show()
            self.logger.info("Floating window initialized and shown")
        else:
            self.floating_window = None
            self.logger.info("Floating window disabled in config")
    
    def _start_services(self) -> None:
        """Start background services."""
        # Start data fetcher
        self.data_fetcher.daemon = True
        self.data_fetcher.start()
        
        # Trigger immediate refresh to load initial data quickly
        self.logger.info("Triggering initial data refresh...")
        self.data_fetcher.trigger_refresh()
        
        # Start tray icon rotation
        self.tray_icon.start_rotation()
        
        # Start floating window rotation
        if self.floating_window:
            self.floating_window.start_rotation()
        
        self.logger.info("Background services started")
    
    def _on_data_updated(self, etf_data: dict, changed_codes: list) -> None:
        """
        Handle data update from fetcher.
        
        Args:
            etf_data: Dictionary of ETFQuote objects
            changed_codes: List of codes that changed
        """
        self.logger.info(f"Data callback triggered: {len(etf_data)} ETFs received, {len(changed_codes or [])} changed")
        
        # Log first ETF data for debugging
        if etf_data:
            first_code = list(etf_data.keys())[0]
            first_quote = etf_data[first_code]
            self.logger.info(f"Sample data: {first_quote.name} ({first_code}): {first_quote.price} ({first_quote.change_percent:+.2f}%)")
        else:
            self.logger.warning("Empty ETF data received in callback")
        
        # Update tray icon
        self.tray_icon.update_data(etf_data, changed_codes)
        
        # Update floating window
        if self.floating_window:
            try:
                self.floating_window.update_data(etf_data, changed_codes)  # 传递变化列表
                self.logger.info(f"Floating window updated successfully with {len(etf_data)} ETFs")
            except Exception as e:
                self.logger.error(f"Failed to update floating window: {e}", exc_info=True)
        else:
            self.logger.warning("Floating window is None, cannot update")
        
        # Update detail window if visible
        if self.detail_window and self.detail_window.IsShown():
            self.detail_window.update_data(etf_data)
    
    def _on_show_settings(self) -> None:
        """Show settings dialog."""
        if self.settings_dialog and self.settings_dialog.IsShown():
            self.settings_dialog.Raise()
            return
        
        self.settings_dialog = SettingsDialog(
            None,
            self.config,
            fetch_name_callback=self._fetch_etf_name
        )
        
        if self.settings_dialog.ShowModal() == wx.ID_OK:
            # Configuration saved, reload and restart services
            self.logger.info("Configuration updated, reloading...")
            self._reload_configuration()
        
        self.settings_dialog.Destroy()
        self.settings_dialog = None
    
    def _on_show_detail(self) -> None:
        """Show detail window."""
        if self.detail_window is None:
            self.detail_window = DetailWindow(None)
            self.detail_window.set_on_refresh(self._on_manual_refresh)
        
        # Update with current data
        etf_data = self.cache_manager.get_all()
        self.detail_window.update_data(etf_data)
        
        self.detail_window.Show()
        self.detail_window.Raise()
    
    def _on_show_about(self) -> None:
        """Show about dialog."""
        about = AboutDialog(None)
        about.ShowModal()
        about.Destroy()
    
    def _on_manual_refresh(self) -> None:
        """Trigger manual refresh."""
        self.logger.info("Manual refresh triggered")
        self.data_fetcher.trigger_refresh()
    
    def _on_pause_toggle(self, paused: bool) -> None:
        """
        Handle pause toggle.
        
        Args:
            paused: True if pausing, False if resuming
        """
        if paused:
            self.data_fetcher.pause()
            self.logger.info("Data fetching paused")
        else:
            self.data_fetcher.resume()
            self.logger.info("Data fetching resumed")
        
        self.tray_icon.set_paused(paused)
    
    def _on_auto_start_toggle(self) -> None:
        """Toggle auto start setting."""
        current = self.config.get('auto_start', False)
        new_value = not current
        
        self.config.set('auto_start', new_value)
        self.config.save()
        
        # TODO: Update Windows registry for auto-start
        # This would require winreg module on Windows
        
        self.logger.info(f"Auto start set to: {new_value}")
        
        wx.MessageBox(
            f"开机自启已{'启用' if new_value else '禁用'}\n"
            "注：需要以管理员权限运行才能修改注册表",
            "设置已更新",
            wx.OK | wx.ICON_INFORMATION
        )
    
    def _on_tray_menu_open(self) -> None:
        """Handle tray menu open - pause floating window guard."""
        if self.floating_window:
            self.floating_window.pause_guard()
            self.logger.info("[托盘菜单] 菜单打开，暂停悬浮窗守护")
    
    def _on_tray_menu_close(self) -> None:
        """Handle tray menu close - resume floating window guard."""
        if self.floating_window:
            self.floating_window.resume_guard()
            self.logger.info("[托盘菜单] 菜单关闭，恢复悬浮窗守护")
    
    def _on_exit(self) -> None:
        """Handle application exit."""
        # Prevent duplicate exit requests
        if hasattr(self, '_exit_in_progress') and self._exit_in_progress:
            self.logger.info("Exit already in progress, ignoring duplicate request")
            return
        
        self._exit_in_progress = True
        self.logger.info("Exit requested. Initiating shutdown.")
        
        # Execute shutdown and exit immediately without delay
        self._shutdown()
        self._do_exit()
    
    def _do_exit(self) -> None:
        """执行实际的退出操作。"""
        try:
            # 立即退出主循环
            self.ExitMainLoop()
        except Exception as e:
            self.logger.error(f"Error during exit: {e}")
            # 如果正常退出失败，强制退出
            import os
            os._exit(0)
    
    def _reload_configuration(self) -> None:
        """Reload configuration and restart services."""
        self.logger.info("[配置重载] 开始重新加载配置...")
        
        # Reload config
        self.config.reload()
        
        # Update ETF list
        etf_list = self.config.get('etf_list', [])
        self.data_fetcher.update_etf_list(etf_list)
        self.logger.info(f"[配置重载] ETF列表已更新: {len(etf_list)} 个 - {', '.join(etf_list)}")
        
        # Update refresh interval
        refresh_interval = self.config.get('refresh_interval', 5)
        self.data_fetcher.update_refresh_interval(refresh_interval)
        self.logger.info(f"[配置重载] 刷新间隔已更新: {refresh_interval}秒")
        
        # Update rotation settings
        rotation_interval = self.config.get('rotation_interval', 3)
        rotation_mode = self.config.get('rotation_mode', 'both')
        self.tray_icon.update_rotation_settings(rotation_interval, rotation_mode)
        self.logger.info(f"[配置重载] 轮播设置已更新: {rotation_interval}秒, 模式={rotation_mode}")
        
        # Control floating window display
        floating_enabled = self.config.get('floating_window.enabled', True)
        if self.floating_window:
            if floating_enabled:
                self.floating_window.Show()
                self.logger.info("[配置重载] 悬浮窗已显示")
            else:
                self.floating_window.Hide()
                self.logger.info("[配置重载] 悬浮窗已隐藏")
        
        self.logger.info("[配置重载] 配置重载完成")
    
    def _fetch_etf_name(self, code: str) -> str:
        """
        Fetch ETF name from cache or API.
        
        Args:
            code: ETF code
            
        Returns:
            ETF name or default
        """
        # First try to get from cache
        cached_quote = self.cache_manager.get(code)
        if cached_quote and cached_quote.name:
            return cached_quote.name
        
        # If not in cache, fetch from API
        try:
            # 确保primary_adapter不为None
            if self.primary_adapter is not None:
                quote = self.primary_adapter.fetch_quote(code)
                if quote and quote.name:
                    return quote.name
        except Exception as e:
            self.logger.warning(f"Failed to fetch name for {code}: {e}")
        
        return f"ETF{code}"

    def _shutdown(self) -> None:
        """Graceful shutdown of all services."""
        self.logger.info("Shutting down application...")
        
        try:
            # Stop data fetcher first to prevent new requests
            if hasattr(self, 'data_fetcher'):
                self.logger.info("Stopping data fetcher...")
                self.data_fetcher.stop()
            
            # Stop tray icon rotation
            if hasattr(self, 'tray_icon'):
                self.logger.info("Stopping tray icon rotation...")
                self.tray_icon.stop_rotation()
                self.tray_icon.RemoveIcon()
            
            # Stop and cleanup floating window
            if hasattr(self, 'floating_window') and self.floating_window:
                self.logger.info("Cleaning up floating window...")
                # Save position
                position = self.floating_window.get_position_config()
                size = self.floating_window.get_size_config()
                self.config.set('floating_window.position', list(position))
                self.config.set('floating_window.size', list(size))
                self.config.save()
                
                self.floating_window.cleanup()
                self.floating_window.Destroy()
            
            # Destroy tray icon
            if hasattr(self, 'tray_icon'):
                self.logger.info("Destroying tray icon...")
                self.tray_icon.Destroy()
            
            # Close API adapters
            if hasattr(self, 'primary_adapter') and self.primary_adapter is not None:
                self.logger.info("Closing primary adapter...")
                self.primary_adapter.close()
            
            if hasattr(self, 'backup_adapters'):
                self.logger.info("Closing backup adapters...")
                for adapter in getattr(self, 'backup_adapters', []):
                    try:
                        if adapter is not None:
                            adapter.close()
                    except Exception as e:
                        self.logger.error(f"Error closing adapter: {e}")
            
            # Close detail window
            if self.detail_window:
                self.logger.info("Destroying detail window...")
                self.detail_window.Destroy()
                
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}", exc_info=True)
        
        self.logger.info("=" * 60)
        self.logger.info("ETF Monitor Stopped")
        self.logger.info("=" * 60)
    
    def OnExit(self) -> int:
        """
        Called when application exits.
        
        Returns:
            Exit code
        """
        # 确保所有资源都被清理
        try:
            # 清理所有可能的定时器
            wx.Yield()  # 处理所有待处理的事件
            
            # 关闭所有HTTP客户端
            if hasattr(self, 'primary_adapter') and self.primary_adapter is not None:
                try:
                    self.primary_adapter.close()
                except:
                    pass
            
            if hasattr(self, 'backup_adapters'):
                for adapter in getattr(self, 'backup_adapters', []):
                    try:
                        if adapter is not None:
                            adapter.close()
                    except:
                        pass
            
            # 关闭所有HTTP连接
            import gc
            gc.collect()
            
        except Exception as e:
            self.logger.error(f"Error in OnExit: {e}")
        
        return 0

