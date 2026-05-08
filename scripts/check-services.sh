#!/bin/bash
# 检查 WorkBuddy 相关服务状态
# 自动检测本机 IP，优先使用 localhost
# 用法: ./check-services.sh

P50_BACKEND="http://10.88.109.205:8080"

# 自动检测 api-doc-server 和 P50 MCP 的地址
# 先用 localhost，失败则尝试检测本机 IP
API_DOC_SERVER="http://localhost:2338"
P50_MCP="http://localhost:2339"

# 尝试检测 api-doc-server
http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "$API_DOC_SERVER/api/projects" 2>/dev/null)
if [ "$http_code" != "200" ]; then
    # localhost 失败，尝试获取本机 IP
    local_ip=$(ipconfig 2>/dev/null | grep -i "IPv4" | head -1 | awk '{print $NF}' | tr -d '\r')
    if [ -n "$local_ip" ]; then
        API_DOC_SERVER="http://$local_ip:2338"
        P50_MCP="http://$local_ip:2339"
    fi
fi

echo "=== 服务状态检查 ==="
echo ""

# 检查 api-doc-server
http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 "$API_DOC_SERVER/api/projects" 2>/dev/null)
if [ "$http_code" = "200" ]; then
    echo "✅ api-doc-server ($API_DOC_SERVER) — 运行正常"
else
    echo "❌ api-doc-server ($API_DOC_SERVER) — 未响应 (HTTP $http_code)"
fi

# 检查 P50 MCP Server
mcp_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 "$P50_MCP/mcp" 2>/dev/null)
if [ "$mcp_code" != "000" ]; then
    echo "✅ P50 MCP Server ($P50_MCP) — 可连接 (HTTP $mcp_code)"
else
    echo "❌ P50 MCP Server ($P50_MCP) — 未响应"
fi

# 检查 P50 后端 API
backend_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 "$P50_BACKEND/api/projects" 2>/dev/null)
if [ "$backend_code" != "000" ]; then
    echo "✅ P50 后端 API ($P50_BACKEND) — 可连接 (HTTP $backend_code)"
else
    echo "❌ P50 后端 API ($P50_BACKEND) — 未响应"
fi

echo ""
echo "=== 端口占用 ==="
netstat -ano 2>/dev/null | grep -E "2338|2339" || echo "相关端口无监听"
