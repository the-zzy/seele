# Seele 2核2GB 云服务器部署检查清单

> 按顺序执行，每一步确认通过后再进行下一步。

---

## 一、服务器基础环境检查

### 1.1 系统资源确认

```bash
# 检查 CPU 核心数
cat /proc/cpuinfo | grep 'processor' | wc -l
# 预期输出: 2

# 检查内存总量
free -h
# 预期: total ≈ 1.8G~2.0G

# 检查磁盘空间
df -h /
# 预期: 可用空间 >= 20GB（40G 云盘预留系统、数据、日志空间）

# 检查系统版本
cat /etc/os-release | grep PRETTY_NAME
# 预期: Ubuntu 20.04+ 或 Debian 11+
```

### 1.2 Swap 配置检查

```bash
swapon --show
# 预期: 显示 /swapfile，size >= 2G

free -h | grep Swap
# 预期: swap total >= 2.0G
```

**如未配置**，执行：

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 二、依赖软件安装检查

### 2.1 Python 环境

```bash
python3 --version
# 预期: Python 3.8.x 或更高

pip3 --version
# 预期: pip 21+

# 检查虚拟环境支持
python3 -m venv --help > /dev/null 2>&1 && echo 'OK' || echo '需安装 python3-venv'
```

**如未安装**：

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv
```

### 2.2 MySQL 服务

```bash
mysql --version
# 预期: mysql  Ver 8.0.x 或 5.7.x

sudo systemctl status mysql
# 预期: active (running)
```

**如未安装**：

```bash
sudo apt-get install -y mysql-server
sudo systemctl enable mysql
sudo systemctl start mysql
```

### 2.3 Node.js 环境

```bash
node --version
# 预期: v16.x 或更高

npm --version
# 预期: 8.x 或更高
```

**如未安装**：

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### 2.4 Nginx

```bash
nginx -v
# 预期: nginx version: nginx/1.x.x

sudo systemctl status nginx
# 预期: active (running)
```

**如未安装**：

```bash
sudo apt-get install -y nginx
```

---

## 三、数据库准备检查

### 3.1 数据库与用户

```bash
sudo mysql -u root -p -e "SHOW DATABASES LIKE 'seele';"
# 预期: 显示 seele 数据库，若无则创建

# 创建数据库（如不存在）
sudo mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS seele CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 3.2 MySQL 内存降配

检查配置文件：

```bash
cat /etc/mysql/mysql.conf.d/mysqld.cnf | grep -E 'innodb_buffer_pool_size|max_connections|key_buffer_size'
# 预期: innodb_buffer_pool_size = 256M, max_connections = 30
```

**推荐配置**（添加到 `/etc/mysql/mysql.conf.d/mysqld.cnf`）：

```ini
[mysqld]
innodb_buffer_pool_size = 256M
key_buffer_size = 16M
query_cache_size = 0
tmp_table_size = 16M
max_heap_table_size = 16M
thread_cache_size = 4
table_open_cache = 128
innodb_log_buffer_size = 4M
max_connections = 30
```

修改后重启：

```bash
sudo systemctl restart mysql
```

### 3.3 数据表初始化

```bash
# 进入项目目录
cd /opt/seele

# 按顺序执行迁移文件（或使用后端自动建表）
sudo mysql -u root -p seele < db-ops/migrations/2026-04-26-00-init-schema.sql
# ... 依次执行其他迁移文件
```

**或**启动后端时 `main.py` 会自动 `create_all`，但索引优化需手动执行迁移。

---

## 四、后端部署检查

### 4.1 代码部署

```bash
# 确认项目目录存在
ls /opt/seele/seele-backend/
# 预期: app/ requirements.txt start.py .env.example ...
```

### 4.2 虚拟环境

```bash
cd /opt/seele/seele-backend

# 创建虚拟环境（如未创建）
python3 -m venv .venv

# 激活并安装依赖
source .venv/bin/activate
pip install -r requirements.txt
# 预期: 全部 Successfully installed，无 ERROR
```

### 4.3 环境变量配置

```bash
cat /opt/seele/seele-backend/.env
```

**必须包含**：

```bash
DEPLOY_ENV=prod
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=你的密码
DB_NAME=seele
APP_HOST=0.0.0.0
APP_PORT=9000
MOONSHOT_API_KEY=你的KimiKey  # 如需AI功能
```

**严禁**使用默认空密码部署到公网。

### 4.4 端口占用检查

```bash
sudo netstat -tlnp | grep :9000
# 预期: 无输出（未被占用）

# 或
ss -tlnp | grep :9000
```

---

## 五、前端构建检查

### 5.1 依赖安装

```bash
cd /opt/seele/seele-frontend

npm install
# 预期: 无 ERR! 日志
```

### 5.2 生产构建

