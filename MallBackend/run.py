import sys
import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from app import create_app, db
from app.utils import cleanup_expired_tokens, seed_initial_data, check_database_schema
import socket
from sqlalchemy import text

# 添加项目根目录到系统路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

app = create_app()

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 配置定时任务清理过期令牌
scheduler = BackgroundScheduler()
scheduler.add_job(cleanup_expired_tokens, 'interval', hours=1)
scheduler.start()

if __name__ == '__main__':
    # 确保数据库表存在
    with app.app_context():
        try:
            # 1. 先检查并修复数据库结构
            logger.info("正在检查数据库结构...")
            check_database_schema()

            # 2. 检查数据库连接是否正常
            logger.info("正在检查数据库连接...")
            db.session.execute(text("SELECT 1 FROM token_blacklist LIMIT 1"))

            # 3. 初始化数据
            logger.info("正在初始化数据...")
            seed_initial_data()
        except Exception as e:
            logger.error(f"数据库初始化失败: {str(e)}")
            try:
                # 尝试创建所有表
                logger.warning("尝试创建数据库表...")
                db.create_all()

                # 再次检查数据库结构
                logger.info("再次检查数据库结构...")
                check_database_schema()

                # 再次初始化数据
                logger.info("再次初始化数据...")
                seed_initial_data()
                logger.info("数据库表创建完成")
            except Exception as create_err:
                logger.error(f"创建数据库表失败: {str(create_err)}")

    # 获取本机 IP 地址
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)

    # 打印 API 文档地址和网络信息
    print("=" * 50)
    print(f"API 文档地址: http://localhost:5000/api/docs")
    print(f"本地网络地址: http://{ip_address}:5000")
    print("=" * 50)

    # 添加详细的路由调试信息
    print("Registered API Endpoints:")
    print("=" * 50)

    # 获取所有端点
    for rule in app.url_map.iter_rules():
        if rule.endpoint not in ('static', 'swagger_ui'):
            methods = ','.join(rule.methods)
            print(f'{methods:<10} {rule}')

    print("\n" + "=" * 50)
    print("Starting MallBackend server...")
    print("=" * 50)

    # 启用详细日志
    app.logger.setLevel(logging.DEBUG)

    app.run(host='0.0.0.0', port=5000, debug=True)