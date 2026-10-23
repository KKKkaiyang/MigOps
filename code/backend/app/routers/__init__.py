from app.routers import (
    b01_space,
    b02_material,
    b03_data_migration,
    b04_task_migration,
    b05_data_check,
    b06_tag,
    b07_lineage,
    common_auth,
    common_user,
)

all_routers = [
    common_auth.router,
    common_user.router,
    b01_space.router,
    b02_material.router,
    b03_data_migration.router,
    b04_task_migration.router,
    b05_data_check.router,
    b06_tag.router,
    b07_lineage.router,
]
