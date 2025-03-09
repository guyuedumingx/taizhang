#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# API基础URL
BASE_URL="http://localhost:8080/api/v1"
echo "API基础URL: $BASE_URL"

# 获取测试令牌
echo -e "\n${YELLOW}获取测试令牌${NC}"
curl -s -X GET "$BASE_URL/test-token" > token_response.json
cat token_response.json
TOKEN=$(cat token_response.json | grep -o '"access_token":"[^"]*"' | cut -d':' -f2 | tr -d '"' | tr -d '\r' | tr -d '}')
echo "提取的令牌: $TOKEN"

if [ -z "$TOKEN" ]; then
  echo -e "${RED}获取令牌失败${NC}"
  exit 1
else
  echo -e "${GREEN}获取令牌成功${NC}"
fi

# 测试健康检查API
echo -e "\n${YELLOW}测试健康检查API${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/health")
echo "响应: $RESPONSE"
if echo "$RESPONSE" | grep -q "ok"; then
  echo -e "${GREEN}✓ 健康检查API正常${NC}"
else
  echo -e "${RED}✗ 健康检查API异常${NC}"
fi

# 测试当前用户信息API
echo -e "\n${YELLOW}测试当前用户信息API${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/auth/me" -H "Authorization: Bearer $TOKEN")
echo "响应: $RESPONSE"
if echo "$RESPONSE" | grep -q "username"; then
  echo -e "${GREEN}✓ 当前用户信息API正常${NC}"
else
  echo -e "${RED}✗ 当前用户信息API异常${NC}"
fi

# 测试用户列表API
echo -e "\n${YELLOW}测试用户列表API${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/users/" -H "Authorization: Bearer $TOKEN")
echo "响应前100个字符: ${RESPONSE:0:100}..."
if echo "$RESPONSE" | grep -q "username"; then
  echo -e "${GREEN}✓ 用户列表API正常${NC}"
else
  echo -e "${RED}✗ 用户列表API异常${NC}"
fi

# 测试团队列表API
echo -e "\n${YELLOW}测试团队列表API${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/teams/" -H "Authorization: Bearer $TOKEN")
echo "响应前100个字符: ${RESPONSE:0:100}..."
if echo "$RESPONSE" | grep -q "name"; then
  echo -e "${GREEN}✓ 团队列表API正常${NC}"
else
  echo -e "${RED}✗ 团队列表API异常${NC}"
fi

# 测试角色列表API
echo -e "\n${YELLOW}测试角色列表API${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/roles/" -H "Authorization: Bearer $TOKEN")
echo "响应前100个字符: ${RESPONSE:0:100}..."
if echo "$RESPONSE" | grep -q "name"; then
  echo -e "${GREEN}✓ 角色列表API正常${NC}"
else
  echo -e "${RED}✗ 角色列表API异常${NC}"
fi

# 测试台账列表API
echo -e "\n${YELLOW}测试台账列表API${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/ledgers/" -H "Authorization: Bearer $TOKEN")
echo "响应前100个字符: ${RESPONSE:0:100}..."
if echo "$RESPONSE" | grep -q "name"; then
  echo -e "${GREEN}✓ 台账列表API正常${NC}"
else
  echo -e "${RED}✗ 台账列表API异常${NC}"
fi

# 测试模板列表API
echo -e "\n${YELLOW}测试模板列表API${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/templates/" -H "Authorization: Bearer $TOKEN")
echo "响应前100个字符: ${RESPONSE:0:100}..."
if echo "$RESPONSE" | grep -q "name"; then
  echo -e "${GREEN}✓ 模板列表API正常${NC}"
else
  echo -e "${RED}✗ 模板列表API异常${NC}"
fi

# 测试工作流列表API
echo -e "\n${YELLOW}测试工作流列表API${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/workflows/" -H "Authorization: Bearer $TOKEN")
echo "响应前100个字符: ${RESPONSE:0:100}..."
if echo "$RESPONSE" | grep -q "name"; then
  echo -e "${GREEN}✓ 工作流列表API正常${NC}"
else
  echo -e "${RED}✗ 工作流列表API异常${NC}"
fi

# 测试工作流节点列表API
echo -e "\n${YELLOW}测试工作流节点列表API${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/workflows/1/nodes" -H "Authorization: Bearer $TOKEN")
echo "响应前100个字符: ${RESPONSE:0:100}..."
if echo "$RESPONSE" | grep -q "name"; then
  echo -e "${GREEN}✓ 工作流节点列表API正常${NC}"
else
  echo -e "${RED}✗ 工作流节点列表API异常${NC}"
fi

# 测试待办任务API
echo -e "\n${YELLOW}测试待办任务API${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/approvals/tasks" -H "Authorization: Bearer $TOKEN")
echo "响应: $RESPONSE"
if [ "$RESPONSE" == "[]" ] || echo "$RESPONSE" | grep -q "id"; then
  echo -e "${GREEN}✓ 待办任务API正常${NC}"
else
  echo -e "${RED}✗ 待办任务API异常${NC}"
fi

# 测试工作流节点审批人API
echo -e "\n${YELLOW}测试工作流节点审批人API${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/workflows/nodes/2/approvers" -H "Authorization: Bearer $TOKEN")
echo "响应: $RESPONSE"
if echo "$RESPONSE" | grep -q "Not Found"; then
  echo -e "${GREEN}✓ 工作流节点审批人API返回404（预期）${NC}"
else
  echo -e "${RED}✗ 工作流节点审批人API异常${NC}"
fi

# 测试工作流节点审批人API（使用正确路径）
echo -e "\n${YELLOW}测试工作流节点审批人API（新路径）${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/workflow-nodes/2/approvers" -H "Authorization: Bearer $TOKEN")
echo "响应: $RESPONSE"
if echo "$RESPONSE" | grep -q "Not Found"; then
  echo -e "${GREEN}✓ 工作流节点审批人API（新路径）返回404（预期）${NC}"
else
  echo -e "${RED}✗ 工作流节点审批人API（新路径）异常${NC}"
fi

echo -e "\n${YELLOW}测试完成${NC}" 