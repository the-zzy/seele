#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地后端接口测速脚本（排除同步任务类接口）"""

import json
import subprocess
import sys
from datetime import datetime
from urllib.parse import urljoin

BASE_URL = 'http://127.0.0.1:9000'
ADMIN_PASSWORD = 'seele'

ENDPOINTS = [
    # 根/健康
    {'name': '根路径', 'method': 'GET', 'path': '/', 'body': None},
    {'name': '健康检查', 'method': 'GET', 'path': '/health', 'body': None},

    # 认证
    {'name': '管理员登录', 'method': 'POST', 'path': '/api/auth/login', 'body': {'username': 'admin', 'password': ADMIN_PASSWORD}},
    {'name': '获取当前用户', 'method': 'GET', 'path': '/api/auth/me', 'body': None, 'auth': True},

    # 股票基础
    {'name': '股票基础分页', 'method': 'POST', 'path': '/api/stock/basic/page', 'body': {'page_num': 1, 'page_size': 10}},
    {'name': '公司概况', 'method': 'GET', 'path': '/api/stock/basic/000001/survey', 'body': None},
    {'name': '同步单股公司概况', 'method': 'POST', 'path': '/api/stock/basic/000001/sync-survey', 'body': {}},
    {'name': '同步单股细分行业', 'method': 'POST', 'path': '/api/stock/basic/000001/sync-industry-detail', 'body': {}},

    # 股票日线
    {'name': '按日期分页日线', 'method': 'GET', 'path': '/api/stock/daily/date/2024-01-02/all?page_num=1&page_size=10', 'body': None},
    {'name': '按代码历史日线', 'method': 'GET', 'path': '/api/stock/daily/symbol/000001', 'body': None},

    # 指标
    {'name': '计算日线指标', 'method': 'POST', 'path': '/api/stock/indicator/compute?trade_date=2020-01-02', 'body': {}},

    # 选股策略
    {'name': '主升浪选股', 'method': 'POST', 'path': '/api/stock/daily/mainwave-picker', 'body': {'page_num': 1, 'page_size': 10}},
    {'name': '单股主升浪检测', 'method': 'GET', 'path': '/api/stock/daily/mainwave-detect/000001', 'body': None},
    {'name': '批量主升浪检测', 'method': 'POST', 'path': '/api/stock/daily/mainwave-detect/batch', 'body': {'symbols': ['000001', '000002']}},

    # 财务
    {'name': '财务指标列表', 'method': 'GET', 'path': '/api/financial?page_num=1&page_size=10', 'body': None},
    {'name': '单股财务详情', 'method': 'GET', 'path': '/api/financial/000001', 'body': None},

    # 持仓（部分需登录）
    {'name': '录入交易', 'method': 'POST', 'path': '/api/portfolio/trades', 'body': {'symbol': '000001', 'name': '平安银行', 'trade_type': 'BUY', 'quantity': 100, 'price': 13.5, 'fee': 5.0, 'trade_date': '2020-01-02'}},
    {'name': '录入做T', 'method': 'POST', 'path': '/api/portfolio/day-trades', 'body': {'symbol': '000001', 'name': '平安银行', 'quantity': 100, 'buy_price': 13.5, 'sell_price': 13.6, 'trade_date': '2020-01-02'}},
    {'name': '交易记录列表', 'method': 'GET', 'path': '/api/portfolio/trades', 'body': None},
    {'name': '当前持仓', 'method': 'GET', 'path': '/api/portfolio/positions', 'body': None},
    {'name': '已清仓记录', 'method': 'GET', 'path': '/api/portfolio/closed', 'body': None},
    {'name': '持仓预警', 'method': 'GET', 'path': '/api/portfolio/alerts', 'body': None},
    {'name': '持仓配置', 'method': 'GET', 'path': '/api/portfolio/config', 'body': None},
    {'name': '资产总览', 'method': 'GET', 'path': '/api/portfolio/summary', 'body': None},
    {'name': '每日盈亏', 'method': 'GET', 'path': '/api/portfolio/daily-pnl', 'body': None},
    {'name': '持仓分布', 'method': 'GET', 'path': '/api/portfolio/distribution', 'body': None},
    {'name': '持仓快照同步', 'method': 'POST', 'path': '/api/portfolio/sync', 'body': {}},
    {'name': '重建每日资产', 'method': 'POST', 'path': '/api/portfolio/rebuild-daily', 'body': {}},

    # 市场情绪
    {'name': '计算市场情绪', 'method': 'POST', 'path': '/api/market/sentiment/compute?trade_date=2020-01-02', 'body': {}},
    {'name': '每日市场情绪', 'method': 'GET', 'path': '/api/market/sentiment/daily?start_date=2020-01-01&end_date=2020-01-05', 'body': None},

    # 指数
    {'name': '指数列表', 'method': 'GET', 'path': '/api/index/list', 'body': None},

    # 系统日志
    {'name': '错误日志', 'method': 'GET', 'path': '/api/system/logs/errors?page_num=1&page_size=10', 'body': None},
    {'name': '操作日志', 'method': 'GET', 'path': '/api/system/logs/operations?page_num=1&page_size=10', 'body': None},
    {'name': '日志概览', 'method': 'GET', 'path': '/api/system/logs/overview', 'body': None},

    # 板块/ETF
    {'name': '板块列表', 'method': 'POST', 'path': '/api/board/list', 'body': {'category': 'industry', 'page_num': 1, 'page_size': 10}},
    {'name': '板块日线', 'method': 'POST', 'path': '/api/board/daily', 'body': {'code': 'BK0428', 'page_num': 1, 'page_size': 10}},
    {'name': '板块成分股', 'method': 'GET', 'path': '/api/board/constituents/BK0428', 'body': None},
    {'name': '保存板块关联', 'method': 'POST', 'path': '/api/board/constituents/save', 'body': {'board_code': 'BK0428', 'constituent_symbol': '000001', 'name': '平安银行'}},

    # 交易日历
    {'name': '最近交易日', 'method': 'GET', 'path': '/api/trade-calendar/latest', 'body': None},

    # 图库
    {'name': '图片列表', 'method': 'GET', 'path': '/api/gallery/images', 'body': None},

    # 访客
    {'name': '访客上报', 'method': 'POST', 'path': '/api/visitor/track', 'body': {'path': '/test', 'referrer': ''}},
    {'name': '访客日志', 'method': 'GET', 'path': '/api/visitor/logs?page_num=1&page_size=10', 'body': None},

    # Agent
    {'name': 'Agent对话', 'method': 'POST', 'path': '/api/agent/chat', 'body': {'message': '你好', 'session_id': 'test'}},
    {'name': '清除Agent会话', 'method': 'DELETE', 'path': '/api/agent/session/test', 'body': None},
]