```bash
npm run build
# 预期: Build complete. dist/ 目录生成

ls /opt/seele/seele-frontend/dist/
# 预期: index.html, js/, css/, favicon.ico 等
```

---

## 六、Nginx 配置检查

### 6.1 配置文件

```bash
cat /etc/nginx/sites-available/seele
```

**预期内容**（已启用 gzip + 静态缓存，适配 3Mbps 带宽）：

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 或服务器 IP

    root /opt/seele/seele-frontend/dist;
    index index.html;

    # 3Mbps 带宽优化：启用 gzip
    gzip on;
    gzip_vary on;
    gzip_min_length 1k;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml
        font/ttf
        font/otf
        font/x-woff;

    # 连接优化
    tcp_nodelay on;
    tcp_nopush on;
    keepalive_timeout 65;

    # 静态资源缓存（30天），减少 3Mbps 带宽重复传输
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    location / {
        try_files $uri $uri/ /index.html;
        # HTML 不缓存，确保前端更新及时生效
        add_header Cache-Control "no-cache";
    }

    location /api {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # 对 API 响应也启用压缩
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
}
```

### 6.2 配置生效检查

```bash
sudo nginx -t
# 预期: syntax is ok, test is successful

sudo systemctl restart nginx
sudo systemctl status nginx
# 预期: active (running)
```

---

## 七、Systemd 服务配置检查

### 7.1 服务文件

```bash
cat /etc/systemd/system/seele-backend.service
```

**预期内容**：

```ini
[Unit]
Description=Seele Backend Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/seele/seele-backend
Environment=DEPLOY_ENV=prod
EnvironmentFile=/opt/seele/seele-backend/.env
ExecStart=/opt/seele/seele-backend/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 9000 --workers 1
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 7.2 服务加载

```bash
sudo systemctl daemon-reload
sudo systemctl enable seele-backend
```

---

## 八、启动与验证

### 8.1 启动后端服务

```bash
sudo systemctl start seele-backend

# 等待 3 秒后检查状态
sudo systemctl status seele-backend
# 预期: active (running)，无红色错误日志

# 查看实时日志
sudo journalctl -u seele-backend -f
# 预期: [SCHEDULER] 定时任务调度器已启动，无异常 Traceback
```

### 8.2 端口监听验证

```bash
ss -tlnp | grep :9000
# 预期: 只有 1 个 LISTEN 进程（单 worker）

ss -tlnp | grep :80
# 预期: nginx 监听 80
```

### 8.3 健康检查

```bash
curl http://127.0.0.1:9000/health
# 预期: {"code":200,"message":"OK","data":null}

curl http://127.0.0.1:9000/
# 预期: {"code":200,"message":"Seele 股票数据管理API...","data":null}
```

### 8.4 前端访问验证

```bash
curl -I http://127.0.0.1:80
# 预期: HTTP/1.1 200 OK
```

通过浏览器访问 `http://服务器IP` 或域名，确认：
- 页面正常加载
- 登录后可正常查看股票列表
- API 请求无 502/504 错误

---

## 九、磁盘与带宽专项（40GB 云盘 + 3Mbps）

### 9.1 磁盘空间规划

40GB 云盘分配参考：

| 用途 | 预估占用 | 说明 |
|------|---------|------|
| Linux 系统 | ~8GB | 基础系统 + 软件包 |
| MySQL 数据 | ~2-5GB | 日线数据持续增长，见下方估算 |
| 后端 + venv | ~500MB | Python 依赖 |
| 前端 dist | ~10MB | 构建产物 |
| Nginx/系统日志 | ~1-2GB | 需配置日志轮转 |
| 剩余可用 | **~22GB** | 预留缓冲 |

```bash
# 检查当前磁盘占用
df -h /
# 预期: 可用 >= 20GB

# 检查各目录占用
du -sh /var/log /var/lib/mysql /opt/seele
```

### 9.2 日志轮转配置（防止磁盘占满）

创建 Nginx 日志轮转配置：

```bash
sudo tee /etc/logrotate.d/nginx-custom << 'EOF'
/var/log/nginx/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 $(cat /var/run/nginx.pid)
    endscript
    size 50M
}
EOF
```

Systemd 日志限制：

```bash
sudo tee -a /etc/systemd/journald.conf << 'EOF'
SystemMaxUse=500M
MaxFileSize=50M
EOF

sudo systemctl restart systemd-journald
```

后端日志清理（如使用文件日志）：

```bash
# 每周清理 7 天前的日志
sudo tee /etc/cron.weekly/cleanup-seele-logs << 'EOF'
#!/bin/bash
find /opt/seele/seele-backend/logs -name "*.log" -mtime +7 -delete
EOF
sudo chmod +x /etc/cron.weekly/cleanup-seele-logs
```

### 9.3 3Mbps 带宽测算

3Mbps = **384KB/s**（上行与下行共享）。

