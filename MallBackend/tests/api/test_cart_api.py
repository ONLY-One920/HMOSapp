
def test_get_cart_api(authenticated_client, init_database):
    """测试获取购物车API"""
    response = authenticated_client.get('/api/cart')

    assert response.status_code == 200
    assert isinstance(response.json, list)


def test_add_to_cart_api(authenticated_client, init_database):
    """测试添加到购物车API"""
    response = authenticated_client.post('/api/cart', json={
        'product_id': '1'
    })

    assert response.status_code == 201
    assert '已添加到购物车' in response.json['message']
    assert 'cart' in response.json

    # 验证购物车中有商品
    assert len(response.json['cart']) > 0
    assert response.json['cart'][0]['product']['id'] == '1'


def test_update_cart_quantity_api(authenticated_client, init_database):
    """测试更新购物车数量API"""
    # 先添加商品到购物车
    authenticated_client.post('/api/cart', json={'product_id': '1'})

    # 获取购物车项ID
    cart_response = authenticated_client.get('/api/cart')
    item_id = cart_response.json[0]['id']

    # 更新数量
    response = authenticated_client.put('/api/cart', json={
        'item_id': item_id,
        'quantity': 3
    })

    assert response.status_code == 200
    assert '购物车已更新' in response.json['message']

    # 验证数量已更新
    assert response.json['cart'][0]['quantity'] == 3


def test_remove_from_cart_api(authenticated_client, init_database):
    """测试从购物车移除API"""
    # 先添加商品到购物车
    authenticated_client.post('/api/cart', json={'product_id': '1'})

    # 获取购物车项ID
    cart_response = authenticated_client.get('/api/cart')
    item_id = cart_response.json[0]['id']

    # 移除商品
    response = authenticated_client.delete(f'/api/cart/{item_id}')

    assert response.status_code == 200
    assert '已从购物车移除' in response.json['message']

    # 验证购物车为空
    assert len(response.json['cart']) == 0


def test_add_nonexistent_product_to_cart(authenticated_client):
    """测试添加不存在的商品到购物车"""
    response = authenticated_client.post('/api/cart', json={
        'product_id': '999'
    })
    assert response.status_code == 404


def test_update_cart_item_with_invalid_quantity(authenticated_client, init_database):
    """测试更新购物车数量为无效值"""
    # 先添加商品到购物车
    authenticated_client.post('/api/cart', json={'product_id': '1'})

    # 获取购物车项ID
    cart_response = authenticated_client.get('/api/cart')
    item_id = cart_response.json[0]['id']

    # 更新数量为0（应该触发删除）
    response = authenticated_client.put('/api/cart', json={
        'item_id': item_id,
        'quantity': 0
    })
    assert response.status_code == 200
    # 验证购物车为空
    assert len(response.json['cart']) == 0


def test_remove_nonexistent_cart_item(authenticated_client):
    """测试删除不存在的购物车项"""
    response = authenticated_client.delete('/api/cart/999')
    assert response.status_code == 404