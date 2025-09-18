# MallBackend 测试说明

本目录包含 MallBackend 项目的自动化测试代码和资源。

## 单元测试 (Unit Tests)

本项目使用 `pytest` 作为单元测试框架。

### 运行全部单元测试

在项目根目录下执行以下命令：

```bash
pip install -r requirements.txt  # 确保安装所有依赖
pip install pytest               # 确保安装了 pytest
python -m pytest tests/ -v
```

`-v` 参数用于显示详细的测试结果。

### 运行特定测试文件

```bash
python -m pytest tests/test_auth_utils.py -v
```

## API 集成测试 (API Integration Tests)

我们使用 Postman 和 Newman 进行 API 集成测试。

### 1. 安装 Newman

Newman 是 Postman 的命令行运行器。你需要先安装 Node.js，然后通过 npm 安装 Newman。

```bash
npm install -g newman
```

### 2. 运行 Postman 集合

在项目根目录下执行以下命令，运行导出的测试集合：

```bash
newman run tests/mall_backend_postman_collection.json
```

### 3. 生成测试报告

Newman 支持生成多种格式的测试报告（如 HTML），这对于持续集成非常有用。

```bash
# 安装 newman-reporter-html
npm install -g newman-reporter-html

# 运行集合并生成HTML报告
newman run tests/mall_backend_postman_collection.json -r html,cli
```
报告文件 `newman/` 会被生成在运行命令的目录下。

## 测试策略简要说明

-   **单元测试**：位于 `test_*.py` 文件中，用于测试工具函数、工具类等独立单元的正确性。
-   **API 集成测试**：通过 Postman Collection 定义，用于测试各个 API 端点的功能、数据返回和状态码是否符合预期。

## 注意事项

1.  运行 API 测试前，请确保后端服务正在运行（例如 `python run.py`）。
2.  部分 API 需要认证令牌，请确保 Postman 环境变量或 Collection 变量已正确配置。