**首次访问加载测算**：

| 资源 | 原始大小 | gzip 后 | 3Mbps 加载时间 |
|------|---------|---------|---------------|
| chunk-vendors.js | 6.5MB | ~2.0MB | ~5.3s |
| app.js | 1.5MB | ~0.5MB | ~1.3s |
| 其他 (css/html/ico) | ~2MB | ~0.5MB | ~1.3s |
| **合计** | **~10MB** | **~3MB** | **~8s** |

> 未开启 gzip 时首次加载需 **~27 秒**，启用后降至 **~8 秒**。

### 9.4 gzip 生效验证

```bash
# 验证 JS 文件是否被压缩
curl -I -H "Accept-Encoding: gzip" http://127.0.0.1/js/app.js
# 预期: Content-Encoding: gzip

# 验证 API 响应是否被压缩
curl -I -H "Accept-Encoding: gzip" http://127.0.0.1/api/stock/basic?page=1&page_size=20
# 预期: Content-Encoding: gzip
```

### 9.5 数据库数据增长预估

A 股约 5000+ 只股票：

| 数据类型 | 每日增量 | 年增量 |
|---------|---------|--------|
| 日线数据 (stock_daily) | ~5000 条 | ~125 万条 |
| 指标数据 (stock_daily_indicator) | ~5000 条 | ~125 万条 |
| 基础信息 (stock_basic) | ~5000 条（首次）| 少量更新 |

**存储估算**（单条 100-200 字节）：
- 日线 + 指标一年约 **500MB**
- 5 年数据约 **2-3GB**
- 40GB 云盘足够支撑 **10 年以上**

```bash
# 查看当前数据库大小
sudo mysql -u root -p -e "SELECT table_name, ROUND(data_length/1024/1024,2) AS size_mb FROM information_schema.tables WHERE table_schema='seele' ORDER BY size_mb DESC;"
```

### 9.6 带宽使用建议

1. **避免高峰时段全量同步**：定时任务（日线同步、指标计算）集中在交易日 17:00-18:00，与自身使用错开。
2. **分页查询控制 page_size**：股票列表、交易记录等接口默认 20-50 条/页，避免单次返回千条数据。
3. **静态资源长期缓存**：Nginx 已配置 js/css 30 天缓存，重复访问几乎不耗带宽。
4. **监控出口带宽**：

```bash
# 实时查看网卡流量（安装 iftop）
sudo apt-get install -y iftop
sudo iftop -i eth0
```

---

## 十、内存监控（部署后持续观察）

```bash
# 实时内存监控
watch -n 5 free -h

# 各进程内存占用
ps aux --sort=-%mem | head -n 10

# MySQL 内存占用
ps aux | grep mysqld | grep -v grep
```

**生产环境正常内存分布**：

| 组件 | 预期占用 |
|------|---------|
| Linux 系统 + 基础服务 | ~300MB |
| MySQL（降配后） | ~250MB |
| FastAPI（单 worker） | ~150MB |
| Nginx | ~20MB |
| 空闲缓冲 | ~200MB |
| **剩余可用** | **~1.1GB** |

---

## 十一、常见问题快速排查

| 现象 | 排查命令 | 常见原因 |
|------|---------|---------|
| 502 Bad Gateway | `sudo systemctl status seele-backend` | 后端未启动或崩溃 |
| 端口被占用 | `sudo lsof -i :9000` | 旧进程未清理 |
| 数据库连接失败 | `sudo mysql -u root -p` | 密码错误或 MySQL 未启动 |
| 前端白屏 | `ls /opt/seele/seele-frontend/dist/` | 未执行 npm run build |
| 内存不足 OOM | `dmesg \| grep -i kill` | 未配置 swap 或 MySQL 未降配 |
| 定时任务未执行 | `sudo journalctl -u seele-backend \| grep SCHEDULER` | 时区或 scheduler 异常 |

---

## 附录：一键快速验证脚本

```bash
#!/bin/bash
echo "=== Seele 部署快速验证 ==="
echo ""
echo "[1/6] 系统资源:"
free -h | grep -E 'Mem|Swap'
echo ""
echo "[2/6] 关键进程:"
sudo systemctl is-active mysql nginx seele-backend
echo ""
echo "[3/6] 端口监听:"
ss -tlnp | grep -E ':80|:9000'
echo ""
echo "[4/6] 后端健康:"
curl -s http://127.0.0.1:9000/health | head -c 100
echo ""
echo ""
echo "[5/6] 前端访问:"
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:80
echo ""
echo ""
echo "[6/6] 内存占用 TOP5:"
ps aux --sort=-%mem | head -n 6
echo ""
echo "=== 验证完成 ==="
```

将以上内容保存为 `verify-deployment.sh`，执行 `bash verify-deployment.sh` 即可快速验收。
