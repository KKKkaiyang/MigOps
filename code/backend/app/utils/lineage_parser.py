# -*- coding: utf-8 -*-
"""数据血缘解析器（移植自 tools/hrwx_lineage/server/lineage_parser.py）。

支持两类脚本：
- PySpark：解析 spark.sql(...) / 临时视图 / saveAsTable / insertInto 等
- 纯 SQL：直接解析 .sql 脚本中的 INSERT / CREATE / MERGE 与 FROM / JOIN / USING

解析规则：
- 提取 spark.sql(...) 中的 SQL 字符串（支持 f-string / 三引号）
- 解析 python 变量赋值、常量折叠、f-string 替换
- 识别临时视图（createOrReplaceTempView / CREATE TEMPORARY VIEW）
- 识别 df.write.saveAsTable / insertInto 输出
- 解析 SQL 中的 FROM/JOIN/USING 来源表与 INSERT/CREATE/MERGE 目标表

输出粒度（最细）：一条「输入表 -> 输出表」的血缘边，返回 dict 列表：
    [{"source":..,"target":..,"sourceType":..,"targetType":..}, ...]
"""

import re

TABLE_TOKEN = (
    r"`[^`]+`(?:\.[\w.]+)*|\"[^\"]+\"(?:\.[\w.]+)*|'[^']+'(?:\.[\w.]+)*|[\w.]+"
)
BLACKLIST_SRC = {"unnest", "values", "lateral", "table"}


def norm_table(t):
    t = t.strip()
    # 反引号在 Spark SQL 中仅作标识符引号
    t = t.replace("`", "")
    if len(t) >= 2 and t[0] == t[-1] and t[0] in ("\"", "'"):
        t = t[1:-1]
    return t.strip()


# ---------------------------------------------------------------------------
# 1. 提取 spark.sql(...) 中的 SQL 字符串（支持 f-string / 三引号）
# ---------------------------------------------------------------------------
def extract_string_literal(text, start):
    i = start
    n = len(text)
    while i < n and text[i] in " \t\n\r":
        i += 1
    if i >= n:
        return None, start, False
    prefix = ""
    while i < n and text[i] in "frubFRUB":
        prefix += text[i]
        i += 1
    is_f = "f" in prefix.lower()
    if i + 2 < n and text[i:i + 3] in ('"""', "'''"):
        q = text[i:i + 3]
        i += 3
        end = text.find(q, i)
        if end == -1:
            return None, start, False
        return text[i:end], end + 3, is_f
    if i < n and text[i] in ('"', "'"):
        q = text[i]
        i += 1
        j = i
        while j < n:
            if text[j] == "\\":
                j += 2
                continue
            if text[j] == q:
                return text[i:j], j + 1, is_f
            j += 1
        return None, start, False
    return None, start, False


def find_sql_calls(text):
    calls = []
    pat = re.compile(r'(?:([A-Za-z_]\w*)\s*=\s*)?(?:(?:spark|session|spark_session)\s*\.)?sql\s*\(')
    for m in pat.finditer(text):
        var = m.group(1)
        content, end, is_f = extract_string_literal(text, m.end())
        if content is not None:
            calls.append({"var": var, "sql": content, "is_f": is_f})
    return calls


# ---------------------------------------------------------------------------
# 2. 收集 python 变量赋值并尽力做常量折叠（解析表名变量）
# ---------------------------------------------------------------------------
def collect_vars(text):
    vars = {}
    for m in re.finditer(r'^\s*([A-Za-z_]\w*)\s*=\s*(.*?)\s*$', text, re.MULTILINE):
        name = m.group(1)
        rhs = m.group(2).strip()
        vars[name] = {"raw": rhs, "value": None, "resolved": False}
    return vars


def expand_fstr(s, vars):
    did = False

    def repl(mm):
        nonlocal did
        expr = mm.group(0)[1:-1].strip()
        idm = re.match(r"[A-Za-z_]\w*", expr)
        if idm:
            vn = idm.group(0)
            v = vars.get(vn)
            if v and v.get("resolved") and isinstance(v.get("value"), str) and "{" not in v["value"]:
                did = True
                return v["value"]
        return mm.group(0)

    return re.sub(r"\{[^{}]*\}", repl, s), did


