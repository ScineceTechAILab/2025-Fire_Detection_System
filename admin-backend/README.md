# 管理系统后端

## 启动方式

### 本地开发

```bash
cd admin-backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Docker 启动

```bash
docker-compose up -d backend
```

## API 文档

启动后访问：http://localhost:8001/docs

## 运行测试

```bash
pytest tests/ -v --cov=app --cov-report=html
```

## 配置说明

- `.env` - 静态敏感信息（飞书 appid、阿里云密钥等）
- `config/feishu.json` - 飞书配置（群聊 ID、联系人）
- `config/sms.json` - 短信配置（联系人）

## 热加载配置

调用接口 `/api/v1/system/reload` 即可重新加载配置，无需重启服务。
