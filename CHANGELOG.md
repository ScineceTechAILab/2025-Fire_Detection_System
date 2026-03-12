# CHANGELOG

## v1.0.0 - 2026-03-11

### 新增功能

#### 后端（admin-backend）
- ✅ 创建完整的 FastAPI 后端项目结构
- ✅ 实现飞书管理模块
  - 群聊 ID 配置（单值配置）
  - 紧急联系人 CRUD（多值配置）
  - 手机号自动补全国家码 +86
  - 手机号格式校验
- ✅ 实现云短信管理模块
  - 紧急联系人 CRUD（与飞书模块数据结构一致）
  - 独立路由与状态管理，数据隔离
- ✅ 实现 JSON 文件存储
  - 配置文件保存在 `config/` 目录
  - `feishu.json` - 飞书配置
  - `sms.json` - 短信配置
  - 文件首次不存在时自动创建空模板
  - 文件锁防止并发写入损坏
- ✅ 实现配置热加载
  - 启动时一次性加载 JSON 到内存
  - `/api/v1/system/reload` 接口实现热加载
  - 无需重启服务即可更新配置
- ✅ 静态敏感信息管理
  - 使用 python-dotenv 从 `.env` 读取密钥
  - 代码中无明文密钥
- ✅ 统一响应格式 `{code, msg, data}`
- ✅ 完整的单元测试（覆盖正常流、异常流、并发场景）

#### 前端（admin-frontend）
- ✅ 创建 Vue3 + TypeScript + Vite 项目
- ✅ 集成 Element Plus UI 组件库
- ✅ 集成 Pinia 状态管理
- ✅ 集成 Vue Router 路由管理
- ✅ Axios 统一封装与拦截器
- ✅ 飞书管理页面
  - 群聊 ID 配置表单
  - 联系人列表展示
  - 新增/编辑联系人表单（带校验）
  - 删除二次确认
  - 操作成功/失败提示
- ✅ 云短信管理页面
  - 联系人列表展示
  - 新增/编辑/删除联系人
  - 复用飞书管理的通用组件
- ✅ 抽离通用组件
  - `ContactForm.vue` - 联系人表单组件
  - `ContactList.vue` - 联系人列表组件
- ✅ TypeScript 严格模式
- ✅ ESLint + Prettier 代码规范

#### 部署
- ✅ 后端 Dockerfile
- ✅ 前端 Dockerfile + Nginx 配置
- ✅ docker-compose.yml 一键启动
- ✅ 完整的 README 文档

### 技术栈

#### 后端
- Python 3.10+
- FastAPI
- Pydantic
- uvicorn
- pytest

#### 前端
- Vue 3
- TypeScript
- Vite
- Element Plus
- Pinia
- Vue Router
- Axios

### 项目结构

```
.
├── admin-backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py          # 配置管理
│   │   │   └── storage.py         # JSON 存储管理
│   │   ├── routers/
│   │   │   ├── feishu.py          # 飞书路由
│   │   │   ├── sms.py             # 短信路由
│   │   │   └── system.py          # 系统路由
│   │   ├── schemas/
│   │   │   ├── common.py          # 通用响应
│   │   │   ├── contact.py         # 联系人模型
│   │   │   ├── feishu.py          # 飞书模型
│   │   │   └── sms.py             # 短信模型
│   │   ├── services/
│   │   │   ├── contact_service.py # 联系人服务
│   │   │   ├── feishu_service.py  # 飞书服务
│   │   │   └── sms_service.py     # 短信服务
│   │   └── main.py                # 应用入口
│   ├── tests/
│   │   ├── test_feishu.py         # 飞书测试
│   │   ├── test_sms.py            # 短信测试
│   │   └── test_system.py         # 系统测试
│   ├── config/                    # 配置文件目录
│   ├── requirements.txt
│   ├── .env
│   └── Dockerfile
├── admin-frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── feishu.ts          # 飞书 API
│   │   │   └── sms.ts             # 短信 API
│   │   ├── components/
│   │   │   ├── ContactForm.vue    # 联系人表单
│   │   │   └── ContactList.vue    # 联系人列表
│   │   ├── stores/
│   │   │   ├── feishu.ts          # 飞书状态
│   │   │   └── sms.ts             # 短信状态
│   │   ├── views/
│   │   │   ├── FeishuView.vue     # 飞书页面
│   │   │   └── SmsView.vue        # 短信页面
│   │   ├── router/
│   │   │   └── index.ts           # 路由配置
│   │   ├── types/
│   │   │   └── index.ts           # 类型定义
│   │   ├── utils/
│   │   │   └── request.ts         # axios 封装
│   │   ├── App.vue
│   │   └── main.ts
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── nginx.conf
│   └── Dockerfile
└── docker-compose.yml
```