def resolve_vars(vars):
    for name, info in vars.items():
        rhs = info["raw"]
        m = re.match(r'^f?(["\'])(.*)\1$', rhs)
        if m:
            info["value"] = m.group(2)
            info["is_fstr"] = rhs[:1] in ("f", "F")
            info["resolved"] = True
        else:
            m2 = re.match(r"^([A-Za-z_]\w*)$", rhs)
            if m2 and m2.group(1) in vars:
                info["alias_of"] = m2.group(1)
    changed = True
    while changed:
        changed = False
        for name, info in vars.items():
            if info.get("resolved") and info.get("is_fstr") and "{" in info["value"]:
                newval, did = expand_fstr(info["value"], vars)
                if did:
                    info["value"] = newval
                    changed = True
    for name, info in vars.items():
        if "alias_of" in info:
            a = vars.get(info["alias_of"])
            if a and a.get("resolved"):
                info["value"] = a["value"]
                info["resolved"] = True
    return vars


def substitute_sql(sql, vars):
    def repl(mm):
        expr = mm.group(0)[1:-1].strip()
        idm = re.match(r"[A-Za-z_]\w*", expr)
        if idm:
            vn = idm.group(0)
            v = vars.get(vn)
            if v and v.get("resolved") and isinstance(v.get("value"), str):
                return v["value"]
        return mm.group(0)

    return re.sub(r"\{[^{}]*\}", repl, sql)


# ---------------------------------------------------------------------------
# 3. 临时视图 & 其他输出/输入
# ---------------------------------------------------------------------------
def find_temp_views(text, vars):
    temp_views = {}
    names = set()
    for m in re.finditer(
        r'(?:([A-Za-z_]\w*)\s*\.\s*)?createOrReplaceTempView\s*\(\s*([^)]*)\)', text, re.IGNORECASE
    ):
        dfvar = m.group(1)
        arg = m.group(2).strip()
        qm = re.match(r'^["\']([^"\']+)["\']$', arg)
        if qm:
            name = qm.group(1)
        else:
            vn = arg.strip()
            name = vars.get(vn, {}).get("value") if vn in vars else None
            if name is None:
                name = arg
        names.add(name)
        if dfvar:
            temp_views[dfvar] = name
    for m in re.finditer(
        r'CREATE\s+(?:OR\s+REPLACE\s+)?TEMPORARY\s+VIEW\s+(' + TABLE_TOKEN + r')', text, re.IGNORECASE
    ):
        names.add(norm_table(m.group(1)))
    return temp_views, names


def resolve_arg(arg, vars):
    qm = re.match(r'^["\']([^"\']+)["\']$', arg)
    if qm:
        return qm.group(1)
    vn = arg.strip()
    if vn in vars and vars[vn].get("resolved"):
        return vars[vn]["value"]
    return arg


def find_df_outputs(text, vars):
    out = []
    for m in re.finditer(
        r'([A-Za-z_]\w*)\s*\.\s*write\b.*?\.saveAsTable\s*\(\s*([^)]*)\)', text, re.IGNORECASE | re.DOTALL
    ):
        out.append((m.group(1), resolve_arg(m.group(2).strip(), vars)))
    for m in re.finditer(
        r'([A-Za-z_]\w*)\s*\.\s*insertInto\s*\(\s*([^)]*)\)', text, re.IGNORECASE
    ):
        out.append((m.group(1), resolve_arg(m.group(2).strip(), vars)))
    return out


def find_spark_table_inputs(text):
    return [
        norm_table(m.group(1))
        for m in re.finditer(r'spark\.table\s*\(\s*["\']([^"\']+)["\']\s*\)', text, re.IGNORECASE)
    ]


