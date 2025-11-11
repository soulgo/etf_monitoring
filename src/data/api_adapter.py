"""
API adapters for fetching ETF quotes from different data sources.

Provides unified interface for multiple quote providers with automatic failover.
"""

import time
from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime

import httpx

from .models import ETFQuote
from ..utils.logger import get_logger
from ..utils.helpers import get_market_prefix


class QuoteAPIAdapter(ABC):
    """
    Abstract base class for quote API adapters.
    
    All adapters must implement fetch_quote method with consistent interface.
    """
    
    def __init__(self, base_url: str, timeout: int = 5):
        """
        Initialize adapter.
        
        Args:
            base_url: API base URL
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.timeout = timeout
        self.logger = get_logger(self.__class__.__name__)
        
        # Create HTTP client with connection pooling
        self.client = httpx.Client(
            timeout=timeout,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
    
    @abstractmethod
    def fetch_quote(self, code: str) -> Optional[ETFQuote]:
        """
        Fetch quote data for given ETF code.
        
        Args:
            code: 6-digit ETF code
            
        Returns:
            ETFQuote object or None if failed
        """
        pass
    
    def close(self):
        """Close HTTP client."""
        if hasattr(self, 'client'):
            self.client.close()
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()


class EastMoneyAdapter(QuoteAPIAdapter):
    """
    Adapter for EastMoney (东方财富) API.
    
    API: http://push2.eastmoney.com/api/qt/stock/get
    Fields: f57=code, f58=name, f43=price, f44=change, f45=change_percent,
            f46=volume, f60=pre_close, f152=update_time
    """
    
    def fetch_quote(self, code: str) -> Optional[ETFQuote]:
        """
        Fetch quote from EastMoney API.
        
        Args:
            code: 6-digit ETF code
            
        Returns:
            ETFQuote object or None if failed
        """
        try:
            # Get market prefix (1=Shanghai, 0=Shenzhen)
            market = get_market_prefix(code)
            secid = f"{market}.{code}"
            
            # Build request URL
            url = self.base_url
            params = {
                'secid': secid,
                'fields': 'f57,f58,f43,f44,f45,f46,f60,f152'
            }
            
            # Send request with retry logic for 502 errors
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    self.logger.debug(f"[EastMoney] 请求 {code} (attempt {attempt + 1})")
                    response = self.client.get(url, params=params)
                    response.raise_for_status()
                    break  # Success, exit retry loop
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 502 and attempt < max_retries - 1:
                        self.logger.warning(f"[EastMoney] 502错误，重试 {attempt + 1}/{max_retries - 1}")
                        time.sleep(0.5)  # 短暂延迟后重试
                        continue
                    else:
                        raise  # 非502错误或最后一次尝试，抛出异常
            
            # Parse response
            data = response.json()
            
            if data.get('rc') != 0 or 'data' not in data:
                self.logger.warning(f"Invalid response for {code}: {data}")
                return None
            
            quote_data = data['data']
            
            # Extract fields
            name = quote_data.get('f58', f'ETF{code}')
            
            # 东方财富API返回的价格数据需要除以100
            price = quote_data.get('f43')
            if price is not None:
                price = price / 100.0
            
            change = quote_data.get('f44')
            if change is not None:
                change = change / 100.0
            
            volume = quote_data.get('f46', 0)
            
            pre_close = quote_data.get('f60')
            if pre_close is not None:
                pre_close = pre_close / 100.0
            
            update_time_raw = quote_data.get('f152')
            
            # Validate required fields
            if price is None or pre_close is None:
                self.logger.warning(f"Missing required fields for {code}")
                return None
            
            # 重新计算涨跌幅，确保准确性
            # change_percent = ((当前价 - 昨收价) / 昨收价) * 100
            if pre_close > 0:
                change_percent = ((price - pre_close) / pre_close) * 100.0
                change = price - pre_close
            else:
                change_percent = 0.0
                change = 0.0
            
            # Parse update time
            update_time = self._parse_update_time(update_time_raw)
            
            # Create ETFQuote object
            quote = ETFQuote(
                code=code,
                name=name,
                price=float(price),
                change=float(change) if change else 0.0,
                change_percent=float(change_percent),
                volume=int(volume),
                pre_close=float(pre_close) if pre_close else float(price),
                update_time=update_time,
                timestamp=time.time()
            )
            
            self.logger.info(f"[EastMoney] 成功获取 {code}: {name} {price} ({change_percent:+.2f}%)")
            return quote
            
        except httpx.TimeoutException:
            self.logger.error(f"[EastMoney] 请求超时 {code}")
            return None
            
        except httpx.HTTPError as e:
            self.logger.error(f"[EastMoney] HTTP错误 {code}: {e}")
            return None
            
        except Exception as e:
            self.logger.error(f"[EastMoney] 获取失败 {code}: {e}")
            return None
    
    def _parse_update_time(self, time_str: Optional[str]) -> str:
        """
        Parse update time string.
        
        Args:
            time_str: Time string (format: YYYYMMDDHHMMSS)
            
        Returns:
            Formatted time string (HH:MM:SS)
        """
        if not time_str:
            return datetime.now().strftime("%H:%M:%S")
        
        try:
            # Parse format: 20231104143000 -> 14:30:00
            if len(time_str) >= 14:
                hour = time_str[8:10]
                minute = time_str[10:12]
                second = time_str[12:14]
                return f"{hour}:{minute}:{second}"
        except:
            pass
        
        return datetime.now().strftime("%H:%M:%S")


class SinaAdapter(QuoteAPIAdapter):
    """
    Adapter for Sina Finance (新浪财经) API.
    
    API: http://hq.sinajs.cn/list=
    Response format: CSV-like string with comma-separated fields
    Fields: 0=name, 1=open, 2=pre_close, 3=price, 4=high, 5=low,
            6=bid, 7=ask, 8=volume, 9=amount, 10-31=various fields
    """
    
    def fetch_quote(self, code: str) -> Optional[ETFQuote]:
        """
        Fetch quote from Sina Finance API.
        
        Args:
            code: 6-digit ETF code
            
        Returns:
            ETFQuote object or None if failed
        """
        try:
            # Get market prefix
            market = 'sh' if get_market_prefix(code) == '1' else 'sz'
            symbol = f"{market}{code}"
            
            # Build request URL
            url = f"{self.base_url}{symbol}"
            
            # Send request with custom headers to avoid 403
            self.logger.debug(f"[Sina] 请求 {code}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://finance.sina.com.cn/'
            }
            response = self.client.get(url, headers=headers)
            response.raise_for_status()
            
            # Parse response
            # Format: var hq_str_sh512170="医疗ETF,1.234,1.230,1.235,...";
            content = response.text.strip()
            
            if not content or '=' not in content:
                self.logger.warning(f"Invalid response for {code}: {content}")
                return None
            
            # Extract data between quotes
            start = content.find('"') + 1
            end = content.rfind('"')
            if start <= 0 or end <= start:
                return None
            
            data_str = content[start:end]
            
            # Check if empty response (market closed or invalid code)
            if not data_str:
                self.logger.warning(f"Empty data for {code}")
                return None
            
            fields = data_str.split(',')
            
            if len(fields) < 32:  # Sina API returns 32+ fields
                self.logger.warning(f"Insufficient fields for {code}: {len(fields)}")
                return None
            
            # Extract fields (indices based on Sina API documentation)
            name = fields[0]
            price = fields[3]
            pre_close = fields[2]
            volume = fields[8]
            update_date = fields[30]  # YYYY-MM-DD
            update_time = fields[31]  # HH:MM:SS
            
            # Validate required fields
            if not price or not pre_close:
                self.logger.warning(f"Missing required fields for {code}")
                return None
            
            # Convert to float and calculate change
            try:
                price_f = float(price)
                pre_close_f = float(pre_close)
                
                if pre_close_f > 0:
                    change_percent = ((price_f - pre_close_f) / pre_close_f) * 100.0
                    change = price_f - pre_close_f
                else:
                    change_percent = 0.0
                    change = 0.0
                    
            except ValueError:
                self.logger.warning(f"Invalid numeric data for {code}")
                return None
            
            # Format update time
            if not update_time or len(update_time) < 8:
                update_time = datetime.now().strftime("%H:%M:%S")
            else:
                # Format is already HH:MM:SS
                update_time = update_time
            
            # Create ETFQuote object
            quote = ETFQuote(
                code=code,
                name=name,
                price=float(price_f),
                change=float(change),
                change_percent=float(change_percent),
                volume=int(float(volume)) if volume else 0,
                pre_close=float(pre_close_f),
                update_time=update_time,
                timestamp=time.time()
            )
            
            self.logger.info(f"[Sina] 成功获取 {code}: {name} {price_f} ({change_percent:+.2f}%)")
            return quote
            
        except httpx.TimeoutException:
            self.logger.error(f"[Sina] 请求超时 {code}")
            return None
            
        except httpx.HTTPError as e:
            self.logger.error(f"[Sina] HTTP错误 {code}: {e}")
            return None
            
        except Exception as e:
            self.logger.error(f"[Sina] 获取失败 {code}: {e}")
            return None


class TencentAdapter(QuoteAPIAdapter):
    """
    Adapter for Tencent (腾讯) API.
    
    API: http://qt.gtimg.cn/q=
    Response format: CSV-like string with fields separated by ~
    """
    
    def fetch_quote(self, code: str) -> Optional[ETFQuote]:
        """
        Fetch quote from Tencent API.
        
        Args:
            code: 6-digit ETF code
            
        Returns:
            ETFQuote object or None if failed
        """
        try:
            # Get market prefix
            market = 'sh' if get_market_prefix(code) == '1' else 'sz'
            symbol = f"{market}{code}"
            
            # Build request URL
            url = f"{self.base_url}{symbol}"
            
            # Send request
            self.logger.debug(f"[Tencent] 请求 {code}")
            response = self.client.get(url)
            response.raise_for_status()
            
            # Parse response
            # Format: v_sh512170="51~医疗ETF~512170~1.234~0.028~2.32~12345678~..."
            content = response.text.strip()
            
            if not content or '~' not in content:
                self.logger.warning(f"Invalid response for {code}: {content}")
                return None
            
            # Extract data between quotes
            start = content.find('"') + 1
            end = content.rfind('"')
            if start <= 0 or end <= start:
                return None
            
            data_str = content[start:end]
            fields = data_str.split('~')
            
            if len(fields) < 40:  # Tencent API returns ~50 fields
                self.logger.warning(f"Insufficient fields for {code}")
                return None
            
            # Extract fields (indices based on Tencent API documentation)
            name = fields[1]
            price = fields[3]
            pre_close = fields[4]
            change = fields[31]  # price - pre_close
            change_percent = fields[32]
            volume = fields[6]
            update_time = fields[30]  # Format: HHMMSS
            
            # Validate required fields
            if not price or not pre_close:
                self.logger.warning(f"Missing required fields for {code}")
                return None
            
            # 重新计算涨跌幅，确保准确性
            # change_percent = ((当前价 - 昨收价) / 昨收价) * 100
            try:
                price_f = float(price)
                pre_close_f = float(pre_close)
                if pre_close_f > 0:
                    change_percent = ((price_f - pre_close_f) / pre_close_f) * 100.0
                    change = price_f - pre_close_f
                else:
                    change_percent = 0.0
                    change = 0.0
            except:
                change_percent = 0.0
                change = 0.0
            
            # Format update time
            if update_time and len(update_time) >= 6:
                hour = update_time[0:2]
                minute = update_time[2:4]
                second = update_time[4:6]
                update_time = f"{hour}:{minute}:{second}"
            else:
                update_time = datetime.now().strftime("%H:%M:%S")
            
            # Create ETFQuote object
            quote = ETFQuote(
                code=code,
                name=name,
                price=float(price),
                change=float(change),
                change_percent=float(change_percent),
                volume=int(volume) if volume else 0,
                pre_close=float(pre_close) if pre_close else float(price),
                update_time=update_time,
                timestamp=time.time()
            )
            
            self.logger.info(f"[Tencent] 成功获取 {code}: {name} {price} ({change_percent:+.2f}%)")
            return quote
            
        except httpx.TimeoutException:
            self.logger.error(f"[Tencent] 请求超时 {code}")
            return None
            
        except httpx.HTTPError as e:
            self.logger.error(f"[Tencent] HTTP错误 {code}: {e}")
            return None
            
        except Exception as e:
            self.logger.error(f"[Tencent] 获取失败 {code}: {e}")
            return None


class XueqiuAdapter(QuoteAPIAdapter):
    """
    Adapter for Xueqiu (雪球) API.
    
    API: https://stock.xueqiu.com/v5/stock/quote.json
    Response format: JSON with quote data
    Requires User-Agent header to simulate browser access
    """
    
    def __init__(self, base_url: str, timeout: int = 5):
        """
        Initialize Xueqiu adapter with custom headers.
        
        Args:
            base_url: API base URL
            timeout: Request timeout in seconds
        """
        super().__init__(base_url, timeout)
        
        # Override client with custom headers for Xueqiu
        self.client = httpx.Client(
            timeout=timeout,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://xueqiu.com/'
            }
        )
    
    def fetch_quote(self, code: str) -> Optional[ETFQuote]:
        """
        Fetch quote from Xueqiu API.
        
        Args:
            code: 6-digit ETF code
            
        Returns:
            ETFQuote object or None if failed
        """
        try:
            # Get market prefix for Xueqiu symbol format
            market = 'SH' if get_market_prefix(code) == '1' else 'SZ'
            symbol = f"{market}{code}"
            
            # Build request URL
            url = self.base_url
            params = {
                'symbol': symbol,
                'extend': 'detail'
            }
            
            # Send request
            self.logger.debug(f"[Xueqiu] 请求 {code}")
            response = self.client.get(url, params=params)
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            
            if 'data' not in data or 'quote' not in data['data']:
                self.logger.warning(f"Invalid response for {code}: {data}")
                return None
            
            quote_data = data['data']['quote']
            
            # Extract fields
            name = quote_data.get('name', f'ETF{code}')
            price = quote_data.get('current')  # 当前价
            pre_close = quote_data.get('last_close')  # 昨收价
            volume = quote_data.get('volume', 0)  # 成交量
            timestamp_ms = quote_data.get('timestamp', int(time.time() * 1000))
            
            # Validate required fields
            if price is None or pre_close is None:
                self.logger.warning(f"Missing required fields for {code}")
                return None
            
            # Calculate change and change_percent
            try:
                price_f = float(price)
                pre_close_f = float(pre_close)
                
                if pre_close_f > 0:
                    change_percent = ((price_f - pre_close_f) / pre_close_f) * 100.0
                    change = price_f - pre_close_f
                else:
                    change_percent = 0.0
                    change = 0.0
                    
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid numeric data for {code}")
                return None
            
            # Format update time from timestamp
            update_time = datetime.fromtimestamp(timestamp_ms / 1000).strftime("%H:%M:%S")
            
            # Create ETFQuote object
            quote = ETFQuote(
                code=code,
                name=name,
                price=float(price_f),
                change=float(change),
                change_percent=float(change_percent),
                volume=int(volume) if volume else 0,
                pre_close=float(pre_close_f),
                update_time=update_time,
                timestamp=time.time()
            )
            
            self.logger.info(f"[Xueqiu] 成功获取 {code}: {name} {price_f} ({change_percent:+.2f}%)")
            return quote
            
        except httpx.TimeoutException:
            self.logger.error(f"[Xueqiu] 请求超时 {code}")
            return None
            
        except httpx.HTTPError as e:
            self.logger.error(f"[Xueqiu] HTTP错误 {code}: {e}")
            return None
            
        except Exception as e:
            self.logger.error(f"[Xueqiu] 获取失败 {code}: {e}")
            return None


class APIAdapterFactory:
    """
    Factory for creating API adapters based on configuration.
    
    Supported adapters:
    - eastmoney: 东方财富 (EastMoney)
    - sina: 新浪财经 (Sina Finance)
    - tencent: 腾讯财经 (Tencent)
    - xueqiu: 雪球 (Xueqiu)
    """
    
    ADAPTERS = {
        'eastmoney': EastMoneyAdapter,
        'sina': SinaAdapter,
        'tencent': TencentAdapter,
        'xueqiu': XueqiuAdapter,
    }
    
    @classmethod
    def create(cls, name: str, base_url: str, timeout: int = 5) -> Optional[QuoteAPIAdapter]:
        """
        Create API adapter by name.
        
        Args:
            name: Adapter name (eastmoney, tencent)
            base_url: API base URL
            timeout: Request timeout
            
        Returns:
            API adapter instance or None if unknown name
        """
        adapter_class = cls.ADAPTERS.get(name.lower())
        if adapter_class is None:
            return None
        
        return adapter_class(base_url, timeout)

