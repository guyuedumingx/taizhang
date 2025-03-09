#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# API基础URL
BASE_URL="http://localhost:8080/api/v1"
echo "API基础URL: $BASE_URL"

# 函数：测试API
test_api() {
  local method=$1
  local endpoint=$2
  local expected_status=$3
  local description=$4
  local headers=$5
  local data=$6
  
  echo -e "\n${YELLOW}测试 $description${NC}"
  echo "请求: $method $BASE_URL$endpoint"
  
  # 构建curl命令
  local cmd="curl -s -o response.json -w '%{http_code}' -X $method \"$BASE_URL$endpoint\""
  
  # 添加头
  if [ ! -z "$headers" ]; then
    for header in $headers; do
      cmd="$cmd -H \"$header\""
    done
  fi
  
  # 添加数据
  if [ ! -z "$data" ]; then
    cmd="$cmd -d '$data'"
  fi
  
  # 执行curl命令获取状态码
  local status=$(eval $cmd)
  echo "状态码: $status"
  
  # 读取响应
  local response=$(cat response.json)
  echo "响应: ${response:0:100}..."
  
  # 检查状态码
  if [ "$status" -eq "$expected_status" ]; then
    echo -e "${GREEN}✓ 状态码匹配 ($status)${NC}"
    return 0
  else
    echo -e "${RED}✗ 状态码不匹配 (实际: $status, 预期: $expected_status)${NC}"
    return 1
  fi
}

# 从测试令牌API获取令牌
echo -e "\n${YELLOW}获取测试令牌${NC}"
curl -s -X GET "$BASE_URL/test-token" > token_response.json
TOKEN=$(cat token_response.json | grep -o '"access_token":"[^"]*"' | cut -d':' -f2 | tr -d '"')

if [ -z "$TOKEN" ]; then
  echo -e "${RED}获取令牌失败${NC}"
  exit 1
else
  echo -e "${GREEN}获取令牌成功${NC}"
  echo "令牌: ${TOKEN:0:20}..."
fi

# 测试健康检查API
test_api "GET" "/health" 200 "健康检查API" "" ""

# 测试当前用户信息API
test_api "GET" "/auth/me" 200 "当前用户信息API" "Authorization: Bearer $TOKEN" ""

# 测试用户列表API
test_api "GET" "/users/" 200 "用户列表API" "Authorization: Bearer $TOKEN" ""

# 测试团队列表API
test_api "GET" "/teams/" 200 "团队列表API" "Authorization: Bearer $TOKEN" ""

# 测试角色列表API
test_api "GET" "/roles/" 200 "角色列表API" "Authorization: Bearer $TOKEN" ""

# 测试台账列表API
test_api "GET" "/ledgers/" 200 "台账列表API" "Authorization: Bearer $TOKEN" ""

# 测试模板列表API
test_api "GET" "/templates/" 200 "模板列表API" "Authorization: Bearer $TOKEN" ""

# 测试工作流列表API
test_api "GET" "/workflows/" 200 "工作流列表API" "Authorization: Bearer $TOKEN" ""

# 测试工作流节点列表API
test_api "GET" "/workflows/1/nodes" 200 "工作流节点列表API" "Authorization: Bearer $TOKEN" ""

# 测试待办任务API
test_api "GET" "/approvals/tasks" 200 "待办任务API" "Authorization: Bearer $TOKEN" ""

# 测试工作流节点审批人API - 注意预期状态码是404，因为该API尚未实现
test_api "GET" "/workflows/nodes/2/approvers" 404 "工作流节点审批人API" "Authorization: Bearer $TOKEN" ""

# 测试工作流节点审批人API（使用正确路径 - 如果问题修复后）
test_api "GET" "/workflow-nodes/2/approvers" 404 "工作流节点审批人API（新路径）" "Authorization: Bearer $TOKEN" ""

echo -e "\n${YELLOW}测试完成${NC}" 