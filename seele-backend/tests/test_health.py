def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    data = response.json()
    assert data['code'] == 200
    assert data['data'] == 'OK'


def test_root(client):
    response = client.get('/')
    assert response.status_code == 200
    data = response.json()
    assert data['code'] == 200
