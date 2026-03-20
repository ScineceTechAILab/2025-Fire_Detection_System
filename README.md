# Fire Detection System

基于 YOLOv8 的火灾检测系统，包含实时检测主程序、管理后台后端（FastAPI）和管理后台前端（Vue 3）。

系统支持以下核心能力：
- 视频流火焰检测（本地摄像头或 RTSP）
- 告警截图落盘
- 飞书群消息通知
- 短信通知（阿里云）
- 后台参数管理与配置热加载

## 1. 系统架构

项目包含 3 个主要服务：
- `main-service`：检测主程序，入口 `main.py`
- `admin-backend`：管理后台后端，端口 `8001`
- `admin-frontend`：管理后台前端（Nginx 托管），端口 `8080`

默认 Docker Compose 编排文件位于项目根目录：`docker-compose.yml`。

## 2. 快速开始（Docker，推荐）

### 2.1 前置条件

- Docker
- Docker Compose
- 已准备 YOLO 权重文件：`core/yolo/weights/best.pt`

可选（GPU 推理）：
- 可用 NVIDIA 驱动与容器运行时（NVIDIA Container Toolkit）

### 2.2 启动步骤

在项目根目录执行：

```bash
docker compose build
docker compose up -d
docker compose ps
```

### 2.3 访问与健康检查

- 前端管理台：`http://localhost:8080`
- 后端健康检查：`http://localhost:8001/health`
- 后端 API 文档：`http://localhost:8001/docs`

### 2.4 查看日志

```bash
docker compose logs -f main-service
docker compose logs -f admin-backend
```

## 3. 配置说明

### 3.1 配置文件目录

主程序会读取 `admin-backend/config` 下的配置：
- `system.json`：系统运行参数（检测阈值、设备、冷却时间等）
- `feishu.json`：飞书群与联系人
- `sms.json`：短信联系人
- `credentials.json`：敏感凭据（飞书/阿里云）

### 3.2 凭据读取优先级

主程序敏感配置读取逻辑：
1. 优先读取 `admin-backend/config/credentials.json`
2. 若未配置，再降级读取根目录 `.env`

### 3.3 关键参数（来自 `system.json`）

常用参数包括：
- `yolo_weights`
- `yolo_device`
- `yolo_confidence`
- `camera_index`
- `rtsp_url`
- `detection_interval`
- `consecutive_threshold`
- `alert_cooldown_seconds`
- `confirm_wait_seconds`

### 3.4 配置热加载

更新后台配置后，可调用后端接口重新加载配置：

```http
POST /api/v1/system/reload
```

## 4. 本地开发

### 4.1 启动主程序（检测服务）

```bash
pip install -r requirements.txt
python main.py
```

说明：
- 本地模式下会尝试显示 OpenCV 窗口，按 `q` 退出。
- 如需无界面运行，可设置环境变量 `HEADLESS=1`。

### 4.2 启动管理后端

```bash
cd admin-backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### 4.3 启动管理前端

```bash
cd admin-frontend
npm install
npm run dev
```

开发模式默认地址：`http://localhost:5173`

## 5. 目录结构（核心）

```text
FireDetectionSystem/
├── main.py
├── requirements.txt
├── docker-compose.yml
├── core/
│   ├── yolo/
│   │   ├── detector.py
│   │   └── weights/best.pt
│   └── communication/
├── admin-backend/
│   ├── app/
│   └── config/
├── admin-frontend/
│   └── src/
├── output/
├── log/
├── docs/
└── test/
```

## 6. 常见问题

### 6.1 摄像头或 RTSP 无法读取

- 检查 `system.json` 中 `rtsp_url` 或 `camera_index`
- 确认网络可达、账号密码正确
- 确认目标流地址可被 OpenCV 拉流

### 6.2 服务端无界面运行报错

建议开启无界面模式：

```bash
export HEADLESS=1
# Windows PowerShell: $env:HEADLESS='1'
```

### 6.3 GPU 未生效

- 检查宿主机 `nvidia-smi`
- 检查容器内是否可见 GPU
- 检查 `system.json` 中 `yolo_device`（如 `cuda:0`）

### 6.4 告警没有触发

- 检查 `yolo_confidence` 是否过高
- 检查 `consecutive_threshold` 和 `detection_interval`
- 检查 `alert_cooldown_seconds` 是否处于冷却期
- 检查飞书与短信配置是否完整

## 7. 安全建议

- 不要将真实密钥、手机号、摄像头地址提交到仓库
- 建议对管理后台加访问控制（内网、反向代理、TLS）
- 生产环境请修改默认账户密码并定期轮换密钥

## 8. 相关文档

更多说明见 `docs/`：
- `docs/部署指南.md`
- `docs/系统参数管理操作手册.md`
- `docs/管理系统登录配置说明.md`
- `docs/Advanced_Fire_Detection_Report.md`
