#!/usr/bin/env python3
"""
查询接口文档的统一脚本。完全自包含，不依赖外部 projects.json。
两种模式：
  默认模式       — 通过 api-doc-server 查询（有缓存）
  --direct 模式  — 直接连接上游 OpenAPI 文档源（无需 api-doc-server）

项目地址配置在本脚本同级目录的 projects.json 中。

用法:
    python query_api.py projects                          # 列出所有项目
    python query_api.py list <项目编号>                    # 列出接口列表
    python query_api.py refresh <项目编号>                  # 刷新缓存
    python query_api.py download <项目编号> --tag <模块>   # 下载指定模块接口为.md文件
    python query_api.py <项目编号> <功能名称>               # 查询接口详情
    python query_api.py <项目编号> <功能名称> --tag <模块>  # 指定模块
    python query_api.py --direct <项目编号> <功能名称>      # 直接查询（无缓存）
    python query_api.py --host <IP> <项目编号> <功能名称>   # 指定 api-doc-server IP

示例:
    python query_api.py P51 "批量下载二维码"
    python query_api.py --direct P51 "批量下载二维码"
    python query_api.py P51 "批量下载二维码" --tag "人员二维码发放管理"
    python query_api.py refresh P51
    python query_api.py --direct download P51 --tag "隐患管理"
    python query_api.py --direct download P51 --tag "会议信息管理" --output ./docs
"""

import sys
import os
import json
import socket
import urllib.request
import urllib.error
import re

# ============================================================
# 项目地址配置 — 自包含，不依赖外部 projects.json
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_FILE = os.path.join(SCRIPT_DIR, "projects.json")


def load_projects():
    """从 skill 自带的 projects.json 加载项目地址"""
    with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def print_projects_list():
    """打印项目列表"""
    try:
        projs = load_projects()
        print("项目列表:")
        for code in sorted(projs.keys()):
            urls = projs[code]
            print(f"  {code}: {len(urls)} 个接口地址")
            for u in urls:
                print(f"    - {u}")
    except Exception as e:
        print(f"❌ 加载项目配置失败: {e}")


# ============================================================
# api-doc-server 模式
# ============================================================

CANDIDATE_HOSTS = [
    "http://localhost:2338",
    "http://127.0.0.1:2338",
]


