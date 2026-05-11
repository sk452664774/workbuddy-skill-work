#!/bin/bash
# ============================================================
# run.sh — Python 解释器自动检测包装器
#
# 自动寻找可用的 Python 解释器，然后在同一个进程中运行
# 指定的 Python 脚本，透传所有参数。
#
# 兼容性设计：
#   - macOS/Linux: python3 或 python 通常直接可用
#   - Windows Git Bash + 正常 Python: python/py 可用
#   - Windows Git Bash + 破损 WindowsApps stub: 自动 fallback
#
# 用法:
#   bash run.sh query_api.py --direct projects
#   bash run.sh p50_api.py accounts list
# ============================================================

# 获取脚本所在目录（作为 SCRIPTS_DIR）
SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"

# ============================================================
# 候选 Python 列表（按优先级排列）
# ============================================================
CANDIDATES=()

# 1. 优先尝试标准的 python3 / python / py 命令
for cmd in python3 python py; do
    if command -v "$cmd" &>/dev/null; then
        CANDIDATES+=("$cmd")
    fi
done

# 2. Windows 下搜索常见安装路径
#    遍历所有 Python3* 子目录
if [ -d "$LOCALAPPDATA/Programs/Python" ]; then
    for p in "$LOCALAPPDATA/Programs/Python/Python3"*/python.exe; do
        [ -f "$p" ] && CANDIDATES+=("$p")
    done
fi

# 3. Git Bash / C 盘常见路径
for p in /c/Python311/python.exe /c/Python312/python.exe /c/Python313/python.exe; do
    [ -f "$p" ] && CANDIDATES+=("$p")
done

# 4. WorkBuddy managed Python
if [ -d "$HOME/.workbuddy/binaries/python/versions" ]; then
    for p in "$HOME/.workbuddy/binaries/python/versions"/*/python.exe; do
        [ -f "$p" ] && CANDIDATES+=("$p")
    done
fi

# ============================================================
# 检测并运行
# ============================================================
for py in "${CANDIDATES[@]}"; do
    if "$py" -c "import sys; sys.exit(0)" &>/dev/null; then
        exec "$py" "$SCRIPTS_DIR/${1:?用法: run.sh <脚本名> [参数...]}" "${@:2}"
        # exec 不会返回，执行成功即结束
    fi
done

# ============================================================
# 所有候选都失败 → 报错退出
# ============================================================
cat >&2 <<'EOF'
❌ 找不到可用的 Python 解释器

请安装 Python 3.8+:
  - 官网下载: https://www.python.org/downloads/
  - 或使用 WorkBuddy managed Python

已尝试的检测路径:
  - python3, python, py 命令
  - %LOCALAPPDATA%\Programs\Python\Python3*\python.exe
  - C:\Python3*\python.exe
  - ~/.workbuddy/binaries/python/versions/*/python.exe

如果 Python 已安装但在其他位置，请手动指定:
  bash run.sh <脚本名>                    # 自动检测
  /path/to/python run.sh <脚本名>         # 或直接运行
EOF
exit 1
