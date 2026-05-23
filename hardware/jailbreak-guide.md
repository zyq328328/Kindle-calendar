# Kindle Touch 越狱指南

## 概述

本指南介绍如何对 Kindle Touch (第7代) 进行越狱，以便安装自定义应用程序和 Python 环境。

## 适用设备

- Kindle Touch (KT) - 第7代触屏版
- 系统版本: 5.3.x - 5.4.x

**注意**: 请先确认您的设备型号和系统版本再继续。

## 准备工作

### 需要准备

- U盘 (FAT32 格式，容量 256MB-4GB)
- 电脑 (Windows/Mac/Linux)
- Kindle Touch 设备
- 稳定的 WiFi 网络

### 检查系统版本

1. 设置 → 关于本机
2. 查看序列号和固件版本

## 越狱步骤

### 方法一：MRPIZ 越狱 (推荐)

这是目前最稳定的方法，适用于大多数 Kindle Touch 设备。

1. **下载越狱工具**
   - 访问 https://github.com/MRPIZ/KindleTouchJailbreak
   - 下载对应的 jailbreak 文件

2. **准备越狱 U盘**
   - 将下载的 `jailbreak.bin` 复制到 U盘根目录
   - 重命名为 `update.bin`

3. **执行越狱**
   - 关闭 Kindle WiFi
   - 将 U盘插入 Kindle
   - 等待约 30 秒
   - 设备会自动进入更新模式
   - 越狱成功后会显示 "Done"

4. **验证越狱**
   - 重启设备
   - 如果能正常进入主界面，说明越狱成功

### 方法二：SNK 越狱

适用于无法使用 MRPIZ 方法的设备。

1. **下载工具**
   - 访问 https://github.com/s unset/Kind leTouchSNK
   - 获取 SNK jailbreak 文件

2. **安装步骤**
   - 按照项目文档进行操作
   - 通常需要通过特殊序列号触发越狱

## 安装 KUAL 启动器

越狱成功后，需要安装 KUAL (Kindle Unified Application Launcher)：

1. **下载 KUAL**
   - 访问 https://github.com/KindleUnpack/KUAL
   - 下载最新版本的 `KUAL Kindle-...azw2`

2. **安装方法**
   - 将下载的 azw2 文件复制到 Kindle 的 `documents` 文件夹
   - 在 Kindle 上打开 "我的图书馆"
   - 找到 KUAL 并打开
   - 点击 "Install" 安装

3. **验证安装**
   - 打开 KUAL 主界面
   - 应能看到菜单选项

## 安装 Python 环境

Kindle Touch 需要安装 Python 才能运行自定义应用。

### 安装 Python 环境

Kindle Touch 需要安装 Python 才能运行自定义应用。

**推荐安装包**（来源：MobileRead 论坛）

| 设备类型 | 安装包 | 大小 | Python版本 |
|---------|--------|------|-----------|
| Touch/K5/KV/KO | [kindle-python-0.15.N-r18981.tar.xz](https://storage.gra.cloud.ovh.net/v1/AUTH_2ac4bfee353948ec8ea7fd1710574097/mr-public/Touch/kindle-python-0.15.N-r18981.tar.xz) | 104.5MB | Python 2.7 + 3.9 |
| Legacy (K4等) | [kindle-python-0.14.N-r18833.tar.xz](https://storage.gra.cloud.ovh.net/v1/AUTH_2ac4bfee353948ec8ea7fd1710574097/mr-public/Legacy/kindle-python-0.14.N-r18833.tar.xz) | 82.8MB | Python 2.7 + 3.9 |

**安装步骤**

1. **安装 MRPI (MobileRead Package Installer)**
   - 下载 [kual-mrinstaller-1.7.N-r19303.tar.xz](https://storage.gra.cloud.ovh.net/v1/AUTH_2ac4bfee353948ec8ea7fd1710574097/mr-public/KUAL/kual-mrinstaller-1.7.N-r19303.tar.xz)
   - 复制到 Kindle 根目录
   - 重启设备，会自动安装

2. **安装 Python**
   - 下载 `kindle-python-0.15.N-r18981.tar.xz`（Touch 版本）
   - 复制到 Kindle 根目录
   - 重启设备，MRPI 会自动识别并安装

3. **验证安装**
   ```bash
   # 通过 SSH 连接后执行
   python3 --version
   # 应显示: Python 3.9.x
   ```

### 依赖库

需要安装以下 Python 库:

```bash
pip install requests
pip install pillow  # 用于图像处理
```

## SSH 连接 (可选但推荐)

安装 SSH 可以更方便地管理文件:

1. **安装 SSH**
   - 通过 KUAL 安装 `SSH Install`
   - 或手动安装 dropbear SSH 服务器

2. **连接方法**
   ```
   IP: 192.168.1.x (查看 Kindle 设置中的 IP)
   Port: 22
   User: root
   Password: (默认无密码或 "rootme")
   ```

3. **使用 SSH 传输文件**
   ```bash
   scp -r ./calendar root@kindle:/mnt/us/
   ```

## 安装日历应用

1. **复制应用文件**
   - 将 `kindle/` 文件夹复制到 `/mnt/us/calendar/`
   - 结构应如下:
   ```
   /mnt/us/calendar/
   ├── main.py
   ├── ui.py
   ├── sync.py
   ├── models.py
   ├── eink.py
   └── config.py
   ```

2. **设置启动方式**

   **方式 A: KUAL 启动**
   - 创建启动脚本 `launch.sh`:
   ```bash
   #!/bin/sh
   cd /mnt/us/calendar
   python3 main.py
   ```

   **方式 B: 自动启动**
   - 编辑 `/etc/inittab` (需要 root)
   - 添加: `::sysinit:/mnt/us/calendar/start.sh`

3. **首次运行**
   - 通过 KUAL 或 SSH 启动应用
   - 检查日志输出是否有错误

## 配置 WiFi 同步

1. **编辑配置文件**
   ```python
   # kindle/config.py
   SERVER_URL = "http://192.168.1.100:8080"
   SYNC_INTERVAL = 30  # 分钟
   ```

2. **设置同步服务器地址**
   - 将 `192.168.1.100:8080` 替换为您的服务器地址
   - 如果在电脑上运行服务端，使用电脑的局域网 IP

## 故障排除

### 越狱失败

- 确认设备型号和系统版本
- 尝试不同的 U盘
- 关闭 WiFi 和休眠

### Python 无法运行

- 检查 Python 路径是否正确
- 确认 libssl 等依赖库已安装
- 查看错误信息: `python3 main.py 2>&1`

### WiFi 无法连接

- 检查 WiFi 密码是否正确
- 确认设备获取到 IP 地址
- 尝试重启路由器

### 屏幕无响应

- 尝试长按电源键 15 秒重启
- 检查电源供应是否稳定
- 如持续问题，可能需要重新安装系统

## 恢复出厂设置 (如需)

1. 设置 → 重置设备
2. 等待设备重启
3. 重新越狱

**注意**: 恢复出厂设置会清除所有数据。

## 相关资源

- Kindle Touch 越狱讨论: https://www.mobileread.com/forums/
- KUAL 官方仓库: https://github.com/KindleUnpack/KUAL
- Python for Kindle: https://github.com/Ge00rG/Kindlets

---
*文档版本: 1.0*
*最后更新: 2026-05-19*

## 免责声明

越狱和改装可能使设备保修失效，并存在一定风险。请谨慎操作，后果自负。