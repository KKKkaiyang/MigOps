#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将参考库 data_lineage_hr.lineage 全量导入到指定迁移空间的 b07_lineage 表。

用途：开发/演示阶段快速灌入真实血缘数据，便于在「血缘管理」页面查看效果。

前置：
- 参考库 data_lineage_hr 可达（默认 127.0.0.1:3306 / root:mysql，可通过环境变量覆盖）；
- 目标空间已在平台创建（按 space_code 定位其空间库 mig_<space_code>_db）。

用法：
    python tools/import_lineage_hr.py --space-code <空间简称>
    # 自定义源库
    SRC_HOST=127.0.0.1 SRC_PASSWORD=xxx python tools/import_lineage_hr.py -s my_space

字段映射（参考 data_lineage_hr.lineage → b07_lineage）：
    workflow_name/task_name/task_type/project_name/script_name
    input_table/input_table_type/output_table/output_table_type
"""
import argparse
import os
import sys
from datetime import datetime

# 将 code/backend 加入路径以复用项目内的 DB 工具与模型
ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "..", "code", "backend")
sys.path.insert(0, os.path.abspath(BACKEND))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.database import SessionLocal, get_space_engine, space_db_name  # noqa: E402
from app.models.b07_lineage import B07Lineage  # noqa: E402
from app.models.space import MigSpace  # noqa: E402


def src_engine():
    host = os.environ.get("SRC_HOST", "127.0.0.1")
    port = int(os.environ.get("SRC_PORT", "3306"))
    user = os.environ.get("SRC_USER", "root")
    pwd = os.environ.get("SRC_PASSWORD", "mysql")
    db = os.environ.get("SRC_DB", "data_lineage_hr")
    url = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}?charset=utf8mb4"
    return create_engine(url, pool_pre_ping=True)


def resolve_space(space_code: str):
    """从公共库解析空间的 id 与库名。"""
    db = SessionLocal()
    try:
        space = db.query(MigSpace).filter(MigSpace.space_code == space_code).first()
        if not space:
            raise SystemExit(f"未找到空间: {space_code}（请先在平台创建该空间）")
        return space.id, space_db_name(space_code)
    finally:
        db.close()


def main():
    ap = argparse.ArgumentParser(description="导入 data_lineage_hr.lineage 到指定空间")
    ap.add_argument("-s", "--space-code", required=True, help="目标迁移空间简称(space_code)")
    ap.add_argument("--clear", action="store_true", help="导入前先清空该空间 b07_lineage")
    args = ap.parse_args()

    space_id, db_name = resolve_space(args.space_code)
    print(f"[info] 目标空间: code={args.space_code} id={space_id} db={db_name}")

    seng = src_engine()
    sdb = get_space_engine(db_name)

    # 1) 读取源数据
    cols = [
        "workflow_name", "task_name", "task_type", "project_name", "script_name",
        "input_table", "input_table_type", "output_table", "output_table_type",
    ]
    with seng.connect() as conn:
        rows = conn.execute(
            text(f"SELECT {', '.join(cols)} FROM lineage")
        ).mappings().all()
    print(f"[info] 源库 lineage 记录数: {len(rows)}")

    if args.clear:
        with sdb.begin() as conn:
            conn.execute(text("DELETE FROM b07_lineage WHERE space_id = :sid"), {"sid": space_id})
        print("[info] 已清空目标空间 b07_lineage")

    # 2) 写入目标空间库
    now = datetime.now()
    added = 0
    skipped = 0
    with Session(sdb) as session:
        for r in rows:
            src = r["input_table"]
            tgt = r["output_table"]
            if not src or not tgt:
                skipped += 1
                continue
            session.add(
                B07Lineage(
                    space_id=space_id,
                    workflow_name=r["workflow_name"],
                    task_name=r["task_name"],
                    task_type=r["task_type"],
                    project_name=r["project_name"],
                    script_name=r["script_name"],
                    input_table=src,
                    input_table_type=r["input_table_type"],
                    output_table=tgt,
                    output_table_type=r["output_table_type"],
                    created_by="import_lineage_hr",
                    created_at=now,
                    updated_by="import_lineage_hr",
                    updated_at=now,
                )
            )
            added += 1
        session.commit()

    print(f"[done] 已导入 {added} 条血缘边（跳过空表名 {skipped} 条）到 {db_name}.b07_lineage")


if __name__ == "__main__":
    main()
