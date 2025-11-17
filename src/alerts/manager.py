import time
from pathlib import Path
import wx

from ..data.models import ETFQuote
from ..ui.alert_popup import AlertPopup
from ..utils.logger import get_logger
from ..utils.helpers import is_call_auction_time

class AlertManager:
    def __init__(self, config):
        self._logger = get_logger(__name__)
        self._rules = {}
        symbols = config.get('symbols', [])
        for entry in symbols:
            if isinstance(entry, dict) and 'symbol' in entry:
                # Support both old (single value) and new (list) format
                up_th = entry.get('up_thresholds', entry.get('up_threshold', []))
                down_th = entry.get('down_thresholds', entry.get('down_threshold', []))
                
                # Convert single value to list for backward compatibility
                if isinstance(up_th, (int, float)):
                    up_th = [float(up_th)] if up_th > 0 else []
                elif not isinstance(up_th, list):
                    up_th = []
                
                if isinstance(down_th, (int, float)):
                    down_th = [float(down_th)] if down_th > 0 else []
                elif not isinstance(down_th, list):
                    down_th = []
                
                self._rules[entry['symbol']] = {
                    'up': up_th,
                    'down': down_th,
                    'dur': int(entry.get('duration_secs', 5))
                }
        self._last_alert = {}  # Key: (code, threshold_value, direction) -> timestamp
        self._min_interval = 30  # 多阈值场景下，30秒更合理
        self._log_path = Path('logs') / 'alerts.log'
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def evaluate(self, quotes: dict, changed_codes: list):
        """根据涨跌幅和用户设置的多个阈值触发弹窗告警。

        约定：
        - 配置里的 up_thresholds / down_thresholds 为阈值列表，如 [2.0, 3.0, 5.0] 表示 2%, 3%, 5%
        - 上涨告警：当前涨跌幅 >= +threshold（检查所有阈值）
        - 下跌告警：当前涨跌幅 <= -threshold（检查所有阈值）
        - 每个阈值独立追踪，避免重复触发
        
        注意：
        - 在集合竞价阶段（9:00-9:30, 14:57-15:00）不触发告警，因为数据可能不准确
        - 价格为0或过小时不触发告警，避免数据异常导致的误报
        """
        # 在集合竞价阶段不触发告警
        if is_call_auction_time():
            # 只在首次进入竞价阶段时记录一次日志，避免频繁输出
            if not hasattr(self, '_in_auction_logged') or not self._in_auction_logged:
                self._logger.info("[告警检查] 进入集合竞价/盘前准备阶段，暂停告警检查")
                self._in_auction_logged = True
            return
        else:
            # 离开竞价阶段时重置标志
            if hasattr(self, '_in_auction_logged') and self._in_auction_logged:
                self._logger.info("[告警检查] 离开集合竞价阶段，恢复告警检查")
                self._in_auction_logged = False
        
        now = time.time()
        for code, quote in quotes.items():
            rule = self._rules.get(code)
            if not rule:
                self._logger.debug(f"[告警检查] {code} 无告警规则，跳过")
                continue

            # 检查价格是否有效（避免价格为0或过小时触发告警）
            if quote.price is None or quote.price < 0.01:
                self._logger.debug(f"[告警检查] {code} 价格无效或为0 ({quote.price})，跳过告警检查")
                continue

            cp = quote.change_percent
            if cp is None:
                self._logger.debug(f"[告警检查] {code} 涨跌幅为None，跳过")
                continue

            # Get threshold lists
            up_thresholds = rule.get('up', [])
            down_thresholds = rule.get('down', [])
            
            # 使用INFO级别以便在默认日志配置下也能看到
            self._logger.info(
                f"[告警检查] {code} ({quote.name}): "
                f"价格={quote.price:.3f}, 涨跌幅={cp:+.2f}%, "
                f"上涨阈值={up_thresholds}, 下跌阈值={down_thresholds}"
            )
            
            # Check each up threshold
            for up_th in up_thresholds:
                up_th = abs(float(up_th))
                if up_th > 0 and cp >= up_th:
                    # Check if we already alerted for this specific threshold
                    alert_key = (code, up_th, '上涨')
                    last = self._last_alert.get(alert_key, 0)
                    if now - last >= self._min_interval:
                        self._logger.info(
                            f"[告警触发] {code} 上涨 {up_th}%: "
                            f"当前涨跌幅={cp:+.2f}% >= 阈值={up_th}%"
                        )
                        self._last_alert[alert_key] = now
                        self._show_popup(code, quote, f'上涨 {up_th}%', rule['dur'])
                        self._write_history(now, code, quote, f'上涨 {up_th}%')
                    else:
                        self._logger.debug(
                            f"[告警跳过] {code} 上涨 {up_th}%: "
                            f"冷却中 (剩余{int(self._min_interval - (now - last))}秒)"
                        )
            
            # Check each down threshold
            for down_th in down_thresholds:
                down_th = abs(float(down_th))
                if down_th > 0 and cp <= -down_th:
                    # Check if we already alerted for this specific threshold
                    alert_key = (code, down_th, '下跌')
                    last = self._last_alert.get(alert_key, 0)
                    if now - last >= self._min_interval:
                        self._logger.info(
                            f"[告警触发] {code} 下跌 {down_th}%: "
                            f"当前涨跌幅={cp:+.2f}% <= 阈值=-{down_th}%"
                        )
                        self._last_alert[alert_key] = now
                        self._show_popup(code, quote, f'下跌 {down_th}%', rule['dur'])
                        self._write_history(now, code, quote, f'下跌 {down_th}%')
                    else:
                        self._logger.debug(
                            f"[告警跳过] {code} 下跌 {down_th}%: "
                            f"冷却中 (剩余{int(self._min_interval - (now - last))}秒)"
                        )

    def _show_popup(self, code: str, quote: ETFQuote, trigger: str, duration: int):
        try:
            def show():
                w = AlertPopup(code, quote.name, quote.price, quote.change_percent, trigger, duration)
                w.Show(True)
                w.Raise()
            wx.CallAfter(show)
        except Exception:
            pass

    def _write_history(self, ts: float, code: str, quote: ETFQuote, trigger: str):
        try:
            line = f"{int(ts)},{code},{quote.price:.3f},{quote.change_percent:.2f},{trigger}\n"
            with open(self._log_path, 'a', encoding='utf-8') as f:
                f.write(line)
        except Exception:
            self._logger.warning('alert history write failed')

