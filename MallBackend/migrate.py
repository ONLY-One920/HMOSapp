import sys
import os
import shutil
from sqlalchemy import text, inspect
from sqlalchemy.exc import OperationalError

# 将项目根目录添加到 Python 路径
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from app import create_app, db
from app.utils import seed_initial_data
from flask_migrate import Migrate, upgrade, init, migrate as _migrate

app = create_app()
migrate = Migrate(app, db)

# 迁移目录路径
migrations_dir = os.path.join(project_root, 'migrations')


def fix_missing_columns():
    """修复缺失的数据表列"""
    try:
        inspector = inspect(db.engine)
        required_columns = {
            'cart_items': ['updated_at'],
        }

        for table, columns in required_columns.items():
            if table in inspector.get_table_names():
                existing_columns = [col['name'] for col in inspector.get_columns(table)]
                for col in columns:
                    if col not in existing_columns:
                        print(f"添加缺失字段 {col} 到表 {table}")
                        try:
                            db.session.execute(text(
                                f"ALTER TABLE {table} "
                                f"ADD COLUMN {col} DATETIME DEFAULT CURRENT_TIMESTAMP "
                                "ON UPDATE CURRENT_TIMESTAMP"
                            ))
                            print(f"成功添加字段 {col}")
                        except Exception as alter_err:
                            print(f"添加字段失败: {str(alter_err)}")
                            # 尝试更简单的添加方式
                            try:
                                db.session.execute(text(
                                    f"ALTER TABLE {table} "
                                    f"ADD COLUMN {col} DATETIME"
                                ))
                                print(f"成功添加字段 {col} (无默认值)")
                            except Exception as simple_err:
                                print(f"简单添加字段失败: {str(simple_err)}")

        db.session.commit()
        return True
    except Exception as e:
        print(f"修复数据库结构失败: {str(e)}")
        db.session.rollback()
        return False


if __name__ == '__main__':
    with app.app_context():
        print("重置迁移环境...")

        # 如果存在迁移目录，则删除
        if os.path.exists(migrations_dir):
            shutil.rmtree(migrations_dir)
        print("已删除旧的迁移目录")

        # 重新初始化迁移仓库
        init(directory=migrations_dir)
        print("迁移仓库已重新初始化")

        # 生成迁移脚本
        print("生成迁移脚本...")
        _migrate(directory=migrations_dir, message='Initial migration')
        print("已生成迁移脚本")

        # 修复迁移脚本中的字段长度问题
        version_dir = os.path.join(migrations_dir, 'versions')
        for file in os.listdir(version_dir):
            if file.endswith('.py') and 'initial_migration' in file:
                file_path = os.path.join(version_dir, file)
                with open(file_path, 'r+', encoding='utf-8') as f:
                    content = f.read()
                    content = content.replace("type_=sa.String(length=6)",
                                              "type_=sa.String(length=50)")
                    f.seek(0)
                    f.write(content)
                    f.truncate()
                print(f"已修复 {file} 中的字段长度")

        # 应用迁移
        print("应用迁移...")
        try:
            upgrade(directory=migrations_dir)
            print("数据库迁移完成")
        except OperationalError as e:
            print(f"迁移失败: {str(e)}")
            print("尝试修复数据库结构...")
            if fix_missing_columns():
                print("数据库结构修复成功，重新应用迁移...")
                try:
                    upgrade(directory=migrations_dir)
                    print("数据库迁移完成")
                except Exception as retry_err:
                    print(f"重新迁移失败: {str(retry_err)}")
            else:
                print("无法修复数据库结构，请手动检查")
        except Exception as e:
            print(f"迁移失败: {str(e)}")

        # 添加初始数据
        seed_initial_data()
        print("数据库初始化完成")