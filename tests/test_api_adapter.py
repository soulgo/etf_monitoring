"""
Tests for API adapters using respx to mock httpx responses.
"""

import time
import respx
import httpx
from datetime import datetime

from src.data.api_adapter import EastMoneyAdapter, SinaAdapter, TencentAdapter, XueqiuAdapter


@respx.mock
def test_eastmoney_parse_success():
    adapter = EastMoneyAdapter(base_url="https://push2.eastmoney.com/api/qt/stock/get", timeout=2)
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    params = {"secid": "1.512170", "fields": "f57,f58,f43,f44,f45,f46,f60,f152"}
    respx.get(url).mock(return_value=httpx.Response(200, json={
        "rc": 0,
        "data": {
            "f58": "医疗ETF",
            "f43": 123456,  # /100 => 1234.56
            "f60": 120000,
            "f46": 1000000,
            "f152": "20250101143000"
        }
    }))
    quote = adapter.fetch_quote("512170")
    assert quote is not None
    assert quote.code == "512170"
    assert abs(quote.price - 1234.56) < 1e-6
    assert quote.update_time == "14:30:00"


@respx.mock
def test_sina_parse_success():
    adapter = SinaAdapter(base_url="http://hq.sinajs.cn/list=", timeout=2)
    symbol = "sh512170"
    url = f"http://hq.sinajs.cn/list={symbol}"
    content = (
        "var hq_str_sh512170=\"医疗ETF,1.000,1.000,1.010,1.020,0.990,0,0,100000,1000," 
        + ",".join(["x"] * 21) + ",2025-01-01,14:30:00\";"
    )
    respx.get(url).mock(return_value=httpx.Response(200, text=content))
    quote = adapter.fetch_quote("512170")
    assert quote is not None
    assert quote.name == "医疗ETF"
    assert abs(quote.price - 1.01) < 1e-6
    assert quote.update_time == "14:30:00"


@respx.mock
def test_tencent_parse_success():
    adapter = TencentAdapter(base_url="http://qt.gtimg.cn/q=", timeout=2)
    symbol = "sh512170"
    url = f"http://qt.gtimg.cn/q={symbol}"
    data = ["51", "医疗ETF", "512170", "1.010", "1.000", "0.010", "100000"]
    # Fill placeholders up to index 30
    while len(data) < 30:
        data.append("x")
    # Set time at index 30, change at 31, change_percent at 32
    data += ["143000", "0.010", "1.00"]
    # Pad to ~45 fields
    while len(data) < 45:
        data.append("x")
    payload = f"v_sh512170=\"{'~'.join(data)}\";"
    respx.get(url).mock(return_value=httpx.Response(200, text=payload))
    quote = adapter.fetch_quote("512170")
    assert quote is not None
    assert quote.name == "医疗ETF"
    assert abs(quote.price - 1.01) < 1e-6
    assert quote.update_time == "14:30:00"


@respx.mock
def test_xueqiu_parse_success():
    adapter = XueqiuAdapter(base_url="https://stock.xueqiu.com/v5/stock/quote.json", timeout=2)
    url = "https://stock.xueqiu.com/v5/stock/quote.json"
    respx.get(url).mock(return_value=httpx.Response(200, json={
        "data": {
            "quote": {
                "name": "医疗ETF",
                "current": 1.01,
                "last_close": 1.00,
                "volume": 100000,
                "timestamp": int(time.time() * 1000)
            }
        }
    }))
    quote = adapter.fetch_quote("512170")
    assert quote is not None
    assert quote.name == "医疗ETF"
    assert abs(quote.price - 1.01) < 1e-6
