#!/usr/bin/env python3
"""
P50 后端 API 直接调用脚本。不依赖 P50 MCP Server，直接调用远程 API。
适用于其他电脑使用 skill 时无需配置 MCP。

用法:
    python p50_api.py accounts list [--page 1] [--size 10] [--keyword <关键词>]
    python p50_api.py accounts create <工号> <姓名>
    python p50_api.py reports list [--employee <工号>] [--start <日期>] [--end <日期>]
    python p50_api.py reports create <工号> <开始日期> <结束日期> <内容>
    python p50_api.py reports update <id> <开始日期> <结束日期> <内容>
    python p50_api.py reports delete <id>
    python p50_api.py projects list [--page 1] [--size 10]
    python p50_api.py projects create <编码> <名称> [描述]
    python p50_api.py projects update <id> <名称> [描述]
    python p50_api.py projects delete <id>
    python p50_api.py requirements list [--project <编码>] [--submitter <工号>] [--executor <工号>] [--status <状态>]
    python p50_api.py requirements create <项目编码> <提交人工号> [--name <名称>] [--desc <描述>] [--executors <工号1,工号2>]
    python p50_api.py requirements update <id> [--name <名称>] [--desc <描述>] [--status <状态>] [--executors <工号1,工号2>]
    python p50_api.py requirements delete <id>

示例:
    python p50_api.py projects list
    python p50_api.py requirements list --submitter h2339
    python p50_api.py requirements create P51 h2339 --name "新需求"
"""

import sys
import json
import urllib.request
import urllib.error

# P50 后端 API 地址（远程服务器，不依赖本地服务）
# 查看 P50 MCP Server 的 .env 文件确认端口
BASE_URL = "http://10.88.109.205"


def api_get(path, params=None):
    url = f"{BASE_URL}{path}"
    if params:
        qs = "&".join(f"{k}={urllib.request.quote(str(v))}" for k, v in params.items() if v is not None)
        url = f"{url}?{qs}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"code": e.code, "msg": body}
    except Exception as e:
        return {"code": 0, "msg": f"连接失败: {e}"}


def api_post(path, data):
    url = f"{BASE_URL}{path}"
    try:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"code": e.code, "msg": body}
    except Exception as e:
        return {"code": 0, "msg": f"连接失败: {e}"}


def api_put(path, data):
    url = f"{BASE_URL}{path}"
    try:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="PUT")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"code": e.code, "msg": body}
    except Exception as e:
        return {"code": 0, "msg": f"连接失败: {e}"}


def api_delete(path):
    url = f"{BASE_URL}{path}"
    try:
        req = urllib.request.Request(url, method="DELETE")
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            try:
                return json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return {"code": 200, "msg": "删除成功"}
    except urllib.error.HTTPError as e:
        return {"code": e.code, "msg": "删除失败"}
    except Exception as e:
        return {"code": 0, "msg": f"连接失败: {e}"}


def extract_list(resp):
    """从 API 响应中提取列表数据，兼容不同返回格式"""
    data = resp.get("data", resp)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # 兼容 data.list / data.rows / data.data
        for key in ("list", "rows", "data", "records", "items"):
            if key in data and isinstance(data[key], list):
                return data[key]
    return []


def extract_total(resp):
    """从 API 响应中提取总数，优先使用 API 返回的 total，如果为 0 则用列表长度"""
    data = resp.get("data", resp)
    if isinstance(data, dict):
        api_total = data.get("total") or data.get("totalCount") or data.get("count")
        return api_total or 0
    return 0


# ============================================================
# Account
# ============================================================

