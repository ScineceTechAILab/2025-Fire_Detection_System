# 管理系统前端

## 启动方式

### 本地开发

```bash
cd admin-frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问：http://localhost:5173

### 构建生产版本

```bash
npm run build
```

### Docker 启动

```bash
docker-compose up -d frontend
```

## 代码规范

```bash
# 代码检查
npm run lint

# 代码格式化
npm run format
```

## 技术栈

- Vue 3
- TypeScript
- Vite
- Element Plus
- Pinia
- Vue Router
- Axios
