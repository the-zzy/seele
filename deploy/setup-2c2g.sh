#!/bin/bash
set -e

echo "========== Seele 2核2GB 服务器部署脚本 =========="

# 1. 创建 Swap
if ! swapon --show | grep -q /swapfile; then
    echo "[1/5] 创建 2GB Swap..."
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
else
    echo "[1/5] Swap 已存在，跳过"
fi

# 2. 安装 Nginx
echo "[2/5] 安装 Nginx..."
sudo apt-get update
sudo apt-get install -y nginx

# 3. 配置 Nginx
echo "[3/5] 配置 Nginx..."
sudo cp deploy/nginx-seele.conf /etc/nginx/sites-available/seele
sudo ln -sf /etc/nginx/sites-available/seele /etc/nginx/sites-enabled/seele
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# 4. 安装 Systemd 服务
echo "[4/5] 安装 Systemd 服务..."
sudo cp deploy/seele-backend.service /etc/systemd/system/seele-backend.service
sudo systemctl daemon-reload
sudo systemctl enable seele-backend

# 5. 完成
echo "[5/5] 部署完成！"
echo ""
echo "优化后预期内存分布（2核2GB）："
echo "  Linux 系统 + 基础服务    ~300MB"
echo "  MySQL（降配后）          ~250MB"
echo "  FastAPI（单 worker）      ~150MB"
echo "  Nginx                    ~20MB"
echo "  空闲缓冲                 ~200MB"
echo "  剩余可用                 ~1.1GB"
echo ""
echo "请手动完成以下步骤："
echo "  1. 修改 /etc/mysql/my.cnf 降低 MySQL 内存配置"
echo "  2. 构建前端：cd seele-frontend && npm run build"
echo "  3. 将 dist 目录部署到 <DEPLOY_DIR>/frontend-dist"
echo "  4. 启动后端：sudo systemctl start seele-backend"
echo ""
