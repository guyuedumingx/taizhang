import requests
import json
import random

# 基础URL
BASE_URL = "http://localhost:8000/api/v1"
# 会话对象，用于保持cookies（令牌）
session = requests.Session()

# 登录函数
def login(ehr_id, password):
    url = f"{BASE_URL}/auth/login"
    # 使用表单格式
    data = {"username": ehr_id, "password": password}
    response = session.post(url, data=data)
    print(f"登录响应: {response.status_code}")
    if response.status_code == 200:
        token_data = response.json()
        # 设置Authorization头
        session.headers.update({"Authorization": f"Bearer {token_data['access_token']}"})
        return token_data
    else:
        print(f"登录错误: {response.text}")
    return None

# 测试用户管理接口
def test_users_api():
    print("\n=== 测试用户管理接口 ===")
    
    # 获取用户列表
    response = session.get(f"{BASE_URL}/users/")
    print(f"获取用户列表响应: {response.status_code}")
    if response.status_code == 200:
        users = response.json()
        print(f"用户数量: {len(users)}")
    
    # 创建新用户
    random_id = random.randint(1000000, 9999999)
    user_data = {
        "username": f"testapi{random_id}",
        "ehr_id": str(random_id),
        "password": "password123",
        "name": "API测试用户",
        "department": "API测试部门",
        "roles": ["user"]
    }
    response = session.post(f"{BASE_URL}/users/", json=user_data)
    print(f"创建用户响应: {response.status_code}")
    if response.status_code == 200:
        user = response.json()
        print(f"创建的用户: {user['username']} (ID: {user['id']})")
        user_id = user['id']
        
        # 更新用户
        update_data = {
            "name": "更新后的API测试用户",
            "department": "更新后的API测试部门"
        }
        response = session.put(f"{BASE_URL}/users/{user_id}", json=update_data)
        print(f"更新用户响应: {response.status_code}")
        
        # 删除用户
        response = session.delete(f"{BASE_URL}/users/{user_id}")
        print(f"删除用户响应: {response.status_code}")

# 测试团队管理接口
def test_teams_api():
    print("\n=== 测试团队管理接口 ===")
    
    # 获取团队列表
    response = session.get(f"{BASE_URL}/teams/")
    print(f"获取团队列表响应: {response.status_code}")
    if response.status_code == 200:
        teams = response.json()
        print(f"团队数量: {len(teams)}")
    
    # 创建新团队
    team_data = {
        "name": "API测试团队",
        "description": "这是一个API测试团队",
        "department": "API测试部门"
    }
    response = session.post(f"{BASE_URL}/teams/", json=team_data)
    print(f"创建团队响应: {response.status_code}")
    if response.status_code == 200:
        team = response.json()
        print(f"创建的团队: {team['name']} (ID: {team['id']})")
        team_id = team['id']
        
        # 获取团队成员
        response = session.get(f"{BASE_URL}/teams/{team_id}/members")
        print(f"获取团队成员响应: {response.status_code}")
        if response.status_code == 200:
            members = response.json()
            print(f"团队成员数量: {len(members)}")
        
        # 创建一个用户添加到团队
        random_id = random.randint(1000000, 9999999)
        user_data = {
            "username": f"teamtest{random_id}",
            "ehr_id": str(random_id),
            "password": "password123",
            "name": "团队测试用户",
            "department": "API测试部门",
            "roles": ["user"]
        }
        response = session.post(f"{BASE_URL}/users/", json=user_data)
        if response.status_code == 200:
            user = response.json()
            user_id = user['id']
            
            # 添加用户到团队
            response = session.post(f"{BASE_URL}/teams/{team_id}/members/{user_id}")
            print(f"添加用户到团队响应: {response.status_code}")
            
            # 获取团队成员
            response = session.get(f"{BASE_URL}/teams/{team_id}/members")
            if response.status_code == 200:
                members = response.json()
                print(f"添加用户后团队成员数量: {len(members)}")
            
            # 从团队中移除用户
            response = session.delete(f"{BASE_URL}/teams/{team_id}/members/{user_id}")
            print(f"从团队中移除用户响应: {response.status_code}")
            
            # 删除用户
            session.delete(f"{BASE_URL}/users/{user_id}")
        
        # 更新团队
        update_data = {
            "name": "更新后的API测试团队",
            "description": "这是更新后的API测试团队描述"
        }
        response = session.put(f"{BASE_URL}/teams/{team_id}", json=update_data)
        print(f"更新团队响应: {response.status_code}")
        
        # 删除团队
        response = session.delete(f"{BASE_URL}/teams/{team_id}")
        print(f"删除团队响应: {response.status_code}")

if __name__ == "__main__":
    # 使用测试用户登录
    token_data = login("1234567", "password123")
    if token_data:
        print("登录成功")
        # 测试用户管理API
        test_users_api()
        # 测试团队管理API
        test_teams_api()
    else:
        print("登录失败") 