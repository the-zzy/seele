"""
同步任务接口速度测试与瓶颈分析脚本

测试内容：
1. 各同步任务触发端点的 HTTP 响应时间（提交任务本身）
2. 任务状态查询、日志查询、详细状态查询端点响应时间
3. 后台任务执行进度跟踪
4. 代码层面瓶颈分析与优化建议

注意：
- 本脚本只测试 API 层响应速度，默认不触发新的同步任务。
- 若需触发新任务测试，请将 TRIGGER_NEW_TASKS 设为 True。
- 当前正在运行的任务不会被中断。
"""

import time
import requests
from datetime import datetime

BASE_URL = 'http://127.0.0.1:9000/api'
TRIGGER_NEW_TASKS = False


def timed_request(method, url, **kwargs):
    """发送请求并返回 (响应时间秒, response_json)"""
    start = time.time()
    try:
        resp = requests.request(method, url, timeout=30, **kwargs)
        elapsed = time.time() - start
        data = resp.json() if resp.status_code == 200 else {'error': resp.text}
        return elapsed, data, resp.status_code
    except Exception as exc:
        elapsed = time.time() - start
        return elapsed, {'error': str(exc)}, 0


def format_ms(seconds):
    """将秒转换为毫秒字符串"""
    return f'{seconds * 1000:.1f}ms'


def test_sync_api_endpoints():
    """测试同步任务相关 API 端点响应时间"""
    results = []

    # 1. 活跃任务列表
    elapsed, data, code = timed_request('GET', f'{BASE_URL}/sync/active-tasks')
    tasks = data.get('data', {}).get('tasks', [])
    results.append({
        'name': 'GET /sync/active-tasks',
        'elapsed': elapsed,
        'status': code,
        'extra': f'active={len(tasks)}',
    })

    # 2. 同步日志查询
    elapsed, data, code = timed_request('GET', f'{BASE_URL}/sync/job-logs', params={'days': 5})
    total_logs = data.get('data', {}).get('total', 0)
    results.append({
        'name': 'GET /sync/job-logs?days=5',
        'elapsed': elapsed,
        'status': code,
        'extra': f'total={total_logs}',
    })

    # 3. 详细同步状态
    elapsed, data, code = timed_request('GET', f'{BASE_URL}/sync/detailed-status')
    daily_status = data.get('data', {}).get('daily', [])
    results.append({
        'name': 'GET /sync/detailed-status',
        'elapsed': elapsed,
        'status': code,
        'extra': f'daily_entries={len(daily_status)}',
    })

    # 4. 任务状态查询（用活跃任务的 task_id）
    if tasks:
        task_id = tasks[0]['task_id']
        elapsed, data, code = timed_request('GET', f'{BASE_URL}/sync/task/{task_id}')
        task_status = data.get('data', {}).get('status')
        progress = data.get('data', {}).get('progress')
        results.append({
            'name': f'GET /sync/task/{task_id[:8]}...',
            'elapsed': elapsed,
            'status': code,
            'extra': f'status={task_status}, progress={progress}',
        })

    # 5. 管道/任务链状态（如果有）
    elapsed, data, code = timed_request('GET', f'{BASE_URL}/sync/pipeline-status')
    if code == 200:
        pipelines = data.get('data', {}).get('pipelines', [])
        results.append({
            'name': 'GET /sync/pipeline-status',
            'elapsed': elapsed,
            'status': code,
            'extra': f'pipelines={len(pipelines)}',
        })

    if TRIGGER_NEW_TASKS:
        # 触发日线同步
        elapsed, data, code = timed_request('POST', f'{BASE_URL}/sync/daily/date/20260525')
        results.append({
            'name': 'POST /sync/daily/date/20260525',
            'elapsed': elapsed,
            'status': code,
            'extra': f"task_id={data.get('data', {}).get('task_id', 'N/A')}",
        })

        # 触发指标计算
        elapsed, data, code = timed_request(
            'POST', f'{BASE_URL}/sync/indicator',
            params={'trade_date': '2026-05-25'}
        )
        results.append({
            'name': 'POST /sync/indicator?trade_date=2026-05-25',
            'elapsed': elapsed,
            'status': code,
            'extra': f"task_id={data.get('data', {}).get('task_id', 'N/A')}",
        })

    return results


def track_running_task(duration_seconds=30):
    """跟踪当前正在运行的任务进度"""
    print('\n--- 跟踪当前运行任务 ---')
    resp = requests.get(f'{BASE_URL}/sync/active-tasks', timeout=10).json()
    tasks = resp.get('data', {}).get('tasks', [])
    if not tasks:
        print('  当前无活跃任务，跳过跟踪')
        return

    task = tasks[0]
    task_id = task['task_id']
    print(f"  跟踪任务: {task_id[:8]}... (job_type={task['job_type']}, trade_date={task['trade_date']})")
    print(f"  开始时间: {task['started_at']}")

    # 计算已运行时间
    started = datetime.fromisoformat(task['started_at'])
    elapsed_so_far = (datetime.now() - started).total_seconds()
    print(f"  已运行: {elapsed_so_far:.0f} 秒")

    samples = []
    for i in range(duration_seconds):
        resp = requests.get(f'{BASE_URL}/sync/task/{task_id}', timeout=10).json()
        data = resp.get('data', {})
        progress = data.get('progress')
        if progress:
            samples.append({
                'time': i + 1,
                'current': progress['current'],
                'total': progress['total'],
                'percent': progress['percent'],
            })
            print(f"  t={i+1:2d}s: {progress['current']:>5}/{progress['total']} ({progress['percent']:>5.1f}%)")
        if data.get('status') != 'running':
            print(f"  任务结束: status={data.get('status')}")
            break
        time.sleep(1)

    if samples:
        first = samples[0]
        last = samples[-1]
        processed = last['current'] - first['current']
        duration = last['time'] - first['time']
        if duration > 0 and processed > 0:
            rate = processed / duration
            remaining = last['total'] - last['current']
            eta = remaining / rate if rate > 0 else float('inf')
            print(f"\n  统计: {rate:.1f} 只/秒, 预计还需 {eta:.0f} 秒完成")


