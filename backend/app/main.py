from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from app.api.api_v1.api import api_router
from app.core.config import settings
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    name: str

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="台账管理系统API",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# 设置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含API路由
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "台账管理系统API服务"}

@app.get("/api/v1/auth/login")
async def login_test():
    return {"message": "登录API测试"}

@app.post("/api/v1/auth/register")
async def register_test(user_in: UserCreate):
    return {
        "id": 1,
        "username": user_in.username,
        "email": user_in.email,
        "name": user_in.name,
        "is_active": True,
        "is_superuser": False,
        "department": "未分配",
        "team_id": None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True) 