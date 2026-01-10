"""
数据库迁移脚本：移除负载均衡相关功能

执行此脚本将：
1. 删除 sessions 表
2. 删除 provider_rr_state 表
3. 从 providers 表移除 weight 列
4. 从 cli_settings 表移除 routing_mode 列

使用方法：
    cd backend
    python -m app.migrations.remove_load_balance
"""

import sqlite3
import os
from pathlib import Path


def migrate():
    # 数据库路径
    db_path = Path(__file__).resolve().parent.parent.parent / "data" / "ccg_gateway.db"

    if not db_path.exists():
        print(f"数据库文件不存在: {db_path}")
        print("如果是首次运行，无需迁移")
        return

    print(f"正在迁移数据库: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. 删除 sessions 表
        print("删除 sessions 表...")
        cursor.execute("DROP TABLE IF EXISTS sessions")

        # 2. 删除 provider_rr_state 表
        print("删除 provider_rr_state 表...")
        cursor.execute("DROP TABLE IF EXISTS provider_rr_state")

        # 3. 从 providers 表移除 weight 列
        print("从 providers 表移除 weight 列...")
        cursor.execute("PRAGMA table_info(providers)")
        columns = cursor.fetchall()
        has_weight = any(col[1] == 'weight' for col in columns)

        if has_weight:
            # 获取除 weight 外的所有列
            cols_to_keep = [col[1] for col in columns if col[1] != 'weight']
            cols_str = ', '.join(cols_to_keep)

            cursor.execute(f"""
                CREATE TABLE providers_new AS
                SELECT {cols_str} FROM providers
            """)
            cursor.execute("DROP TABLE providers")
            cursor.execute("ALTER TABLE providers_new RENAME TO providers")

            # 重建索引和约束
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_cli_provider_name
                ON providers(cli_type, name)
            """)

        # 4. 从 cli_settings 表移除 routing_mode 列
        print("从 cli_settings 表移除 routing_mode 列...")
        cursor.execute("PRAGMA table_info(cli_settings)")
        columns = cursor.fetchall()
        has_routing_mode = any(col[1] == 'routing_mode' for col in columns)

        if has_routing_mode:
            cols_to_keep = [col[1] for col in columns if col[1] != 'routing_mode']
            cols_str = ', '.join(cols_to_keep)

            cursor.execute(f"""
                CREATE TABLE cli_settings_new AS
                SELECT {cols_str} FROM cli_settings
            """)
            cursor.execute("DROP TABLE cli_settings")
            cursor.execute("ALTER TABLE cli_settings_new RENAME TO cli_settings")

        conn.commit()
        print("迁移完成!")

    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