def curl_once(method, url, body, token=None):
    cmd = [
        'curl', '-s', '-o', '/dev/null', '-w',
        '%{http_code}\t%{time_total}\t%{time_connect}\t%{time_namelookup}\t%{size_download}\n',
        '-X', method,
    ]
    if token:
        cmd += ['-H', f'Authorization: Bearer {token}']
    if body is not None:
        cmd += ['-H', 'Content-Type: application/json', '-d', json.dumps(body, ensure_ascii=False)]
    cmd.append(url)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        parts = result.stdout.strip().split('\t')
        return {
            'status': int(parts[0]) if parts[0].isdigit() else None,
            'total': float(parts[1]) if len(parts) > 1 else None,
            'connect': float(parts[2]) if len(parts) > 2 else None,
            'namelookup': float(parts[3]) if len(parts) > 3 else None,
            'size': int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0,
            'error': result.stderr.strip() if result.stderr else None,
        }
    except subprocess.TimeoutExpired:
        return {'status': None, 'total': 60.0, 'connect': None, 'namelookup': None, 'size': 0, 'error': 'timeout'}
    except Exception as exc:
        return {'status': None, 'total': None, 'connect': None, 'namelookup': None, 'size': 0, 'error': str(exc)}


def login():
    url = urljoin(BASE_URL, '/api/auth/login')
    metric = curl_once('POST', url, {'username': 'admin', 'password': ADMIN_PASSWORD})
    if metric['status'] != 200:
        raise RuntimeError(f'登录失败: status={metric["status"]}, error={metric["error"]}')
    # curl -s 不输出 body，需要再请求一次获取 token
    cmd = [
        'curl', '-s', '-X', 'POST',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps({'username': 'admin', 'password': ADMIN_PASSWORD}, ensure_ascii=False),
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    return data.get('data', {}).get('token') or data.get('token')


def main():
    print(f'API 测速开始: {BASE_URL}')
    print(f'时间: {datetime.now().isoformat()}')
    print(f'端点数量: {len(ENDPOINTS)}')
    print('正在登录获取 Token...')
    token = login()
    print('登录成功')
    print('-' * 80)

    results = []
    for idx, ep in enumerate(ENDPOINTS, 1):
        url = urljoin(BASE_URL, ep['path'])
        use_token = ep['path'] not in ('/', '/health')
        metric = curl_once(ep['method'], url, ep.get('body'), token=token if use_token else None)
        results.append({
            'seq': idx,
            'name': ep['name'],
            'method': ep['method'],
            'path': ep['path'],
            **metric,
        })
        total_str = f"{metric['total']:.3f}s" if metric['total'] is not None else 'N/A'
        status_str = str(metric['status']) if metric['status'] else 'ERR'
        print(f"[{idx:02d}/{len(ENDPOINTS):02d}] {ep['method']:6} {status_str:4} {total_str:>8} {ep['name']}")

    output_path = 'd:/seele/scripts/api_speed_test_result.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'base_url': BASE_URL,
            'tested_at': datetime.now().isoformat(),
            'total_endpoints': len(ENDPOINTS),
            'authenticated': True,
            'results': results,
        }, f, ensure_ascii=False, indent=2)

    print('-' * 80)
    print(f'结果已保存: {output_path}')


if __name__ == '__main__':
    main()
