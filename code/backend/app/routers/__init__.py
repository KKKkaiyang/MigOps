from app.routers import (
    b01_space,
    b02_material,
    b03_data_migration,
    b04_task_migration,
    b05_data_check,
)

all_routers = [
    b01_space.router,
    b02_material.router,
    b03_data_migration.router,
    b04_task_migration.router,
    b05_data_check.router,
]
