# Seele 项目指令

## Windows 进程管理（启动/重启服务前必读）

**重启后端前必须彻底清理所有 Python 进程，不能依赖 `start.py` 的端口检查逻辑。**

### 为什么
1. git bash 中 `taskkill /F` 的 `/` 被解析为路径分隔符，单斜杠命令会失败，旧 worker 残留
2. Windows 下可能出现"僵尸连接"：`Get-NetTCPConnection` 显示 OwningProcess 已死但端口仍在 LISTEN
3. 新 uvicorn 进程仍能绑定到已被旧进程占用的端口，形成多实例同时监听，请求随机被旧实例处理，表现为新代码不生效、端点 404、内存状态无法清空

### 正确操作
1. **先杀全部 Python**：`taskkill //F //IM python.exe //T`（git bash 必须用双斜杠）
2. **或用 PowerShell**：`Stop-Process -Name python -Force`
3. **验证端口释放**：`netstat -ano | findstr :9000`，确认没有 LISTENING 后再启动
4. **前端 8000 端口同理**：`netstat -ano | findstr :8000`

### 禁止
- 不要只 `taskkill //PID <单个pid>`，僵尸进程的 PID 在所有进程管理工具中都可能"幽灵化"
- 不要依赖 `start.py` 的 `kill_process_on_port`，它对僵尸进程无效
- 不要直接 `taskkill /F /IM node.exe` 或 `taskkill /F /IM python.exe`（单斜杠在 git bash 中会失败）

---

## 并发与同步任务

### 严禁使用 ThreadPoolExecutor.map
在可能长时间阻塞的任务中（尤其是外部网络请求），**必须使用 `executor.submit` + `as_completed`**。`map` 有两个致命缺陷：
1. **异常静默吞没**：主线程不消费迭代器时，工作线程异常不会抛出
2. **顺序阻塞死锁**：按提交顺序 yield 结果，任一任务挂死即卡死整个迭代器

```python
# 正确
futures = [executor.submit(_process_stock, stock) for stock in all_stocks]
for future in concurrent.futures.as_completed(futures):
    try:
        future.result()
    except Exception as exc:
        logger.error('处理异常: %s', exc)
```

### 外部数据接口必须加 socket 超时
baostock、akshare 等第三方库**没有内置请求超时**。必须在 socket 层面设置全局超时：

```python
import socket
old_timeout = socket.getdefaulttimeout()
socket.setdefaulttimeout(30)
try:
    rs = bs.query_history_k_data_plus(...)
except socket.timeout:
    return None, 'timeout', 'baostock request timeout (30s)'
finally:
    socket.setdefaulttimeout(old_timeout)
```

注意：`future.result(timeout=X)` 只能保护主线程，无法终止已挂起的工作线程。socket 超时才能真正释放工作线程。

### 长时间任务禁止使用 SSE
浏览器对 SSE 长连接有内置超时（约 10-20 分钟），长时间同步任务会中途断开且无感知。

**必须使用「异步任务触发 + 客户端轮询」模式：**
- 后端：`POST /sync/xxx` 立即返回 `task_id`，后台线程执行
- 后端：`GET /sync/task/{task_id}` 查询进度
- 前端：`setInterval` 轮询（2-3 秒一次）
- 使用 `useSyncTask` composable 实现跨页面进度共享和刷新自动恢复

---

## 数据操作规范

### SQLAlchemy 批量插入数据类型
使用 `INSERT ... ON DUPLICATE KEY UPDATE` 批量写入时，必须确保：
1. **numpy 类型转原生 Python**：`ta` 库返回的 `numpy.float64` 不能被 MySQL 驱动接受，入库前必须包一层 `float()`：`float(round(macd.macd().iloc[-1], 4))`
2. **NaN 转 None**：`if val != val: result[key] = None`
3. **字典键统一**：在函数入口处就初始化所有可能的键为 `None`，确保每只股票返回的字典结构完全一致
4. **批量写入加 try/except 和日志**，失败时至少能定位是哪一批次出错

---

## 前后端接口规范

### 异步任务端点调用一致性
引入后台任务模式后，**必须同步修改前端 API 调用地址**，不能只改后端不改前端。

后台任务的设计模式：
- API 层只负责`注册任务→启动线程→返回 task_id`
- 所有重逻辑放到线程函数里
- 前端用 `task_id` 轮询 `/sync/task/{task_id}` 获取进度和结果
- 同步端点应该考虑废弃或重写，防止前端误调用

---

## 部署配置

### DEPLOY_ENV 切换
- `seele-backend/app/config.py` 是唯一定义 dev/prod 差异的文件
- 通过 `DEPLOY_ENV=dev|prod` 自动推导连接池、热重载、并发数等参数
- dev 默认值：pool_size=20, max_overflow=10, reload=True, sync_max_workers=10
- prod 默认值：pool_size=5, max_overflow=5, reload=False, sync_max_workers=2
- 环境变量如 `DB_POOL_SIZE=3` 可独立覆盖自动推导值