def detect_ip_hosts():
    """尝试获取本机局域网 IP 作为备选地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("10.80.188.53", 1))
        local_ip = s.getsockname()[0]
        s.close()
        if local_ip:
            CANDIDATE_HOSTS.append(f"http://{local_ip}:2338")
    except Exception:
        pass
    seen = set()
    deduped = []
    for h in CANDIDATE_HOSTS:
        if h not in seen:
            seen.add(h)
            deduped.append(h)
    return deduped


def find_api_base():
    """依次尝试候选地址，返回第一个可用的 base URL"""
    hosts = detect_ip_hosts()
    for base in hosts:
        try:
            req = urllib.request.Request(f"{base}/api/projects")
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") == 200:
                    return base
        except Exception:
            continue
    return CANDIDATE_HOSTS[0]


def api_get(path, base_url):
    url = f"{base_url}{path}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"code": e.code, "msg": body, "raw": True}
    except Exception as e:
        return {"code": 0, "msg": f"连接失败: {e}"}


def api_post(path, base_url):
    url = f"{base_url}{path}"
    try:
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"code": e.code, "msg": body, "raw": True}
    except Exception as e:
        return {"code": 0, "msg": f"连接失败: {e}"}


def cmd_proxy_projects(base_url):
    data = api_get("/api/projects", base_url)
    if data.get("code") == 200:
        projs = data.get("data", {})
        print("项目列表 (api-doc-server):")
        for code, info in sorted(projs.items()):
            print(f"  {code}: {info['api_count']} 个接口地址")
    else:
        print(f"获取失败: {data.get('msg', data)}")


def cmd_proxy_list(project_code, base_url):
    data = api_get(f"/api/list/{project_code}?format=json", base_url)
    if data.get("code") == 200:
        tag_map = data.get("data", {}).get("tag_map", {})
        if not tag_map:
            print(f"项目 {project_code} 无缓存，请先执行 refresh")
            return
        print(f"\n项目 {project_code} 接口列表:\n")
        for tag in sorted(tag_map.keys()):
            apis = tag_map[tag]
            print(f"【{tag}】({len(apis)}个接口)")
            for a in apis:
                print(f"  - {a}")
            print()
    elif data.get("code") == 404:
        print(f"项目 {project_code} 无本地缓存，请先执行 refresh")
    else:
        print(f"查询失败: {data.get('msg', data)}")


def cmd_proxy_refresh(project_code, base_url):
    print(f"正在刷新项目 {project_code} 的接口列表...")
    data = api_post(f"/api/refresh/{project_code}", base_url)
    if data.get("code") == 200:
        tag_map = data.get("data", {}).get("tag_map", {})
        total = len(tag_map)
        api_total = sum(len(v) for v in tag_map.values())
        print(f"✅ 刷新成功 — {total} 个功能模块, {api_total} 个接口")
        for tag, apis in sorted(tag_map.items()):
            print(f"  {tag}: {len(apis)}个接口")
    else:
        print(f"❌ 刷新失败: {data.get('msg', data)}")


def cmd_proxy_query(project_code, api_summary, base_url, tag_filter=None):
    encoded = urllib.request.quote(api_summary)
    path = f"/api/query/{project_code}/{encoded}"
    if tag_filter:
        path += f"?tag={urllib.request.quote(tag_filter)}"

    data = api_get(path, base_url)
    code = data.get("code")

    if code == 200:
        print_query_result(data)
    elif code == 300:
        d = data.get("data", {})
        tags = d.get("tags", [])
        print(f"⚠️  功能 '{api_summary}' 在多个模块下都有 ({len(tags)}个):")
        for t in tags:
            print(f"    - {t}")
        print(f"\n  请使用 --tag <模块名> 指定查询哪个模块。")
        print(f"  示例: python query_api.py {project_code} \"{api_summary}\" --tag \"{tags[0]}\"")
    elif code == 404:
        print(f"❌ 未找到接口: {api_summary}")
        print(f"  可能原因:")
        print('    1. 功能名称不对 — 用具体功能名，如"批量下载二维码"')
        print(f"    2. 缓存过期 — 试试先执行 refresh: python query_api.py refresh {project_code}")
        print(f"    3. 项目编号不对 — 检查项目是否存在: python query_api.py projects")
    else:
        print(f"❌ 查询异常: {data.get('msg', data)}")


# ============================================================
# --direct 模式：直接连接上游 OpenAPI 文档，不依赖 api-doc-server
# ============================================================


def fetch_upstream_doc(url):
    """获取上游 OpenAPI JSON 文档"""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return None


def direct_get_tags(urls):
    """直接从上获取接口标签列表"""
    all_tags = {}
    for url in urls:
        doc = fetch_upstream_doc(url)
        if not doc:
            continue
        paths = doc.get("paths", {})
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.lower() not in ("get", "post", "put", "delete", "patch"):
                    continue
                for tag in details.get("tags", []):
                    if tag not in all_tags:
                        all_tags[tag] = []
                    key = f"{method.upper()} {path}"
                    summary = details.get("summary", "") or details.get("description", "")
                    if summary and key not in {f"{a['method']} {a['path']}" for a in all_tags[tag]}:
                        all_tags[tag].append({"method": method.upper(), "path": path, "summary": summary})
    return all_tags


def direct_search(urls, keyword):
    """直接从上游搜索接口"""
    results = []
    for url in urls:
        doc = fetch_upstream_doc(url)
        if not doc:
            continue
        paths = doc.get("paths", {})
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.lower() not in ("get", "post", "put", "delete", "patch"):
                    continue
                summary = details.get("summary", "") or details.get("description", "")
                if keyword.lower() in summary.lower():
                    results.append({
                        "method": method.upper(),
                        "path": path,
                        "summary": summary,
                        "description": details.get("description", ""),
                        "tag": details.get("tags", [""])[0] if details.get("tags") else "",
                        "tags": details.get("tags", []),
                        "parameters": details.get("parameters", []),
                        "requestBody": details.get("requestBody", {}),
                        "responses": details.get("responses", {}),
                        "source": url
                    })
    return results


def print_query_result(data):
    """打印查询结果"""
    d = data.get("data", {})
    api = d.get("api", {})
    print(f"✅ 查询成功")
    print(f"   模块: {d.get('tag', '')}")
    print(f"   方法: {api.get('method', '')}")
    print(f"   路径: {api.get('path', '')}")
    print(f"   描述: {api.get('description', '')}")

    params = api.get("parameters", [])
    if params:
        print(f"\n   请求参数 ({len(params)}个):")
        for p in params:
            required = "必填" if p.get("required") else "可选"
            print(f"     [{required}] {p.get('name', '')} ({p.get('in', '')}) — {p.get('description', '')}")

    request_body = api.get("requestBody", {})
    if request_body:
        content = request_body.get("content", {})
        if "application/json" in content:
            schema = content["application/json"].get("schema", {})
            print(f"\n   请求体:")
            if "properties" in schema:
                for name, info in schema["properties"].items():
                    t = info.get("type", "")
                    desc = info.get("description", "")
                    print(f"     {name}: {t} — {desc}")

    responses = api.get("responses", {})
    if responses:
        for status, resp_detail in responses.items():
            print(f"\n   响应 {status}: {resp_detail.get('description', '')}")
            content = resp_detail.get("content", {})
            if "*/*" in content:
                schema = content["*/*"].get("schema", {})
                if "properties" in schema:
                    for name, info in schema["properties"].items():
                        t = info.get("type", "")
                        desc = info.get("description", "")
                        print(f"     {name}: {t} — {desc}")

    if d.get("schemas"):
        print(f"\n   完整 schemas: {len(d['schemas'])} 个定义")
    if d.get("file"):
        print(f"   缓存文件: {d['file']}")


def print_direct_result(results, keyword):
    """打印直接查询结果"""
    if not results:
        print(f"❌ 未找到接口: {keyword}")
        return
    # 按 tag 分组
    by_tag = {}
    for r in results:
        tag = r.get("tag", "未分类")
        if tag not in by_tag:
            by_tag[tag] = []
        by_tag[tag].append(r)
    print(f"✅ 找到 {len(results)} 个匹配接口 (直接查询):\n")
    for tag, apis in sorted(by_tag.items()):
        print(f"【{tag}】")
        for a in apis:
            print(f"  {a['method']} {a['path']}")
            print(f"   └ {a['summary']}")
        print()


def cmd_direct_projects():
    """直接模式：显示项目列表"""
    print_projects_list()


def cmd_direct_list(project_code):
    """直接模式：列出所有接口"""
    projs = load_projects()
    if project_code not in projs:
        print(f"❌ 项目 {project_code} 不存在")
        return
    urls = projs[project_code]
    if not isinstance(urls, list):
        urls = [urls]

    tags = direct_get_tags(urls)
    if not tags:
        print(f"❌ 无法连接上游 API（项目 {project_code} 的接口地址不可达）")
        return
    print(f"\n项目 {project_code} 接口列表 (直接查询):\n")
    for tag in sorted(tags.keys()):
        apis = tags[tag]
        print(f"【{tag}】({len(apis)}个接口)")
        for a in apis:
            print(f"  {a['method']} {a['path']}")
            print(f"   └ {a['summary']}")
        print()


def cmd_direct_query(project_code, api_summary, tag_filter=None):
    """直接模式：搜索接口"""
    projs = load_projects()
    if project_code not in projs:
        print(f"❌ 项目 {project_code} 不存在")
        return
    urls = projs[project_code]
    if not isinstance(urls, list):
        urls = [urls]

    results = direct_search(urls, api_summary)
    if not results:
        print(f"❌ 未找到接口: {api_summary}（上游 API 不可达或无匹配）")
        return

    # 过滤 tag
    if tag_filter:
        results = [r for r in results if r.get("tag") == tag_filter]
        if not results:
            print(f"❌ 在模块 [{tag_filter}] 下未找到: {api_summary}")
            return

    # 如果有多个不同 tag，提示选择
    unique_tags = list(set(r.get("tag", "") for r in results))
    if len(unique_tags) > 1 and not tag_filter:
        print(f"⚠️  功能 '{api_summary}' 在多个模块下都有 ({len(unique_tags)}个):")
        for t in unique_tags:
            count = sum(1 for r in results if r.get("tag") == t)
            print(f"    - {t} ({count}个)")
        print(f"\n  请使用 --tag <模块名> 指定查询哪个模块。")
        return

    # 取第一个匹配项展示详细内容
    r = results[0]
    print(f"✅ 查询成功 (直接模式)")
    tag = r.get("tag", "")
    if tag:
        print(f"   模块: {tag}")
    print(f"   方法: {r['method']}")
    print(f"   路径: {r['path']}")
    print(f"   描述: {r.get('description', '')}")
    print(f"   来源: {r.get('source', '')}")

    params = r.get("parameters", [])
    if params:
        print(f"\n   请求参数 ({len(params)}个):")
        for p in params:
            required = "必填" if p.get("required") else "可选"
            print(f"     [{required}] {p.get('name', '')} ({p.get('in', '')}) — {p.get('description', '')}")

    request_body = r.get("requestBody", {})
    if request_body:
        content = request_body.get("content", {})
        if "application/json" in content:
            schema = content["application/json"].get("schema", {})
            print(f"\n   请求体: 有定义")
            if "properties" in schema:
                for name, info in schema["properties"].items():
                    t = info.get("type", "")
                    desc = info.get("description", "")
                    print(f"     {name}: {t} — {desc}")

    responses = r.get("responses", {})
    if responses:
        for status, resp_detail in responses.items():
            print(f"\n   响应 {status}: {resp_detail.get('description', '')}")
            content = resp_detail.get("content", {})
            if "*/*" in content:
                schema = content["*/*"].get("schema", {})
                if "properties" in schema:
                    for name, info in schema["properties"].items():
                        t = info.get("type", "")
                        desc = info.get("description", "")
                        print(f"     {name}: {t} — {desc}")


# ============================================================
# 下载模式：将指定模块的接口导出为 .md 文件
# 包含完整的 $ref 递归解析（请求参数、请求体、响应嵌套结构）
# ============================================================


def sanitize_filename(name):
    """过滤 Windows 文件名中的非法字符 \\ / : * ? \" < > |"""
    if not name:
        return "unnamed"
    return re.sub(r'[\\/:*?"<>|]', '_', name).strip()


