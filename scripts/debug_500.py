#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""使用 TestClient 复现 500 错误并打印堆栈"""

import sys
sys.path.insert(0, 'd:/seele/seele-backend')

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# 登录
res = client.post('/api/auth/login', json={'username': 'admin', 'password': 'seele'})
print('login', res.status_code, res.text[:200])
token = res.json().get('data', {}).get('token')
headers = {'Authorization': f'Bearer {token}'}

endpoints = [
    ('POST', '/api/stock/basic/page', {'page_num': 1, 'page_size': 10}),
    ('POST', '/api/stock/basic/000001/sync-survey', {}),
    ('POST', '/api/stock/basic/000001/sync-industry-detail', {}),
    ('GET', '/api/stock/daily/mainwave-detect/000001', None),
    ('POST', '/api/stock/daily/mainwave-detect/batch', {'symbols': ['000001', '000002']}),
    ('GET', '/api/financial?page_num=1&page_size=10', None),
    ('POST', '/api/agent/chat', {'message': '你好', 'session_id': 'test'}),
]

for method, path, body in endpoints:
    print(f'\n=== {method} {path} ===')
    try:
        if method == 'GET':
            r = client.get(path, headers=headers)
        else:
            r = client.post(path, json=body or {}, headers=headers)
        print('status:', r.status_code)
        print('body:', r.text[:500])
    except Exception as exc:
        print('exception:', exc)
        import traceback
        traceback.print_exc()
