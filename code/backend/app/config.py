import os


class Settings:
    """全局配置，环境变量优先覆盖默认值。

    数据源切换：DB_TYPE=mysql 使用 MySQL；DB_TYPE=starrocks 使用 StarRocks。
    两者均通过 pymysql 驱动连接（StarRocks 兼容 MySQL 协议）。
    """

    APP_NAME = os.getenv("APP_NAME", "MigOps")
    API_V1_PREFIX = os.getenv("API_V1_PREFIX", "/api/v1")

    DB_TYPE = os.getenv("DB_TYPE", "mysql")  # mysql | starrocks
    # 注意：本机 /etc/hosts 缺失 127.0.0.1 localhost 回环映射时，
    # pymysql 解析 "localhost" 会报 [Errno 8] nodename nor servname，
    # 故默认使用 IP 127.0.0.1 直连，避免依赖 DNS 解析。
    MYSQL_URL = os.getenv(
        "MYSQL_URL",
        "mysql+pymysql://root:mysql@127.0.0.1:3306/mig_common_db?charset=utf8mb4",
    )
    STARROCKS_URL = os.getenv(
        "STARROCKS_URL",
        "mysql+pymysql://root:root@127.0.0.1:9030/mig_common_db?charset=utf8mb4",
    )

    DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))
    MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", "200"))

    # ── 认证与安全（公共业务需求 §3） ──
    JWT_SECRET = os.getenv(
        "JWT_SECRET", "migops-dev-secret-please-override-in-production"
    )
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))

    # 登录失败策略：达到阈值出现验证码；累计达上限锁定账号
    CAPTCHA_FAIL_THRESHOLD = int(os.getenv("CAPTCHA_FAIL_THRESHOLD", "3"))
    LOGIN_LOCK_THRESHOLD = int(os.getenv("LOGIN_LOCK_THRESHOLD", "10"))
    LOGIN_LOCK_MINUTES = int(os.getenv("LOGIN_LOCK_MINUTES", "30"))
    CAPTCHA_TTL_SECONDS = int(os.getenv("CAPTCHA_TTL_SECONDS", "300"))

    # markdown 资料查看密码策略（项目空间业务需求 D10 / D16）
    VIEW_TOKEN_EXPIRE_MINUTES = int(os.getenv("VIEW_TOKEN_EXPIRE_MINUTES", "30"))
    VIEW_PWD_MAX_FAILS = int(os.getenv("VIEW_PWD_MAX_FAILS", "5"))
    VIEW_PWD_LOCK_MINUTES = int(os.getenv("VIEW_PWD_LOCK_MINUTES", "10"))

    # 默认管理员（系统初始化种子账号）
    DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@1234")

    # 项目空间库名前缀：mig_<space_code>_db
    SPACE_DB_PREFIX = os.getenv("SPACE_DB_PREFIX", "mig_")

    PORT = int(os.getenv("PORT", "8999"))

    # ── skill 管理（b08，平台级全局） ──
    # skill zip 本地存储根目录（后续可切换对象存储，见 StorageBackend 抽象）
    _default_skill_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "skills"
    )
    SKILL_STORAGE_DIR = os.getenv("SKILL_STORAGE_DIR", _default_skill_dir)
    # 单文件上传上限（字节），默认 50MB
    SKILL_MAX_UPLOAD_BYTES = int(os.getenv("SKILL_MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
    # REST API ak/sk 签名：时间戳允许偏差（秒）与 nonce 防重放窗口（秒）
    API_SIGN_TIME_SKEW_SECONDS = int(os.getenv("API_SIGN_TIME_SKEW_SECONDS", "300"))
    API_SIGN_NONCE_TTL_SECONDS = int(os.getenv("API_SIGN_NONCE_TTL_SECONDS", "300"))
    # Fernet 密钥（用于加密存储 secret_key）；缺省由 JWT_SECRET 派生 32 字节 URL-safe 密钥
    API_KEY_FERNET_KEY = os.getenv("API_KEY_FERNET_KEY", "")


settings = Settings()