def _lookup_ref(ref_str, schemas):
    """解析 \$ref 字符串 #/components/schemas/Xxx 或 #/definitions/Xxx，返回 schema 定义"""
    if not ref_str:
        return None
    ref_name = ref_str.split("/")[-1]
    return schemas.get(ref_name)


def _gen_schema_fields_table(schema, schemas, cols=3, required_list=None):
    """
    递归生成 schema 字段的 Markdown 表格行，完整展开 \$ref 嵌套。
    cols=3 → 响应表 (字段|类型|描述)
    cols=4 → 请求体表 (字段|类型|必填|描述)
    cols=5 → 请求参数表 (字段|类型|必填|描述)，嵌套行占位位置列
    返回 (lines, has_rows)
    """
    lines = []
    has_rows = False

    ref = schema.get("$ref", "")
    if ref:
        resolved = _lookup_ref(ref, schemas)
        if not resolved:
            return lines, False
        return _gen_schema_fields_table(resolved, schemas, cols, required_list)

    props = schema.get("properties", {})
    req_list = schema.get("required", []) if required_list is None else required_list
    if not props:
        return lines, False

    for pname, pinfo in sorted(props.items()):
        ptype = pinfo.get("type", "")
        pdesc = pinfo.get("description", "")
        is_req = "是" if pname in req_list else "否"

        if cols == 5:
            # 请求参数表：| 字段 | 位置(空) | 类型 | 必填 | 描述 |
            lines.append(f"| {pname} |  | {ptype} | {is_req} | {pdesc} |\n")
        elif cols == 4:
            lines.append(f"| {pname} | {ptype} | {is_req} | {pdesc} |\n")
        else:
            lines.append(f"| {pname} | {ptype} | {pdesc} |\n")
        has_rows = True

        def _write_nested(fields, req_fields, indent_prefix):
            """写入嵌套字段"""
            nonlocal has_rows
            for npname, npinfo in sorted(fields.items()):
                nt = npinfo.get("type", "")
                ndesc = npinfo.get("description", "")
                nr = "是" if npname in req_fields else "否"
                entry = f"{indent_prefix}└ {npname}"
                if cols == 5:
                    lines.append(f"| {entry} |  | {nt} | {nr} | {ndesc} |\n")
                elif cols == 4:
                    lines.append(f"| {entry} | {nt} | {nr} | {ndesc} |\n")
                else:
                    lines.append(f"| {entry} | {nt} | {ndesc} |\n")
                has_rows = True

        # items.$ref (数组元素)
        items_ref = pinfo.get("items", {}).get("$ref", "")
        if items_ref:
            nested = _lookup_ref(items_ref, schemas)
            if nested:
                _write_nested(nested.get("properties", {}), nested.get("required", []), "  ")

        # additionalProperties.$ref (Map)
        addl_ref = pinfo.get("additionalProperties", {}).get("$ref", "")
        if addl_ref:
            nested = _lookup_ref(addl_ref, schemas)
            if nested:
                _write_nested(nested.get("properties", {}), nested.get("required", []), "  ")

        # 直接 $ref (非数组对象字段)
        p_ref = pinfo.get("$ref", "")
        if p_ref and not items_ref:
            nested = _lookup_ref(p_ref, schemas)
            if nested:
                _write_nested(nested.get("properties", {}), nested.get("required", []), "  ")

    return lines, has_rows


