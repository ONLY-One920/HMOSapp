
def test_get_products_api(test_client, init_database):
    """测试获取商品API"""
    response = test_client.get('/api/products')

    assert response.status_code == 200
    assert isinstance(response.json, list)
    assert len(response.json) > 0
    assert 'name' in response.json[0]
    assert 'price' in response.json[0]


def test_create_product_api(authenticated_client):
    """测试创建商品API"""
    response = authenticated_client.post('/api/products', json={
        'id': 'test-product',
        'name': '测试商品',
        'price': 99.99,
        'image': 'test.jpg',
        'description': '测试商品描述'
    })

    assert response.status_code == 201
    assert 'product_id' in response.json


def test_update_product_api(authenticated_client,test_client):
    """测试更新商品API"""
    response = authenticated_client.put('/api/products/1', json={
        'name': '更新后的华为手机',
        'price': 2099.0,
        'description': '更新后的描述'
    })

    assert response.status_code == 200
    assert '更新成功' in response.json['message']

    # 验证更新结果
    response = test_client.get('/api/products')
    updated_product = next((p for p in response.json if p['id'] == '1'), None)
    assert updated_product is not None
    assert updated_product['name'] == '更新后的华为手机'
    assert updated_product['price'] == 2099.0


def test_delete_product_api(authenticated_client,test_client):
    """测试删除商品API"""
    response = authenticated_client.delete('/api/products/2')

    assert response.status_code == 200
    assert '已删除' in response.json['message']

    # 验证商品已删除
    response = test_client.get('/api/products')
    deleted_product = next((p for p in response.json if p['id'] == '2'), None)
    assert deleted_product is None


def test_search_products_api(test_client, init_database):
    """测试搜索商品API"""
    response = test_client.get('/api/products/search?q=华为')

    assert response.status_code == 200
    assert isinstance(response.json, list)
    assert len(response.json) > 0
    assert '华为' in response.json[0]['name']


def test_get_product_detail_api(test_client, init_database):
    """测试获取商品详情API"""
    response = test_client.get('/api/products/1/detail')

    assert response.status_code == 200
    assert response.json['id'] == '1'
    assert 'name' in response.json
    assert 'price' in response.json
    assert 'images' in response.json

def test_create_product_with_missing_fields(authenticated_client):
    """测试创建商品时缺少必要字段"""
    response = authenticated_client.post('/api/products', json={
        'name': '测试商品',
        'price': 99.99
        # 缺少id字段
    })
    assert response.status_code == 400

def test_update_nonexistent_product(authenticated_client):
    """测试更新不存在的商品"""
    response = authenticated_client.put('/api/products/999', json={
        'name': '不存在的商品',
        'price': 99.99
    })
    assert response.status_code == 404

def test_delete_nonexistent_product(authenticated_client):
    """测试删除不存在的商品"""
    response = authenticated_client.delete('/api/products/999')
    assert response.status_code == 404

def test_search_products_empty_result(test_client):
    """测试搜索无结果的情况"""
    response = test_client.get('/api/products/search?q=不存在的关键词')
    assert response.status_code == 200
    assert len(response.json) == 0