def cmd_accounts(args):
    if not args or args[0] == "list":
        params = {}
        if "--page" in args:
            params["pageNum"] = args[args.index("--page") + 1]
        if "--size" in args:
            params["pageSize"] = args[args.index("--size") + 1]
        if "--keyword" in args:
            params["keyword"] = args[args.index("--keyword") + 1]
        data = api_get("/api/accounts", params)
        rows = extract_list(data)
        print(f"账号列表 (共 {len(rows)} 条):")
        for r in rows:
            print(f"  [{r.get('employeeId', '')}] {r.get('name', '')}")
    elif args[0] == "create" and len(args) >= 3:
        data = api_post("/api/accounts", {"employeeId": args[1], "name": args[2]})
        status = "成功" if data.get("code") in (200, None) else "失败"
        print(f"创建账号 {status}: {json.dumps(data, ensure_ascii=False, indent=2)}")
    else:
        print("用法: python p50_api.py accounts list|create <工号> <姓名>")


# ============================================================
# Weekly Report
# ============================================================

def cmd_reports(args):
    if not args or args[0] == "list":
        params = {}
        if "--employee" in args:
            params["employeeId"] = args[args.index("--employee") + 1]
        if "--start" in args:
            params["queryStartDate"] = args[args.index("--start") + 1]
        if "--end" in args:
            params["queryEndDate"] = args[args.index("--end") + 1]
        if "--page" in args:
            params["pageNum"] = args[args.index("--page") + 1]
        if "--size" in args:
            params["pageSize"] = args[args.index("--size") + 1]
        data = api_get("/api/weekly-report", params)
        rows = extract_list(data)
        print(f"周报列表 (共 {len(rows)} 条):")
        for r in rows:
            start = r.get("reportStartDate", "")
            end = r.get("reportEndDate", "")
            content = r.get("content", "").replace("\n", " | ")[:80]
            print(f"  [id={r.get('id', '?')}] {start} ~ {end}")
            print(f"    └ {content}")
    elif args[0] == "create" and len(args) >= 5:
        data = api_post("/api/weekly-report", {
            "employeeId": args[1],
            "reportStartDate": args[2],
            "reportEndDate": args[3],
            "content": args[4]
        })
        print(f"创建周报: {json.dumps(data, ensure_ascii=False, indent=2)}")
    elif args[0] == "update" and len(args) >= 5:
        data = api_put(f"/api/weekly-report/{args[1]}", {
            "reportStartDate": args[2],
            "reportEndDate": args[3],
            "content": args[4]
        })
        print(f"更新周报: {json.dumps(data, ensure_ascii=False, indent=2)}")
    elif args[0] == "delete" and len(args) >= 2:
        data = api_delete(f"/api/weekly-report/{args[1]}")
        print(f"删除周报: {json.dumps(data, ensure_ascii=False, indent=2)}")
    else:
        print("用法: python p50_api.py reports list|create|update|delete ...")


# ============================================================
# Project
# ============================================================

def cmd_projects(args):
    if not args or args[0] == "list":
        params = {}
        if "--page" in args:
            params["pageNum"] = args[args.index("--page") + 1]
        if "--size" in args:
            params["pageSize"] = args[args.index("--size") + 1]
        if "--keyword" in args:
            params["keyword"] = args[args.index("--keyword") + 1]
        data = api_get("/api/projects", params)
        rows = extract_list(data)
        print(f"项目列表 (共 {len(rows)} 条):")
        for r in rows:
            code = r.get("projectCode", "")
            name = r.get("projectName", "")
            desc = r.get("description", "")
            print(f"  {code} — {name}   [{desc[:500] if desc else ''}]")
    elif args[0] == "create" and len(args) >= 3:
        payload = {"projectCode": args[1], "projectName": args[2]}
        if len(args) >= 4:
            payload["description"] = args[3]
        data = api_post("/api/projects", payload)
        print(f"创建项目: {json.dumps(data, ensure_ascii=False, indent=2)}")
    elif args[0] == "update" and len(args) >= 3:
        payload = {"projectName": args[2]}
        if len(args) >= 4:
            payload["description"] = args[3]
        data = api_put(f"/api/projects/{args[1]}", payload)
        print(f"编辑项目: {json.dumps(data, ensure_ascii=False, indent=2)}")
    elif args[0] == "delete" and len(args) >= 2:
        data = api_delete(f"/api/projects/{args[1]}")
        print(f"删除项目: {json.dumps(data, ensure_ascii=False, indent=2)}")
    else:
        print("用法: python p50_api.py projects list|create|update|delete ...")


