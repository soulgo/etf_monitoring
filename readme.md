# ETF 监控工具 V1.0

一个轻量级的 Windows 桌面应用，用于实时监控自选 ETF 的价格变化，支持系统托盘显示、悬浮窗口和自动轮播。

## 📋 目录

- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [用户指南](#用户指南)
- [技术架构](#技术架构)
- [开发指南](#开发指南)
- [运维指南](#运维指南)
- [常见问题](#常见问题)

---

## ✨ 功能特性

### 核心功能
- ✅ **实时行情监控**：自动获取 ETF 最新价格、涨跌幅、成交量
- ✅ **系统托盘显示**：在托盘图标 Tooltip 中轮播显示多个 ETF
- ✅ **右下角悬浮窗**：可拖动、可缩放的悬浮窗，字体自适应窗口大小
- ✅ **智能轮播模式**：支持定时轮播、价格变化触发、混合模式
- ✅ **灵活配置**：图形化设置界面，支持 ETF 列表管理和参数调整
- ✅ **主备接口切换**：东方财富主接口，腾讯行情备用，自动故障切换
- ✅ **开机自启**：可选开机自动启动功能

### 界面特点
- 🎨 **涨跌配色**：涨红跌绿，醒目直观
- 📏 **自由缩放**：悬浮窗支持任意边框和四角拖拽调整
- 🔤 **字体适配**：窗口大小改变时字体自动缩放，内容始终完整显示
- 🎯 **轻量高效**：常驻内存 < 100MB，CPU 占用 < 3%

### 数据可靠性
- 🔄 **自动重试**：网络异常时自动重试，超时自动切换备用接口
- 💾 **智能缓存**：数据本地缓存，变化检测，避免重复请求
- 📊 **实时更新**：默认 5 秒刷新间隔，可自定义

---

## 🚀 快速开始

### 方式一：使用安装包（推荐）

1. 下载 `ETFMonitor_Setup_v1.0.0.exe`
2. 双击运行安装程序
3. 按照向导完成安装
4. 启动程序，右键托盘图标打开"设置"
5. 添加自选 ETF 代码（如 512170、515790）
6. 点击"保存"开始监控

### 方式二：从源码运行

#### 环境要求
- Python 3.8+
- Windows 10/11

#### 安装步骤

```bash
# 1. 克隆仓库
git clone <repository-url>
cd etf_monitoring

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行程序
python main.py
```

---

## 📖 用户指南

### 首次使用

1. **启动程序**
   - 程序启动后会在系统托盘显示图标
   - 右下角会出现悬浮窗（可通过托盘菜单隐藏/显示）

2. **添加自选 ETF**
   - 右键托盘图标 → 点击"设置"
   - 在"我的自选 ETF"区域输入代码（如 512170）
   - 点击"添加"按钮
   - 程序会自动获取 ETF 名称
   - 点击"保存"生效

3. **调整参数**
   - 数据刷新间隔：3-30 秒（默认 5 秒）
   - 托盘轮播间隔：1-60 秒（默认 3 秒）
   - 轮播模式：定时轮播 / 价格变化时 / 两者都（推荐）

### 悬浮窗使用

#### 拖动悬浮窗
- 在窗口中间区域**按住鼠标左键拖动**即可移动

#### 调整窗口大小
- 将鼠标移到**任意边框或四个角**
- 鼠标光标会变成双向箭头（↕ ↔ ↖↘ ↗↙）
- **按住鼠标左键拖动**即可调整大小
- 支持缩放到极小尺寸，字体会自动适配

#### 悬浮窗右键菜单
- **重置到右下角**：恢复到屏幕右下角位置
- **重置尺寸**：恢复默认窗口大小（350×60）
- **透明度**：不透明 / 轻微透明 / 半透明 / 透明
- **隐藏悬浮窗**：隐藏窗口（可通过托盘菜单重新显示）

#### 悬浮窗快捷操作
- **双击**：快速隐藏悬浮窗

### 托盘菜单

右键托盘图标可打开菜单：

```
┌─────────────────────┐
│ ● 显示悬浮窗        │
│ ● 查看所有基金      │
│ ──────────────────  │
│   设置...           │
│   手动刷新          │
│ ──────────────────  │
│   关于              │
│   退出              │
└─────────────────────┘
```

- **显示悬浮窗**：显示/隐藏右下角悬浮窗
- **查看所有基金**：打开详情窗口，查看完整 ETF 列表
- **设置**：打开设置界面
- **手动刷新**：立即刷新所有 ETF 数据
- **关于**：查看版本信息
- **退出**：关闭程序

### 托盘 Tooltip 显示

将鼠标悬停在托盘图标上可查看当前显示的 ETF 信息：

```
医疗ETF (512170)
最新价: 3.640 (↑+0.28%)
更新: 14:35:12
```

### 配置文件

配置文件位于程序目录下的 `config.json`，包含所有设置参数。

**主要配置项**：
- `etf_list`：自选 ETF 代码列表
- `refresh_interval`：数据刷新间隔（秒）
- `rotation_interval`：托盘轮播间隔（秒）
- `rotation_mode`：轮播模式（timer/change/both）
- `floating_window`：悬浮窗配置（位置、大小、字体、透明度）
- `auto_start`：开机自启
- `log_level`：日志级别（INFO/DEBUG/WARNING/ERROR）

**示例配置**：
```json
{
  "config_version": "1.0",
  "etf_list": ["512170", "515790", "512690"],
  "refresh_interval": 5,
  "rotation_interval": 3,
  "rotation_mode": "both",
  "floating_window": {
    "enabled": true,
    "position": [100, 100],
    "size": [350, 60],
    "font_size": 18,
    "transparency": 200,
    "always_on_top": true
  },
  "auto_start": false,
  "log_level": "INFO"
}
```

### 日志文件

日志文件位于 `logs/etf_monitor.log`，记录程序运行状态和错误信息。

**日志级别**：
- `INFO`：正常运行信息
- `WARNING`：警告信息（如请求慢、接口切换）
- `ERROR`：错误信息（如请求失败）
- `DEBUG`：详细调试信息（需在配置中启用）

---

## 🏗 技术架构

### 系统架构图

```
┌─────────────────────────────────────────────┐
│           展示层（UI Layer）                 │
│  - 系统托盘图标 + Tooltip 轮播               │
│  - 右下角悬浮窗（可拖拽、可缩放）             │
│  - 设置对话框（ETF 管理 + 参数配置）         │
│  - 详情窗口（显示所有 ETF 列表）             │
└─────────────────┬───────────────────────────┘
                  │ wxPython 事件机制
┌─────────────────▼───────────────────────────┐
│         业务逻辑层（Logic Layer）            │
│  - 轮播控制器（定时/变化触发）               │
│  - 配置管理器（读写 config.json）            │
│  - 数据缓存管理器（内存缓存 + 变化检测）     │
└─────────────────┬───────────────────────────┘
                  │ Python Queue + 事件通知
┌─────────────────▼───────────────────────────┐
│         数据层（Data Layer）                 │
│  - HTTP 客户端（httpx 异步请求）             │
│  - 接口适配器（东方财富/腾讯）               │
│  - 主备切换逻辑 + 自动重试                   │
└─────────────────────────────────────────────┘
```

### 技术栈

| 组件 | 技术选型 | 版本 | 说明 |
|------|---------|------|------|
| UI 框架 | wxPython | 4.2.x | 原生 Windows 外观，资源占用低 |
| HTTP 客户端 | httpx | 0.25.x | 支持同步/异步，连接池，超时控制 |
| 配置管理 | JSON | - | 标准库，简单易读 |
| 日志框架 | logging | - | Python 标准库，按天轮转 |
| 打包工具 | PyInstaller | 6.x | 打包为单文件 exe |

### 目录结构

```
etf_monitoring/
├── main.py                  # 程序入口
├── requirements.txt         # Python 依赖
├── config.json             # 用户配置文件
├── config.default.json     # 默认配置模板
├── build.spec              # PyInstaller 配置
├── build.ps1               # 构建脚本
├── src/                    # 源代码目录
│   ├── __init__.py
│   ├── app.py              # 主应用类
│   ├── config/             # 配置管理模块
│   │   ├── manager.py      # 配置管理器
│   │   └── validator.py    # 配置验证器
│   ├── data/               # 数据层模块
│   │   ├── models.py       # 数据模型
│   │   ├── fetcher.py      # 数据采集器
│   │   ├── cache.py        # 缓存管理器
│   │   └── api_adapter.py  # 接口适配器
│   ├── ui/                 # UI 模块
│   │   ├── tray_icon.py    # 系统托盘
│   │   ├── floating_window.py  # 悬浮窗
│   │   ├── settings_dialog.py  # 设置界面
│   │   ├── detail_window.py    # 详情窗口
│   │   └── about_dialog.py     # 关于对话框
│   └── utils/              # 工具模块
│       ├── logger.py       # 日志工具
│       ├── helpers.py      # 辅助函数
│       └── events.py       # 自定义事件
├── logs/                   # 日志目录
│   └── etf_monitor.log
├── resources/              # 资源目录
│   └── icons/              # 图标资源
├── dist/                   # 打包输出目录
│   └── ETFMonitor.exe
└── README.md               # 本文档
```

### 核心模块说明

#### 1. 配置管理模块 (`src/config/`)
- **manager.py**：配置管理器，负责加载、保存、验证配置文件
- **validator.py**：配置验证器，确保配置项合法性

**特点**：
- 单例模式，全局统一配置访问
- 支持点号路径访问（如 `config.get('api_config.primary.timeout')`）
- 原子性保存（临时文件 + 重命名）
- 自动填充缺失项

#### 2. 数据层模块 (`src/data/`)
- **models.py**：数据模型定义（ETFQuote, ETFCache）
- **fetcher.py**：数据采集器，定时轮询行情接口
- **cache.py**：缓存管理器，内存缓存 + 变化检测
- **api_adapter.py**：接口适配器工厂，统一不同接口格式

**数据流程**：
```
[定时器触发] → [并发请求 ETF 列表] → [解析响应] 
   → [更新缓存] → [检测变化] → [通知 UI 更新]
```

**主备切换逻辑**：
- 主接口连续失败 3 次 → 切换备用接口
- 每 5 分钟尝试切回主接口
- 记录切换日志（WARNING 级别）

#### 3. UI 模块 (`src/ui/`)
- **tray_icon.py**：系统托盘图标，Tooltip 轮播显示
- **floating_window.py**：悬浮窗，支持拖拽、缩放、字体自适应
- **settings_dialog.py**：设置界面，ETF 管理和参数配置
- **detail_window.py**：详情窗口，显示所有 ETF 列表
- **about_dialog.py**：关于对话框，版本信息

**悬浮窗核心特性**：
- 8 方向调整：4 边 + 4 角
- 光标自动切换：根据位置显示对应光标
- 字体自动缩放：`font_size = height × 0.45`，范围 4-32px
- 内边距自适应：`padding = height × 0.15`，范围 2-10px
- 文本完整显示：动态缩小字体直到内容完全可见

#### 4. 工具模块 (`src/utils/`)
- **logger.py**：日志工具，按天轮转，分级记录
- **helpers.py**：辅助函数（格式化、验证等）
- **events.py**：wxPython 自定义事件

### 数据接口

#### 东方财富接口（主接口）

**接口地址**：
```
http://push2.eastmoney.com/api/qt/stock/get
```

**请求参数**：
- `secid`：证券代码（格式：`1.512170`，1 表示上海市场）
- `fields`：返回字段（f57=代码, f58=名称, f43=最新价, f45=涨跌幅等）

**返回示例**：
```json
{
  "rc": 0,
  "data": {
    "f57": "512170",
    "f58": "医疗ETF",
    "f43": 3.64,
    "f44": 0.01,
    "f45": 0.28,
    "f46": 12345678,
    "f60": 3.63,
    "f152": "20251105143000"
  }
}
```

#### 腾讯行情接口（备用）

**接口地址**：
```
http://qt.gtimg.cn/q=
```

**请求参数**：
- `q`：证券代码（格式：`sz512170`，sz 表示深圳，sh 表示上海）

**返回格式**：
```
v_sz512170="1~医疗ETF~512170~3.64~3.63~...";
```

---

## 💻 开发指南

### 环境搭建

1. **安装 Python 3.8+**
   ```bash
   python --version  # 确认版本
   ```

2. **创建虚拟环境**（推荐）
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **运行程序**
   ```bash
   python main.py
   ```

### 开发模式

启用 DEBUG 日志：
```json
{
  "log_level": "DEBUG"
}
```

查看详细日志：
```bash
Get-Content -Path logs\etf_monitor.log -Tail 50 -Wait
```

### 构建打包

#### 方式一：使用 PowerShell 脚本

```powershell
.\build.ps1
```

#### 方式二：手动执行

```bash
# 1. 清理旧文件
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue

# 2. 打包为单文件 exe
pyinstaller build.spec

# 3. 复制配置文件
Copy-Item config.default.json dist/
Copy-Item config.json dist/ -ErrorAction SilentlyContinue
```

打包后的文件在 `dist/` 目录。

### 代码规范

- **命名规范**：
  - 类名：大驼峰（`ETFMonitorApp`）
  - 函数/变量：小写下划线（`fetch_quote`）
  - 私有方法：前缀下划线（`_update_cache`）
  - 常量：大写下划线（`DEFAULT_INTERVAL`）

- **文档字符串**：
  - 所有公开类和方法必须有 docstring
  - 使用 Google 风格
  ```python
  def fetch_quote(code: str) -> ETFQuote:
      """
      获取 ETF 行情数据。
      
      Args:
          code: ETF 代码
          
      Returns:
          ETFQuote 对象
          
      Raises:
          NetworkError: 网络请求失败
      """
  ```

- **类型注解**：
  - 函数参数和返回值使用类型注解
  - 复杂类型使用 `typing` 模块

### 添加新功能

#### 示例：添加新的数据接口

1. 在 `src/data/api_adapter.py` 中创建新适配器类：
   ```python
   class NewAPIAdapter(APIAdapter):
       def fetch_quote(self, code: str) -> Optional[ETFQuote]:
           # 实现接口逻辑
           pass
   ```

2. 在 `APIAdapterFactory` 中注册：
   ```python
   @staticmethod
   def create(adapter_type: str, ...) -> APIAdapter:
       if adapter_type == 'new_api':
           return NewAPIAdapter(...)
   ```

3. 在 `config.json` 中配置：
   ```json
   {
     "api_config": {
       "primary": {
         "name": "new_api",
         "base_url": "...",
         "timeout": 5
       }
     }
   }
   ```

---

## 🔧 运维指南

### 日常运维

#### 查看运行状态
```powershell
# 查看进程
Get-Process -Name ETFMonitor

# 查看内存占用
Get-Process -Name ETFMonitor | Select-Object Name, WS

# 查看最新日志
Get-Content logs\etf_monitor.log -Tail 20
```

#### 重启程序
```powershell
# 强制关闭
Stop-Process -Name ETFMonitor -Force

# 重新启动
Start-Process dist\ETFMonitor.exe
```

### 日志管理

日志文件默认按天轮转，保留最近 7 天：
```
logs/
├── etf_monitor.log           # 当前日志
├── etf_monitor.log.2025-11-05
├── etf_monitor.log.2025-11-04
└── ...
```

**日志分析**：
```powershell
# 统计错误数量
Select-String -Path logs\etf_monitor.log -Pattern "ERROR" | Measure-Object

# 查找特定 ETF 的日志
Select-String -Path logs\etf_monitor.log -Pattern "512170"

# 查看接口切换记录
Select-String -Path logs\etf_monitor.log -Pattern "switching to backup"
```

### 性能监控

#### 资源占用目标

| 指标 | 目标值 | 实际测试 |
|------|--------|---------|
| 常驻内存 | < 100MB | ~65MB |
| CPU 平均 | < 3% | ~1.5% |
| CPU 峰值 | < 10% | ~5% |
| 网络流量 | < 1MB/小时 | ~0.5MB/小时（10 ETF） |

#### 性能优化建议

1. **减少刷新频率**：
   - 将 `refresh_interval` 从 5 秒调整为 10 秒
   - 降低网络请求频率

2. **减少监控数量**：
   - 建议不超过 20 个 ETF
   - 过多会增加网络请求和内存占用

3. **调整日志级别**：
   - 生产环境使用 `INFO` 级别
   - 避免 `DEBUG` 级别的性能开销

### 故障排查

#### 问题：程序无法启动

**可能原因**：
1. 配置文件损坏
2. 端口被占用（如果有网络服务）
3. 缺少依赖库

**解决方法**：
```powershell
# 1. 删除配置文件，使用默认配置
Remove-Item config.json
Copy-Item config.default.json config.json

# 2. 查看日志
Get-Content logs\etf_monitor.log -Tail 50

# 3. 重新安装依赖（源码运行）
pip install -r requirements.txt --force-reinstall
```

#### 问题：数据不更新

**可能原因**：
1. 网络连接问题
2. 接口失效
3. 程序暂停刷新

**解决方法**：
```powershell
# 1. 检查网络连接
Test-NetConnection push2.eastmoney.com

# 2. 查看日志中的错误信息
Select-String -Path logs\etf_monitor.log -Pattern "ERROR|WARNING" -Tail 20

# 3. 手动刷新
# 右键托盘图标 → 手动刷新
```

#### 问题：托盘图标消失

**可能原因**：
1. 程序崩溃
2. explorer.exe 重启导致托盘图标丢失

**解决方法**：
```powershell
# 1. 检查程序是否运行
Get-Process -Name ETFMonitor -ErrorAction SilentlyContinue

# 2. 如果进程存在但图标消失，重启程序
Stop-Process -Name ETFMonitor -Force
Start-Process dist\ETFMonitor.exe
```

#### 问题：悬浮窗无法拖动/缩放

**可能原因**：
1. 鼠标位置不正确
2. 窗口被其他程序覆盖

**解决方法**：
1. 确保鼠标在窗口边缘（距离边缘 12px 内）
2. 右键悬浮窗 → "重置到右下角"
3. 重启程序

### 备份与恢复

#### 备份配置

```powershell
# 备份配置文件
Copy-Item config.json config.backup.json

# 备份到其他位置
Copy-Item config.json D:\Backup\etf_config_$(Get-Date -Format 'yyyyMMdd').json
```

#### 恢复配置

```powershell
# 从备份恢复
Copy-Item config.backup.json config.json

# 恢复默认配置
Copy-Item config.default.json config.json
```

### 卸载程序

#### 使用安装包安装的版本

1. 控制面板 → 程序和功能
2. 找到"ETF 监控工具"
3. 点击"卸载"
4. 选择是否保留配置文件

#### 手动清理

```powershell
# 1. 停止程序
Stop-Process -Name ETFMonitor -Force -ErrorAction SilentlyContinue

# 2. 删除开机自启动项
Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" `
  -Name "ETFMonitor" -ErrorAction SilentlyContinue

# 3. 删除程序目录
Remove-Item -Recurse -Force "C:\Program Files\ETF Monitor"

# 4. 删除用户数据（可选）
Remove-Item -Recurse -Force "$env:APPDATA\ETF Monitor"
```

---

## ❓ 常见问题

### Q1: 如何添加自选 ETF？

**A**: 右键托盘图标 → 设置 → 在"输入代码"框输入 ETF 代码（如 512170）→ 点击"添加" → 点击"保存"

### Q2: 支持哪些 ETF 代码？

**A**: 支持所有在上海/深圳交易所上市的 ETF。代码为 6 位数字，如：
- 512170（医疗 ETF）
- 515790（光伏 ETF）
- 512690（酒 ETF）
- 159928（消费 ETF）

### Q3: 数据延迟有多大？

**A**: 默认 5 秒刷新一次，实际延迟约 5-10 秒。可在设置中调整刷新间隔（最快 3 秒）。

### Q4: 悬浮窗无法拖动怎么办？

**A**: 
1. 确保在窗口**中间区域**按住左键拖动（不是在边缘）
2. 如果卡住，右键悬浮窗 → "重置到右下角"
3. 重启程序

### Q5: 如何调整悬浮窗大小？

**A**: 
1. 将鼠标移到窗口**边缘或四个角**
2. 光标变成双向箭头时，按住左键拖动
3. 支持 8 个方向调整：上下左右 + 四个角

### Q6: 字体太小/太大怎么办？

**A**: 字体会根据窗口大小自动调整：
- 窗口变大 → 字体自动变大
- 窗口变小 → 字体自动变小
- 建议窗口高度 40-100 像素之间

### Q7: 涨跌颜色能自定义吗？

**A**: 当前版本固定为涨红跌绿。自定义颜色功能将在后续版本提供。

### Q8: 程序占用资源多吗？

**A**: 非常轻量：
- 内存：约 60-80MB
- CPU：空闲时 < 2%，刷新时瞬间 < 5%
- 网络：每小时约 0.5MB（监控 10 个 ETF）

### Q9: 支持开机自启吗？

**A**: 支持。在设置界面勾选"开机自动启动"即可。

### Q10: 数据来源可靠吗？

**A**: 
- 主接口：东方财富（https://push2.eastmoney.com）
- 备用接口：腾讯行情（http://qt.gtimg.cn）
- 自动主备切换，确保数据连续性

### Q11: 如何查看所有 ETF？

**A**: 右键托盘图标 → "查看所有基金"，会打开详情窗口显示完整列表。

### Q12: 程序崩溃了怎么办？

**A**: 
1. 查看日志：`logs\etf_monitor.log`
2. 尝试删除 `config.json`，使用默认配置
3. 如问题持续，提交 Issue（附上日志）

---

## 📝 版本历史

### v1.0.0 (2025-11-05)

**首次发布**

✨ 新功能：
- 实时监控自选 ETF 行情
- 系统托盘图标 + Tooltip 轮播显示
- 右下角悬浮窗，支持拖拽和 8 方向缩放
- 字体自适应窗口大小，内容始终完整显示
- 图形化设置界面，ETF 管理和参数配置
- 详情窗口，查看所有 ETF 列表
- 主备接口自动切换，数据可靠
- 开机自启动功能
- 完善的日志记录

🎨 界面优化：
- 涨红跌绿配色
- 悬浮窗透明度可调
- 设置界面优化，列表区域加大

🐛 Bug 修复：
- 修复鼠标捕获丢失导致的异常
- 修复窗口缩放时的布局问题
- 修复 ETF 名称显示问题

---

## 📄 许可证

本项目仅供学习和个人使用。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📞 联系方式

如有问题或建议，请提交 Issue 或联系开发者。

---

**ETF 监控工具 V1.0** - 让行情监控更简单 🚀