---

## 补充区（由用户追加）

### 启动前：彻底清理旧进程 checklist

**问题实例（2026-05-14）**：执行 `taskkill //F //IM python.exe //T` 后，仍残留 `.venv\Scripts\python.exe start.py`（PID 28760），导致启动后出现**两套 uvicorn 后端**同时运行，只有一套绑定 9000 端口，另一套成为孤儿进程白白占用内存。

**必须执行的清理步骤（按顺序）**：

```bash
# 1. 先杀全部 Python（git bash 用双斜杠）
taskkill //F //IM python.exe //T

# 2. 验证是否真的杀干净了——这条不能省
tasklist | grep -i python

# 3. 如果还有残留，用 powershell 补充清理
powershell -Command "Stop-Process -Name python -Force"

# 4. 确认端口没有 LISTENING
netstat -ano | findstr :9000
netstat -ano | findstr :8000
```

**为什么不能跳过验证**：
- `taskkill` 按进程名匹配，不同路径的 `python.exe` 理论上都会被匹配，但 Windows 下可能存在进程句柄未释放、子进程与父进程脱离等情况
- `start.py` 内部可能启动了子进程（uvicorn + worker），`taskkill //T` 虽然会杀子进程，但如果子进程已经脱离父进程关系，可能幸存
- 残留的旧进程不会报错，只会静默消耗资源，导致代码热重载失效、数据库连接池耗尽等隐蔽问题

### 启动后：验证只启动了一套服务

```bash
# 1. 检查是否只有一个 start.py
tasklist | grep -i python

# 2. 检查只有一个 uvicorn 监听 9000
netstat -ano | findstr :9000

# 3. 检查只有一个 node 监听 8000
netstat -ano | findstr :8000
```

### 反思：为什么本次重启遗漏了旧进程

1. **执行 taskkill 后没有二次确认**：只看了 netstat 的端口状态，没有用 `tasklist` 确认进程是否全部消失
2. **对 `python start.py` 的启动机制不够警惕**：git bash 中执行 `python start.py` 时，如果脚本有 shebang 或存在路径解析差异，可能触发多次启动（见 memory: Windows Bash 命令进程残留与重复问题）
3. **start.py 本身没有健壮的单例保护**：项目级的启动脚本应该增加 PID 文件或端口占用检查，防止重复启动

### 为什么 tasklist 看到多个 python 进程（2026-05-14 追加）

**问题现象**：即使清理干净后启动，执行 `tasklist | grep -i python` 仍看到 3 个甚至 5 个 python 进程。

**根本原因**：
1. **`.venv\Scripts\python.exe` 是 uv 的 shim（约 47KB），不是原生 python（原生约 91KB）**。uv shim 的行为是：启动一个代理进程自身（Parent），再由代理进程创建子进程调用真正的 uv python 解释器执行脚本。因此 `python start.py` 会产生两层进程：shim 代理 + 真实 python。
2. **start.py 原有代码使用 `subprocess.run([sys.executable, '-m', 'uvicorn', ...])`**，`sys.executable` 返回的是 shim 路径，导致又启动了一层 shim → 真实 python 的 uvicorn。旧进程未清干净时，新旧实例叠加，就会出现 5 个甚至更多 python 进程。
3. **uvicorn `--reload` 模式本身会启动 reloader + worker 两个进程**。

**已修复**：`start.py` 已改为直接 `import uvicorn; uvicorn.run(...)` 调用，消除了 `subprocess.run` 产生的额外一层 start.py 子进程。

**正常启动后的进程结构应为**：
```
Bash/PowerShell (PID X)
  └─ .venv\Scripts\python.exe start.py      [uv shim 代理进程，不占端口]
        └─ uv\python\...\python.exe start.py  [真实 python，uvicorn reloader，监听 9000]
              └─ uv\python\...\python.exe      [uvicorn worker]
```

**判断是否有残留的唯一标准**：`netstat -ano | findstr :9000` 只能有**一个** `LISTENING` 进程。tasklist 看到 3 个 python 是正常的（shim + reloader + worker），但如果有两个都在监听 9000，或者有两个 start.py 各自带有 uvicorn 子进程，就是残留未清干净。

<!-- 用户可在此追加新的项目级规则，我会自动读取 -->

## Git 工作流规范

### 禁止直接在 main 分支修改内容

**main 分支只能通过 PR（Pull Request）合并进入，禁止任何直接提交、推送或覆盖。**

所有代码变更必须在功能分支（如 `feature/xxx`）上开发，经过 PR review 后合并到 main。

原因：
- 保证 main 分支始终是可追溯、可回滚的
- 防止本地实验性修改污染生产基线
- 确保部署版本与代码审查记录一致

如果需要在 main 上修复问题，应：
1. 从 main 切出 `hotfix/xxx` 分支
2. 在 hotfix 分支上修改
3. 通过 PR 合并回 main

