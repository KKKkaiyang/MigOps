#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 TDM 数据校验结果 CSV 转换为 Excel（纯标准库，无需 pandas/openpyxl）。

输出字段：
    表名    -> 库名.表名 (srcDatabase.srcTable)
    源端    -> 源端数据条数 (srcResult)
    目标端  -> 目标端数据条数 (dstResult)
    校验结果 -> 通过 / 不通过 (checkResult == True 为通过)

用法：
    python3 convert_check_result.py <输入CSV> [输出Excel]
"""

import argparse
import csv
import os
import zipfile
from xml.sax.saxutils import escape


def read_rows(input_csv):
    """读取 CSV，返回 (表名, 源端, 目标端, 校验结果) 列表。"""
    rows = []
    with open(input_csv, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            db = (r.get("srcDatabase") or "").strip()
            tbl = (r.get("srcTable") or "").strip()
            src = (r.get("srcResult") or "").strip()
            dst = (r.get("dstResult") or "").strip()
            check = (r.get("checkResult") or "").strip().lower()
            result = "通过" if check == "true" else "不通过"
            rows.append((db + "." + tbl, src, dst, result))
    return rows


def _col_letter(idx):
    """0-based 列索引转 Excel 列字母：0->A, 1->B ..."""
    s = ""
    idx += 1
    while idx:
        idx, rem = divmod(idx - 1, 26)
        s = chr(65 + rem) + s
    return s


def _cell_xml(col, row_idx, value):
    ref = "%s%d" % (_col_letter(col), row_idx)
    if value == "" or value is None:
        return '<c r="%s"/>' % ref
    # 尝试按数字处理
    try:
        f = float(value)
        if f.is_integer():
            return '<c r="%s"><v>%d</v></c>' % (ref, int(f))
        return '<c r="%s"><v>%s</v></c>' % (ref, f)
    except (ValueError, TypeError):
        return '<c r="%s" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (
            ref,
            escape(str(value)),
        )


def write_xlsx(output_xlsx, headers, rows):
    """用标准库 zipfile 生成最小可用的 .xlsx。"""
    ncols = len(headers)

    sheet_rows = []
    # 表头
    sheet_rows.append(
        "<row r=\"1\">"
        + "".join(_cell_xml(c, 1, headers[c]) for c in range(ncols))
        + "</row>"
    )
    # 数据
    for i, row in enumerate(rows, start=2):
        sheet_rows.append(
            '<row r="%d">' % i
            + "".join(_cell_xml(c, i, row[c]) for c in range(ncols))
            + "</row>"
        )
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>" + "".join(sheet_rows) + "</sheetData></worksheet>"
    )

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )

    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )

    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="校验结果" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )

    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )

    with zipfile.ZipFile(output_xlsx, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def main():
    parser = argparse.ArgumentParser(description="将 TDM 数据校验结果 CSV 转换为 Excel")
    parser.add_argument("input", help="输入 CSV 文件路径")
    parser.add_argument(
        "output",
        nargs="?",
        default=None,
        help="输出 Excel 文件路径（默认：输入文件同目录同名 .xlsx）",
    )
    args = parser.parse_args()

    input_csv = args.input
    output_xlsx = args.output or os.path.splitext(input_csv)[0] + ".xlsx"

    headers = ["表名", "源端", "目标端", "校验结果"]
    rows = read_rows(input_csv)

    pass_count = sum(1 for r in rows if r[3] == "通过")
    write_xlsx(output_xlsx, headers, rows)

    print("已生成: %s" % output_xlsx)
    print("总行数: %d  通过: %d  不通过: %d" % (len(rows), pass_count, len(rows) - pass_count))


if __name__ == "__main__":
    main()
