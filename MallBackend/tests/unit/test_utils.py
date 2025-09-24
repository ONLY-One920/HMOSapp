from app.utils import validate_credentials, check_database_schema
from unittest.mock import patch, MagicMock


def test_validate_credentials():
    """测试验证凭据函数"""
    # 测试有效凭据
    is_valid, message = validate_credentials("123456", "password123")
    assert is_valid is True
    assert message == ""

    # 测试无效用户名
    is_valid, message = validate_credentials("123", "password123")
    assert is_valid is False
    assert "6位数字" in message

    # 测试密码过长
    is_valid, message = validate_credentials("123456", "a" * 21)
    assert is_valid is False
    assert "1-20个字符" in message


@patch("app.utils.inspect")
@patch("app.utils.text")
def test_check_database_schema(mock_text, mock_inspect, test_app):
    """测试数据库结构检查"""
    with test_app.app_context():
        # 模拟数据库检查器
        mock_inspector = MagicMock()
        mock_inspect.return_value = mock_inspector

        # 模拟表结构
        mock_inspector.get_table_names.return_value = ["cart_items", "products"]
        mock_inspector.get_columns.return_value = [{"name": "id"}, {"name": "user_id"}]

        # 模拟数据库会话
        mock_db = MagicMock()

        # 使用patch模拟current_app
        with patch("app.utils.current_app") as mock_app:
            mock_app.extensions = {"sqlalchemy": mock_db}

            # 调用函数
            result = check_database_schema()

            # 验证结果
            assert result is True

            # 验证ALTER TABLE语句被执行
            assert mock_db.session.execute.called


@patch("app.utils.inspect")
@patch("app.utils.text")
def test_check_database_schema_with_missing_tables(mock_text, mock_inspect, test_app):
    """测试数据库结构检查时表不存在的情况"""
    with test_app.app_context():
        # 模拟检查器
        mock_inspector = MagicMock()
        mock_inspect.return_value = mock_inspector

        # 模拟没有表
        mock_inspector.get_table_names.return_value = []

        # 模拟数据库会话
        mock_db = MagicMock()

        with patch("app.utils.current_app") as mock_app:
            mock_app.extensions = {"sqlalchemy": mock_db}

            # 调用函数
            result = check_database_schema()

            # 验证没有执行ALTER TABLE
            assert not mock_db.session.execute.called
            assert result is False


def test_validate_credentials_edge_cases():
    """测试验证凭据的边界情况"""
    # 空用户名
    is_valid, message = validate_credentials("", "password")
    assert is_valid is False

    # 空密码
    is_valid, message = validate_credentials("123456", "")
    assert is_valid is False

    # 用户名包含非数字字符
    is_valid, message = validate_credentials("123abc", "password")
    assert is_valid is False