def cmd_direct_download(project_code, tag_filter, output_dir=None):
    """直接模式：下载指定模块的所有接口为 .md 文件（包含完整的 \$ref 递归解析）"""
    projs = load_projects()
    if project_code not in projs:
        print(f"❌ 项目 {project_code} 不存在")
        return

    urls = projs[project_code]
    if not isinstance(urls, list):
        urls = [urls]

    if not output_dir:
        output_dir = os.getcwd()
    else:
        output_dir = os.path.abspath(output_dir)
        os.makedirs(output_dir, exist_ok=True)

    # 遍历所有上游地址，收集匹配的接口
    all_results = []
    for url in urls:
        doc = fetch_upstream_doc(url)
        if not doc:
            continue
        schemas = doc.get("components", {}).get("schemas", {})
        paths = doc.get("paths", {})
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.lower() not in ("get", "post", "put", "delete", "patch"):
                    continue
                tags = details.get("tags", [])
                if tag_filter not in tags:
                    continue
                all_results.append({
                    "method": method.upper(),
                    "path": path,
                    "summary": details.get("summary", ""),
                    "description": details.get("description", ""),
                    "parameters": details.get("parameters", []),
                    "requestBody": details.get("requestBody", {}),
                    "responses": details.get("responses", {}),
                    "schemas": schemas,
                    "source": url
                })

    if not all_results:
        print(f"❌ 模块 [{tag_filter}] 下未找到任何接口")
        return

    # 创建标签文件夹
    folder_name = sanitize_filename(tag_filter)
    target_dir = os.path.join(output_dir, folder_name)
    os.makedirs(target_dir, exist_ok=True)

    print(f"\n正在下载模块 [{tag_filter}] 的 {len(all_results)} 个接口到 {target_dir} ...\n")

    for r in all_results:
        summary = r.get("summary", "").strip()
        if not summary:
            summary = f"{r['method']}_{r['path'].replace('/', '_')}"
        filename = sanitize_filename(summary) + ".md"
        filepath = os.path.join(target_dir, filename)

        schemas = r.get("schemas", {})
        lines = []
        lines.append(f"# {summary}\n\n")
        lines.append(f"**方法**: `{r['method']}`\n")
        lines.append(f"**路径**: `{r['path']}`\n")
        if r.get("description"):
            lines.append(f"**描述**: {r['description']}\n")

        # ======== 请求参数 ========
        params = r.get("parameters", [])
        if params:
            lines.append("\n## 请求参数\n\n")
            lines.append("| 名称 | 位置 | 类型 | 必填 | 描述 |\n")
            lines.append("|------|------|------|------|------|\n")
            for p in params:
                required = "是" if p.get("required") else "否"
                p_name = p.get("name", "")
                p_in = p.get("in", "")
                p_schema = p.get("schema", {})
                p_type = p_schema.get("type", "")
                p_desc = p.get("description", "")
                # 如果 schema 是 $ref，用 ref 名称作为类型
                p_ref_type = p_schema.get("$ref", "")
                if p_ref_type:
                    p_type = p_ref_type.split("/")[-1]
                lines.append(f"| {p_name} | {p_in} | {p_type} | {required} | {p_desc} |\n")

                # 如果 schema 有 \$ref，展开嵌套字段
                p_ref = p_schema.get("$ref", "")
                if p_ref:
                    resolved = _lookup_ref(p_ref, schemas)
                    if resolved:
                        sub_lines, _ = _gen_schema_fields_table(
                            resolved, schemas, cols=5
                        )
                        lines.extend(sub_lines)

        # ======== 请求体 ========
        req_body = r.get("requestBody", {})
        if req_body:
            content = req_body.get("content", {})
            if "application/json" in content:
                schema = content["application/json"].get("schema", {})
                ref = schema.get("$ref", "")
                lines.append("\n## 请求体\n\n")
                if ref:
                    ref_name = ref.split("/")[-1]
                    lines.append(f"**类型**: `{ref_name}`\n\n")
                # 完整展开请求体字段
                lines.append("| 字段 | 类型 | 必填 | 描述 |\n")
                lines.append("|------|------|------|------|\n")
                sub_lines, _ = _gen_schema_fields_table(
                    schema, schemas, cols=4
                )
                if sub_lines:
                    lines.extend(sub_lines)
                else:
                    # 没有嵌套属性时，至少显示顶层
                    props = schema.get("properties", {})
                    req_list = schema.get("required", [])
                    for pname, pinfo in sorted(props.items()):
                        t = pinfo.get("type", "")
                        pdesc = pinfo.get("description", "")
                        is_req = "是" if pname in req_list else "否"
                        lines.append(f"| {pname} | {t} | {is_req} | {pdesc} |\n")

        # ======== 响应 ========
        responses = r.get("responses", {})
        if responses:
            lines.append("\n## 响应\n\n")
            for status, resp_detail in responses.items():
                resp_desc = resp_detail.get("description", "")
                lines.append(f"**{status}**: {resp_desc}\n\n")
                content = resp_detail.get("content", {})
                if "*/*" in content:
                    schema = content["*/*"].get("schema", {})
                    ref = schema.get("$ref", "")
                    if ref:
                        ref_name = ref.split("/")[-1]
                        lines.append(f"数据结构: `{ref_name}`\n\n")
                    # 完整展开响应字段
                    lines.append("| 字段 | 类型 | 描述 |\n")
                    lines.append("|------|------|------|\n")
                    sub_lines, _ = _gen_schema_fields_table(
                        schema, schemas, cols=3
                    )
                    if sub_lines:
                        lines.extend(sub_lines)
                    else:
                        # 兜底：直接显示顶层 properties
                        props = schema.get("properties", {})
                        for pname, pinfo in sorted(props.items()):
                            t = pinfo.get("type", "")
                            pdesc = pinfo.get("description", "")
                            lines.append(f"| {pname} | {t} | {pdesc} |\n")

        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)

        print(f"  ✓ {filename}")

    print(f"\n✅ 下载完成: {len(all_results)} 个接口 -> {target_dir}")


