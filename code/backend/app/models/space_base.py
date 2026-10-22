from sqlalchemy.orm import DeclarativeBase


class SpaceBase(DeclarativeBase):
    """空间库（mig_<space_code>_db）业务表基类。

    与公共库 Base（app.models.base，映射 mig_common_db）使用相互独立的
    metadata，确保 create_all 只把各自模型建到目标库：
    - Base      → mig_common_db（common_* / b01_space 等公共表）
    - SpaceBase → mig_<space_code>_db（b02~b04 空间业务表）
    """
