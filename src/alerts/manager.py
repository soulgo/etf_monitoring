import time
from pathlib import Path
import wx

from ..data.models import ETFQuote
from ..ui.alert_popup import AlertPopup
from ..utils.logger import get_logger

class AlertManager:
    def __init__(self, config):
        self._logger = get_logger(__name__)
        self._rules = {}
        symbols = config.get('symbols', [])
        for entry in symbols:
            if isinstance(entry, dict) and 'symbol' in entry:
                self._rules[entry['symbol']] = {
                    'up': float(entry.get('up_threshold', 0.0)),
                    'down': float(entry.get('down_threshold', 0.0)),
                    'dur': int(entry.get('duration_secs', 5))
                }
        self._last_alert = {}
        self._min_interval = 60
        self._log_path = Path('logs') / 'alerts.log'
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def evaluate(self, quotes: dict, changed_codes: list):
        """根据涨跌幅和用户设置的阈值触发弹窗告警。

        约定：
        - 配置里的 up_threshold / down_threshold 统一按“百分比绝对值”存储，如 3.0 表示 3%
        - 上涨告警：当前涨跌幅 >= +up_threshold
        - 下跌告警：当前涨跌幅 <= -down_threshold
        这样无论用户在配置里填 3 还是 -3，都会按 3% 处理，更符合直觉。
        """
        now = time.time()
        for code, quote in quotes.items():
            rule = self._rules.get(code)
            if not rule:
                continue

            cp = quote.change_percent
            if cp is None:
                continue

            # 统一使用绝对值作为阈值，避免正负号混乱
            up_th = abs(float(rule.get('up', 0.0)))
            down_th = abs(float(rule.get('down', 0.0)))

            trigger = None
            # 上涨：涨跌幅 >= +up_th
            if up_th > 0 and cp >= up_th:
                trigger = '上涨'
            # 下跌：涨跌幅 <= -down_th
            elif down_th > 0 and cp <= -down_th:
                trigger = '下跌'

            if not trigger:
                continue

            last = self._last_alert.get(code, 0)
            if now - last < self._min_interval:
                continue

            self._last_alert[code] = now
            self._show_popup(code, quote, trigger, rule['dur'])
            self._write_history(now, code, quote, trigger)

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