# ============================================================
# Requirement
# ============================================================

def cmd_requirements(args):
    if not args or args[0] == "list":
        params = {}
        if "--project" in args:
            params["projectCode"] = args[args.index("--project") + 1]
        if "--submitter" in args:
            params["submitterCode"] = args[args.index("--submitter") + 1]
        if "--executor" in args:
            params["executorCode"] = args[args.index("--executor") + 1]
        if "--status" in args:
            params["executionStatus"] = args[args.index("--status") + 1]
        if "--name" in args:
            params["requirementName"] = args[args.index("--name") + 1]
        if "--page" in args:
            params["pageNum"] = args[args.index("--page") + 1]
        if "--size" in args:
            params["pageSize"] = args[args.index("--size") + 1]
        data = api_get("/api/requirements", params)
        rows = extract_list(data)
        print(f"需求列表 (共 {len(rows)} 条):")
        for r in rows:
            status = r.get("executionStatus", "")
            name = r.get("requirementName", "未命名")
            project = r.get("projectCode", "")
            executor = r.get("executorNames", "") or "无"
            print(f"  [id={r.get('id', '?')}] {name} — {project} — [{status}]  执行人: {executor}")
    elif args[0] == "create" and len(args) >= 3:
        payload = {"projectCode": args[1], "submitterCode": args[2]}
        # 解析可选参数
        i = 3
        while i < len(args):
            if args[i] == "--name" and i + 1 < len(args):
                payload["requirementName"] = args[i + 1]
                i += 2
            elif args[i] == "--desc" and i + 1 < len(args):
                payload["requirementDesc"] = args[i + 1]
                i += 2
            elif args[i] == "--executors" and i + 1 < len(args):
                payload["executorCodes"] = args[i + 1].split(",")
                i += 2
            else:
                i += 1
        data = api_post("/api/requirements", payload)
        print(f"创建需求: {json.dumps(data, ensure_ascii=False, indent=2)}")
    elif args[0] == "update" and len(args) >= 2:
        payload = {}
        i = 2
        while i < len(args):
            if args[i] == "--name" and i + 1 < len(args):
                payload["requirementName"] = args[i + 1]
                i += 2
            elif args[i] == "--desc" and i + 1 < len(args):
                payload["requirementDesc"] = args[i + 1]
                i += 2
            elif args[i] == "--status" and i + 1 < len(args):
                payload["executionStatus"] = args[i + 1]
                i += 2
            elif args[i] == "--executors" and i + 1 < len(args):
                payload["executorCodes"] = args[i + 1].split(",")
                i += 2
            else:
                i += 1
        data = api_put(f"/api/requirements/{args[1]}", payload)
        print(f"编辑需求: {json.dumps(data, ensure_ascii=False, indent=2)}")
    elif args[0] == "delete" and len(args) >= 2:
        data = api_delete(f"/api/requirements/{args[1]}")
        print(f"删除需求: {json.dumps(data, ensure_ascii=False, indent=2)}")
    else:
        print("用法: python p50_api.py requirements list|create|update|delete ...")


# ============================================================
# 主入口
# ============================================================

COMMANDS = {
    "accounts": cmd_accounts,
    "reports": cmd_reports,
    "projects": cmd_projects,
    "requirements": cmd_requirements,
}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd in COMMANDS:
        COMMANDS[cmd](sys.argv[2:])
    else:
        print(f"未知命令: {cmd}")
        print("可用命令: accounts, reports, projects, requirements")
        sys.exit(1)


if __name__ == "__main__":
    main()
