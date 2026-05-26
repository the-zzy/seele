# Seele 生产服务器资产清单

> 记录部署目标服务器的硬件、系统与软件环境信息，便于团队维护和后续扩容参考。

---

## 基础硬件

| 项目 | 配置 |
|------|------|
| 提供商 | 阿里云 |
| 实例规格 | 2核2GB |
| 云盘 | 40GB |
| 公网带宽 | 3Mbps |
| 架构 | x86_64 |

---

## 操作系统

| 项目 | 详情 |
|------|------|
| 发行版 | Alibaba Cloud Linux 3.2104 U12.2 (OpenAnolis Edition) |
| 平台 ID | platform:al8 |
| 兼容系 | RHEL / Fedora / CentOS / Anolis |
| 包管理器 | `dnf` |

---

## 软件环境

| 软件 | 版本 | 安装方式 | 服务名 |
|------|------|---------|--------|
| Python | 3.12.7 | 系统自带 | - |
| MySQL | 8.0.45 | `dnf install mysql-server` | `mysqld` |
| Node.js | v22.22.2 | `dnf install nodejs npm` | - |
| npm | 10.9.7 | 随 Node.js 安装 | - |
| Nginx | 1.20.1 | `dnf install nginx` | `nginx` |

---

## 部署适配注意

- 项目自带的 `deploy/setup-2c2g.sh` 基于 `apt-get`，此服务器需改用 `dnf`
- MySQL 服务名为 `mysqld`（Ubuntu 下为 `mysql`）
- 项目部署目录: `/opt/seele`
- 前端端口: 80 (Nginx)
- 后端端口: 9000 (Systemd)

---

## 变更记录

| 日期 | 操作人 | 变更内容 |
|------|--------|---------|
| 2026-05-27 | - | 初始化服务器，安装 MySQL / Node.js / Nginx |