# ---------------------------------------------------------------------------
# 4. SQL 内部的表解析
# ---------------------------------------------------------------------------
def split_statements(sql):
    """按分号切分语句，但忽略字符串字面量（单/双/反引号）内部的分号。"""
    out = []
    cur = []
    quote = None
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        if quote:
            cur.append(ch)
            if ch == quote:
                if i + 1 < n and sql[i + 1] == quote:
                    cur.append(sql[i + 1])
                    i += 2
                    continue
                quote = None
            i += 1
            continue
        if ch in ("'", '"', '`'):
            quote = ch
            cur.append(ch)
            i += 1
            continue
        if ch == ";":
            s = "".join(cur).strip()
            if s:
                out.append(s)
            cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    s = "".join(cur).strip()
    if s:
        out.append(s)
    return out


def strip_string_literals(sql):
    """去掉 SQL 中的单/双引号字符串字面量（保留反引号标识符）。"""
    s = re.sub(r"'(?:[^']|'')*'", " ", sql)
    s = re.sub(r'"(?:[^"]|"")*"', " ", sql)
    return s


def find_ctes(stmt):
    return {m.group(1) for m in re.finditer(r'(?:WITH|,)\s*([A-Za-z_]\w*)\s+AS\s*\(', stmt, re.IGNORECASE)}


def extend_table(stmt, m, grp=1):
    name = norm_table(m.group(grp))
    j = m.end(grp)
    if j < len(stmt) and stmt[j] == "{":
        end = stmt.find("}", j)
        if end != -1:
            name = name + stmt[j:end + 1]
    return name


def find_targets(stmt):
    targets = []
    pats = [
        (r'INSERT\s+INTO\s+(?:TABLE\s+)?(' + TABLE_TOKEN + r')', "正式表"),
        (r'INSERT\s+OVERWRITE\s+(?:TABLE\s+)?(' + TABLE_TOKEN + r')', "正式表"),
        (r'CREATE\s+OR\s+REPLACE\s+TEMPORARY\s+VIEW\s+(' + TABLE_TOKEN + r')', "临时表"),
        (r'CREATE\s+TEMPORARY\s+VIEW\s+(' + TABLE_TOKEN + r')', "临时表"),
        (r'CREATE\s+OR\s+REPLACE\s+VIEW\s+(' + TABLE_TOKEN + r')', "正式表"),
        (r'CREATE\s+(?:OR\s+REPLACE\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(' + TABLE_TOKEN + r')', "正式表"),
        (r'MERGE\s+INTO\s+(' + TABLE_TOKEN + r')', "正式表"),
    ]
    for pat, ttype in pats:
        for m in re.finditer(pat, stmt, re.IGNORECASE):
            targets.append((extend_table(stmt, m, 1), ttype))
    return targets


def find_sources(stmt, ctes):
    exclude = set()
    for m in re.finditer(r'DELETE\s+FROM\s+(' + TABLE_TOKEN + r')', stmt, re.IGNORECASE):
        exclude.add(extend_table(stmt, m, 1))
    for m in re.finditer(r'UPDATE\s+(' + TABLE_TOKEN + r')\s+SET', stmt, re.IGNORECASE):
        exclude.add(extend_table(stmt, m, 1))
    srcs = []
    pat = r'\b(?:FROM|(?:\w+\s+)?JOIN|USING)\b\s+(' + TABLE_TOKEN + r')'
    for m in re.finditer(pat, stmt, re.IGNORECASE):
        t = extend_table(stmt, m, 1)
        low = t.lower()
        if low in BLACKLIST_SRC or t in ctes or t in exclude:
            continue
        srcs.append(t)
    return srcs


