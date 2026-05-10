# Seele 2核2GB 服务器部署优化清单

> 目标：在个人使用、同机部署 MySQL 的前提下，确保项目在 2核2GB 云服务器上稳定运行，避免 OOM。

---

## 1. MySQL 内存降配

修改 MySQL 配置文件（`/etc/mysql/my.cnf` 或 `/etc/my.cnf.d/`）：

```ini
[mysqld]
# 核心内存参数
innodb_buffer_pool_size = 256M
key_buffer_size = 16M
query_cache_size = 0
tmp_table_size = 16M
max_heap_table_size = 16M
thread_cache_size = 4
table_open_cache = 128
innodb_log_buffer_size = 4M

# 限制连接数
max_connections = 30
```

修改后重启 MySQL：
```bash
sudo systemctl restart mysql
```

**预期节省**：~300MB 内存

---

## 2. 后端关闭开发模式

文件：`seele-backend/app/main.py`

修改 `uvicorn.run` 参数：

```python
uvicorn.run(
    'app.main:app',
    host=settings.app_host,
    port=settings.app_port,
    reload=False,    # 关闭热重载
    workers=1,       # 单 worker，避免多进程占用内存
)
```

生产环境启动命令：
```bash
cd seele-backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 9000 --workers 1
```

---

## 3. 数据库连接池调小

文件：`seele-backend/app/database.py`

```python
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,        # 从 20 降至 5
    max_overflow=5,
)
```

---

## 4. 数据同步脚本限制并发

文件：`seele-backend/scripts/sync_history_data.py`

在 `multiprocessing.Pool` 创建前增加限制：

```python
import os

max_workers = min(os.cpu_count(), 2)  # 最多 2 个进程
with Pool(processes=max_workers) as pool:
    ...
```

**注意**：全量历史数据同步建议分批进行（按年份或股票代码分段），避免 pandas 单次加载过多数据导致内存暴涨。

---

## 5. 开启 Swap 虚拟内存

防止突发内存不足时进程被系统杀死：

```bash
# 创建 2GB swap 文件
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 设置开机自动挂载
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

验证：
```bash
swapon --show
free -h
```

---

## 6. 前端部署

构建后使用 Nginx 托管静态文件：

```bash
cd seele-frontend
npm run build
```

Nginx 配置示例：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /path/to/seele-frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 优化后预期内存分布

| 组件 | 内存占用 |
|------|---------|
| Linux 系统 + 基础服务 | ~300MB |
| MySQL（降配后） | ~250MB |
| FastAPI（单 worker） | ~150MB |
| Nginx | ~20MB |
| 空闲缓冲 | ~200MB |
| **剩余可用** | **~1.1GB** |

---

## 高风险操作提醒

- **全量历史数据同步**时 pandas 内存占用可能达到 500MB+，建议在服务器空闲时段执行
- 如频繁出现卡顿，可进一步将 `innodb_buffer_pool_size` 降至 **128M**
- 监控命令：`watch -n 2 free -h`