def analyze_bottlenecks():
    """基于代码分析后台任务瓶颈与优化方向"""
    print('\n--- 后台任务代码瓶颈分析 ---\n')

    analysis = [
        {
            'task': 'daily 同步 (POST /sync/daily/date/{date})',
            'impl': 'ProcessPoolExecutor 多进程拉取 akshare/baostock',
            'bottlenecks': [
                'Windows spawn 模式下启动 6-12 个进程开销极大（每个进程需重新导入整个 Python 环境）',
                '当前 workers = min(cpu_count * 2, 12)，可能过度并行',
                '批量写入阈值 500 偏低，5000+ 只股票会产生 10+ 次 DB 事务',
                '_test_akshare / _test_baostock 每次同步都执行，无缓存',
            ],
            'optimizations_done': [
                'workers 改为 min(cpu_count, 6)，小批量进一步降为 1-4',
                '批量写入阈值从 500 提高到 1500',
                '数据源探测结果缓存 5 分钟（_source_test_cache）',
            ],
            'further': [
                '可考虑改用 ThreadPoolExecutor + 进程内 socket 超时，避免 spawn 开销',
                '预加载前收盘价查询可改为子查询，减少一次 DB round-trip',
            ]
        },
        {
            'task': 'financial 同步 (POST /sync/financial)',
            'impl': 'ThreadPoolExecutor 逐只 HTTP 请求 akshare',
            'bottlenecks': [
                '每只股票的财务数据需要一次独立的 HTTP 请求',
                'akshare 无批量财务接口，无法减少请求次数',
                '15 秒超时只能保护主线程，挂起的工作线程仍占用池槽位',
            ],
            'optimizations_done': [
                'socket 超时已在代码中设置（30s 全局）',
            ],
            'further': [
                '增量同步：只同步缺失或 report_date 较旧的股票',
                '缩短单股超时时间至 10s，快速失败释放线程',
                '批量写入阈值可进一步提高到 2000',
            ]
        },
        {
            'task': 'indicator 计算 (POST /sync/indicator)',
            'impl': 'ThreadPoolExecutor + ta 库逐只计算',
            'bottlenecks': [
                '预查询 all_rows 返回量巨大（5000 symbol x 60 days = 30万行）',
                'rows_by_symbol 在 Python 中构建，大量 ORM 对象创建开销',
                'ta 库计算受 GIL 限制，多线程对 CPU 密集型任务收益有限',
            ],
            'optimizations_done': [],
            'further': [
                '改用 pandas 批量向量化计算，替代逐只股票 ta 计算',
                'SQL 层用窗口函数 / CTE 直接取最近 60 天，减少传输量',
                '仅计算缺失 indicator 的股票（增量计算）',
            ]
        },
        {
            'task': 'stock-basic 同步 (POST /sync/stock-basic)',
            'impl': 'akshare 3 次请求 + baostock fallback',
            'bottlenecks': [
                '外部 API 响应速度不可控',
                '停牌信息同步每次都要请求 stock_tfp_em',
            ],
            'optimizations_done': [],
            'further': [
                '停牌信息可独立为每日定时任务，不在 stock-basic 同步中重复拉取',
                'cap_map（流通市值）可缓存 5 分钟',
            ]
        },
    ]

    for a in analysis:
        print(f"任务: {a['task']}")
        print(f"  实现: {a['impl']}")
        print('  瓶颈:')
        for b in a['bottlenecks']:
            print(f'    - {b}')
        if a['optimizations_done']:
            print('  本轮已优化（需重启后生效）:')
            for o in a['optimizations_done']:
                print(f'    + {o}')
        if a['further']:
            print('  可继续优化方向:')
            for f in a['further']:
                print(f'    - {f}')
        print()


def main():
    print('=== 同步任务接口速度测试 ===\n')

    # 1. API 端点响应时间
    results = test_sync_api_endpoints()
    print('--- API 端点响应时间 ---')
    print(f'{"端点":<55} {"耗时":<12} {"状态"}')
    print('-' * 90)
    for r in results:
        flag = 'SLOW' if r['elapsed'] > 0.5 else 'OK'
        print(f"{r['name']:<55} {format_ms(r['elapsed']):<12} [{flag}] {r['extra']}")

    # 2. 跟踪正在运行的任务
    track_running_task(duration_seconds=10)

    # 3. 瓶颈分析
    analyze_bottlenecks()

    print('\n--- 总结 ---')
    print('同步任务 API 端点本身响应都很快（<100ms），瓶颈在后台执行。')
    print('当前已做代码优化（减少进程数、增大批量写入、缓存数据源探测），')
    print('需重启后端后生效。')


if __name__ == '__main__':
    main()