# ---------------------------------------------------------------------------
# 5. PySpark 解析
# ---------------------------------------------------------------------------
def _parse_pyspark(text):
    vars = collect_vars(text)
    resolve_vars(vars)
    sql_calls = find_sql_calls(text)
    temp_views_map, temp_names = find_temp_views(text, vars)
    df_outputs = find_df_outputs(text, vars)
    spark_table_inputs = find_spark_table_inputs(text)

    df_sources = {}
    edges = []

    def add_edge(src, tgt, tgt_type):
        if not src or not tgt:
            return
        in_type = "临时表" if src in temp_names else "正式表"
        edges.append((src, tgt, in_type, tgt_type))

    for call in sql_calls:
        sql = call["sql"]
        if call["is_f"]:
            sql = substitute_sql(sql, vars)
        var = call["var"]
        srcs_all = []
        for stmt in split_statements(sql):
            stmt = strip_string_literals(stmt)
            ctes = find_ctes(stmt)
            targets = find_targets(stmt)
            srcs = find_sources(stmt, ctes)
            srcs_all.extend(srcs)
            for (tgt, ttype) in targets:
                for s in srcs:
                    add_edge(s, tgt, ttype)
        if var:
            df_sources.setdefault(var, set()).update(srcs_all)

    for dfvar, tmpname in temp_views_map.items():
        for s in df_sources.get(dfvar, set()):
            add_edge(s, tmpname, "临时表")

    for dfvar, outname in df_outputs:
        for s in df_sources.get(dfvar, set()):
            add_edge(s, outname, "正式表")

    for s in spark_table_inputs:
        if not any(e[0] == s for e in edges):
            in_type = "临时表" if s in temp_names else "正式表"
            edges.append((s, "", in_type, ""))

    seen, result = set(), []
    for e in edges:
        key = (e[0], e[1], e[2], e[3])
        if key in seen:
            continue
        seen.add(key)
        result.append(e)

    return [
        {"source": src, "target": tgt, "sourceType": in_type, "targetType": out_type}
        for (src, tgt, in_type, out_type) in result
    ]


# ---------------------------------------------------------------------------
# 6. 纯 SQL 解析
# ---------------------------------------------------------------------------
def _parse_sql(text):
    edges = []
    seen = set()
    temp_views = set()

    for stmt in split_statements(text):
        s = strip_string_literals(stmt)
        for m in re.finditer(
            r'CREATE\s+(?:OR\s+REPLACE\s+)?TEMPORARY\s+VIEW\s+(' + TABLE_TOKEN + r')',
            s, re.IGNORECASE,
        ):
            temp_views.add(norm_table(m.group(1)))

    def add_edge(src, tgt, tgt_type):
        if not src or not tgt:
            return
        in_type = "临时表" if src in temp_views else "正式表"
        key = (src, tgt, in_type, tgt_type)
        if key in seen:
            return
        seen.add(key)
        edges.append({"source": src, "target": tgt, "sourceType": in_type, "targetType": tgt_type})

    for stmt in split_statements(text):
        stmt = strip_string_literals(stmt)
        ctes = find_ctes(stmt)
        targets = find_targets(stmt)
        srcs = find_sources(stmt, ctes)
        for (tgt, ttype) in targets:
            for s in srcs:
                add_edge(s, tgt, ttype)
    return edges


# ---------------------------------------------------------------------------
# 7. 主解析（按语言分发，支持自动识别）
# ---------------------------------------------------------------------------
def _detect_lang(text):
    """启发式判断脚本语言：含有 PySpark 特征则按 pyspark 解析，否则按纯 SQL。"""
    markers = [
        r'\bspark\s*\.\s*(sql|read|table)\b',
        r'\bcreateOrReplaceTempView\b',
        r'\b\.saveAsTable\s*\(',
        r'\binsertInto\s*\(',
        r'\bfrom\s+pyspark\b',
        r'\bimport\s+pyspark\b',
    ]
    for pat in markers:
        if re.search(pat, text, re.IGNORECASE):
            return "pyspark"
    return "sql"


def parse_text(text, lang=None):
    if not text or not text.strip():
        return []
    if isinstance(lang, str) and lang.strip().lower() in ("pyspark", "sql"):
        lang = lang.strip().lower()
    else:
        lang = _detect_lang(text)
    if lang == "sql":
        return _parse_sql(text)
    return _parse_pyspark(text)


def parse_file(path):
    with open(path, encoding="utf-8", errors="ignore") as f:
        text = f.read()
    return parse_text(text)