# ============================================================
# 主入口
# ============================================================

def main():
    args = list(sys.argv[1:])

    # 解析全局参数
    base_url = None
    direct_mode = False

    if "--host" in args:
        idx = args.index("--host")
        if idx + 1 < len(args):
            host_ip = args[idx + 1]
            if not host_ip.startswith("http"):
                base_url = f"http://{host_ip}:2338"
            else:
                base_url = host_ip
            args = args[:idx] + args[idx+2:]

    if "--direct" in args:
        direct_mode = True
        args.remove("--direct")

    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0]

    # --- projects 命令 ---
    if cmd == "projects":
        if direct_mode:
            cmd_direct_projects()
        else:
            if not base_url:
                base_url = find_api_base()
            cmd_proxy_projects(base_url)
        return

    # --- list/refresh 命令：python query_api.py (list|refresh) <项目编号> ---
    if cmd in ("list", "refresh"):
        if len(args) < 2:
            print(f"用法: python query_api.py {cmd} <项目编号>")
            sys.exit(1)
        project_code = args[1]
        if cmd == "list":
            if direct_mode:
                cmd_direct_list(project_code)
            else:
                if not base_url:
                    base_url = find_api_base()
                cmd_proxy_list(project_code, base_url)
        else:
            if direct_mode:
                print("⚠️  refresh 仅支持 api-doc-server 模式（--direct 模式下无缓存）")
            else:
                if not base_url:
                    base_url = find_api_base()
                cmd_proxy_refresh(project_code, base_url)
        return

    # --- download 命令：python query_api.py [--direct] download <项目编号> --tag <模块> [--output <路径>] ---
    if cmd == "download":
        if len(args) < 2:
            print(f"用法: python query_api.py [--direct] download <项目编号> --tag <模块名> [--output <保存路径>]")
            sys.exit(1)
        project_code = args[1]
        tag_filter = None
        output_dir = None

        if "--tag" in args:
            idx = args.index("--tag")
            if idx + 1 < len(args):
                tag_filter = args[idx + 1]
        if "--output" in args:
            idx = args.index("--output")
            if idx + 1 < len(args):
                output_dir = args[idx + 1]

        if not tag_filter:
            print("❌ download 需要指定 --tag <模块名>")
            sys.exit(1)

        if direct_mode:
            cmd_direct_download(project_code, tag_filter, output_dir)
        else:
            print("⚠️  download 仅支持 --direct 模式")
        return

    # --- 查询模式：python query_api.py <项目编号> <功能名称> [--tag <模块>] ---
    if len(args) < 2:
        print(f"用法: python query_api.py [--direct] [--host <IP>] <命令> <项目编号> [<功能名称>] [--tag <模块>]")
        sys.exit(1)

    project_code = args[0]
    api_summary = args[1]
    tag_filter = None
    if "--tag" in args:
        idx = args.index("--tag")
        if idx + 1 < len(args):
            tag_filter = args[idx + 1]

    if direct_mode:
        cmd_direct_query(project_code, api_summary, tag_filter)
    else:
        if not base_url:
            base_url = find_api_base()
        cmd_proxy_query(project_code, api_summary, base_url, tag_filter)


if __name__ == "__main__":
    main()
