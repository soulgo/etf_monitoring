#!/usr/bin/env python3
"""
ETF Monitor - Main Entry Point

Real-time ETF price monitoring with system tray integration.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.app import ETFMonitorApp
from src.config.manager import get_config
from src.utils.logger import setup_logger, get_logger


def main():
    """
    Main entry point for ETF Monitor application.
    
    Workflow:
    1. Setup logging
    2. Load configuration
    3. Initialize wxPython app
    4. Enter main event loop
    """
    # Setup logging early
    logger = setup_logger()
    
    try:
        # Load configuration
        config = get_config()
        if not config.load():
            logger.warning("Failed to load configuration, using defaults")
        
        # Create and run application
        app = ETFMonitorApp(False)
        app.MainLoop()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
        
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        
        # Try to show error dialog if wx available
        try:
            import wx
            app = wx.App(False)
            wx.MessageBox(
                f"程序发生严重错误：\n{e}\n\n请查看日志文件了解详情",
                "错误",
                wx.OK | wx.ICON_ERROR
            )
        except:
            pass
        
        sys.exit(1)


if __name__ == '__main__':
    main()

