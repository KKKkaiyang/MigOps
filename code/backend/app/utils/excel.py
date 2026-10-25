"""Excel/CSV 导入导出工具（b03/b04/b05 台账导入导出共用）。

- 读取：.xlsx 经 openpyxl，.xls 经 xlrd，.csv 经标准库 csv；返回 (表头, 行字典列表, 原始行号列表)；
- 生成：模板与导出均为 xlsx 字节流；
- 日期单元格兼容 datetime 对象与字符串两种形态。
"""

import csv
import io
from datetime import date, datetime
from typing import List, Optional, Tuple

from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAX_IMPORT_ROWS = 5000
ALLOWED_EXTENSIONS = (".xlsx", ".xls", ".csv")


def check_import_file(filename: Optional[str]) -> None:
    from app.core.exceptions import BizError

    name = (filename or "").lower()
    if not name.endswith(ALLOWED_EXTENSIONS):
        raise BizError("仅支持 .xls / .xlsx 或 .csv 文件")


def read_tabular(content: bytes, filename: str) -> Tuple[List[str], List[dict], List[int]]:
    """读取表格式文件，返回 (表头, 行数据, 行号)。行号从 2 起（第 1 行为表头）。"""
    name = (filename or "").lower()
    if name.endswith(".csv"):
        return _read_csv(content)
    if name.endswith(".xls"):
        return _read_xls(content)
    return _read_xlsx(content)


def _read_csv(content: bytes) -> Tuple[List[str], List[dict], List[int]]:
    text = content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader if any((c or "").strip() for c in r)]
    if not rows:
        return [], [], []
    headers = [(h or "").strip() for h in rows[0]]
    data, line_nos = [], []
    for idx, row in enumerate(rows[1:], start=2):
        item = {}
        for i, key in enumerate(headers):
            raw = row[i] if i < len(row) else ""
            item[key] = raw.strip() if isinstance(raw, str) else raw
        data.append(item)
        line_nos.append(idx)
    return headers, data, line_nos


def _read_xlsx(content: bytes) -> Tuple[List[str], List[dict], List[int]]:
    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    try:
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        header_row = next(rows_iter, None)
        if not header_row:
            return [], [], []
        headers = [str(h).strip() if h is not None else "" for h in header_row]
        data, line_nos = [], []
        for idx, row in enumerate(rows_iter, start=2):
            if not any(v is not None and str(v).strip() for v in row):
                continue
            item = {}
            for i, key in enumerate(headers):
                v = row[i] if i < len(row) else None
                item[key] = v.strip() if isinstance(v, str) else v
            data.append(item)
            line_nos.append(idx)
        return headers, data, line_nos
    finally:
        wb.close()


def _read_xls(content: bytes) -> Tuple[List[str], List[dict], List[int]]:
    """读取旧版 .xls（BIFF，经 xlrd）；xlrd 2.x 仅支持 .xls，与 openpyxl 分工。"""
    import xlrd

    book = xlrd.open_workbook(file_contents=content)
    sheet = book.sheet_by_index(0)
    if sheet.nrows < 1:
        return [], [], []
    headers = [
        str(sheet.cell_value(0, c)).strip() if sheet.ncols > c else "" for c in range(sheet.ncols)
    ]
    data, line_nos = [], []
    for r in range(1, sheet.nrows):
        row = [sheet.cell_value(r, c) for c in range(sheet.ncols)]
        if not any(str(v).strip() for v in row):
            continue
        item = {}
        for i, key in enumerate(headers):
            v = row[i] if i < len(row) else ""
            item[key] = v.strip() if isinstance(v, str) else v
        data.append(item)
        line_nos.append(r + 1)
    return headers, data, line_nos


def _to_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _to_date(value) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"无法解析日期: {text}")


def _to_datetime(value) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析时间: {text}")


def _to_int(value) -> Optional[int]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().replace(",", "")
    try:
        return int(float(text))
    except ValueError as exc:
        raise ValueError(f"无法解析数字: {value}") from exc


# 列定义：键名 -> (表头, 宽度, 转换器, 是否必填)
def make_xlsx(headers: List[str], rows: List[list], widths: Optional[List[int]] = None) -> bytes:
    """生成 xlsx 字节流。"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(headers)
    for row in rows:
        ws.append(row)
    for i, width in enumerate(widths or [], start=1):
        ws.column_dimensions[get_column_letter(i)].width = width
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


__all__ = [
    "XLSX_MEDIA_TYPE",
    "MAX_IMPORT_ROWS",
    "ALLOWED_EXTENSIONS",
    "check_import_file",
    "read_tabular",
    "make_xlsx",
    "_to_str",
    "_to_date",
    "_to_datetime",
    "_to_int",
]
