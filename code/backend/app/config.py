import os


class Settings:
    """全局配置，环境变量优先覆盖默认值。

    数据源切换：DB_TYPE=mysql 使用 MySQL；DB_TYPE=starrocks 使用 StarRocks。
    两者均通过 pymysql 驱动连接（StarRocks 兼容 MySQL 协议）。
    """

    APP_NAME = os.getenv("APP_NAME", "MigOps")
    API_V1_PREFIX = os.getenv("API_V1_PREFIX", "/api/v1")

    DB_TYPE = os.getenv("DB_TYPE", "mysql")  # mysql | starrocks
    MYSQL_URL = os.getenv(
        "MYSQL_URL",
        "mysql+pymysql://root:root@localhost:3306/mig_common_db?charset=utf8mb4",
    )
    STARROCKS_URL = os.getenv(
        "STARROCKS_URL",
        "mysql+pymysql://root:root@localhost:9030/mig_common_db?charset=utf8mb4",
    )

    DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))
    MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", "200"))


settings = Settings()
