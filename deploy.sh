#!/bin/bash

# 类级注释：STALAB 火灾检测系统一键部署脚本
# 功能：
# - Git 仓库更新
# - 配置文件检查
# - Docker 容器部署
# - 健康检查

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 函数级注释：打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}


# 函数级注释：检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "命令 $1 未安装，请先安装"
        exit 1
    fi
}

# 函数级注释：Git 更新仓库
git_update() {
    print_info "更新 Git 仓库..."
    
    if [ ! -d ".git" ]; then
        print_warning "当前目录不是 Git 仓库，跳过更新"
        return
    fi
    
    git fetch --all
    # 尝试重置到 main，失败则尝试 master
    git reset --hard origin/main || git reset --hard origin/master || {
        print_warning "无法重置到远程分支，请手动检查"
        return
    }
    git pull
    
    print_success "Git 仓库更新完成"
}

# 函数级注释：检查 Docker 和 Docker Compose
check_docker() {
    print_info "检查 Docker 环境..."
    check_command docker
    
    if ! docker compose version &> /dev/null; then
        print_error "Docker Compose 插件未安装或无法运行"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker 服务未运行，请先启动 Docker"
        exit 1
    fi
    
    print_success "Docker 环境检查通过"
}



# 函数级注释：检查配置文件
check_config_files() {
    print_info "检查配置文件..."
    
    local config_dir="admin-backend/config"
    local required_files=(
        "admin.json"
        "feishu.json"
        "sms.json"
        "system.json"
    )
    
    if [ ! -d "$config_dir" ]; then
        print_warning "配置目录 $config_dir 不存在，正在创建..."
        mkdir -p "$config_dir"
    fi
    
    local missing_files=()
    for file in "${required_files[@]}"; do
        if [ ! -f "$config_dir/$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        print_warning "缺少以下配置文件: ${missing_files[*]}"
        print_warning "将创建默认配置文件..."
        
        for file in "${missing_files[@]}"; do
            case "$file" in
                admin.json)
                    cat > "$config_dir/$file" << 'EOF'
{"username":"admin","password":"$2b$12$KIX/Qr/vf6b5f5f5f5f5fOeX7X7X7X7X7X7X7X7X7X7X7X7X7X7"}
EOF
                    ;;
                feishu.json)
                    cat > "$config_dir/$file" << 'EOF'
{"contacts":[]}
EOF
                    ;;
                sms.json)
                    cat > "$config_dir/$file" << 'EOF'
{"contacts":[]}
EOF
                    ;;
                system.json)
                    cat > "$config_dir/$file" << 'EOF'
{"rtsp_url":"","yolo_device":"cuda:0","yolo_confidence":0.5,"consecutive_threshold":3,"alert_cooldown_seconds":60}
EOF
                    ;;
            esac
            print_success "已创建默认配置文件: $file"
        done
    fi
    
    # 检查 .env 文件
    if [ ! -f "admin-backend/.env" ]; then
        print_warning "admin-backend/.env 不存在，正在创建..."
        cat > "admin-backend/.env" << 'EOF'
feishu_app_id=
feishu_app_secret=
ALI_ACCESS_KEY_ID=
ALI_ACCESS_KEY_SECRET=
ALI_SMS_SIGN_NAME=
ALI_SMS_TEMPLATE_CODE=
EOF
        print_success "已创建默认 .env 文件"
    fi
    
    print_success "配置文件检查完成"
}

# 函数级注释：检查持久化目录
check_directories() {
    print_info "检查持久化目录..."
    
    local dirs=(
        "admin-backend/config"
        "log"
        "output"
        "core/yolo/weights"
    )
    
    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            print_warning "创建目录: $dir"
            mkdir -p "$dir"
        fi
    done
    
    # 检查 YOLO 权重文件
    if [ ! -f "core/yolo/weights/best.pt" ]; then
        print_warning "YOLO 权重文件 core/yolo/weights/best.pt 不存在"
        print_warning "请确保在部署前上传权重文件"
    fi
    
    print_success "目录检查完成"
}

# 函数级注释：停止现有容器
stop_containers() {
    print_info "停止现有容器..."
    
    if [ -f "docker-compose.yml" ]; then
        docker compose down || true
    fi
    
    print_success "容器已停止"
}

# 函数级注释：构建并启动容器
build_and_start() {
    print_info "构建并启动容器..."
    
    docker compose build
    docker compose up -d
    
    print_success "容器已启动"
}

# 函数级注释：健康检查
health_check() {
    print_info "执行健康检查..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker compose ps | grep -q "Up"; then
            print_success "容器健康检查通过"
            
            echo ""
            echo "========================================"
            echo "部署成功！"
            echo "========================================"
            echo "后端健康检查: http://localhost:8001/health"
            echo "管理后台: http://localhost:8080"
            echo "========================================"
            echo ""
            
            docker compose ps
            return
        fi
        
        print_info "等待容器启动... ($attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "健康检查超时，请检查容器日志"
    docker compose logs
    exit 1
}

# 函数级注释：显示帮助信息
show_help() {
    cat << 'EOF'
STALAB 火灾检测系统一键部署脚本

用法: ./deploy.sh [选项]

选项:
    -h, --help      显示帮助信息
    --no-git        跳过 Git 更新
    --no-health     跳过健康检查
    --stop-only     仅停止容器
    --logs          显示容器日志

示例:
    ./deploy.sh                    # 完整部署
    ./deploy.sh --no-git           # 不更新 Git
    ./deploy.sh --stop-only        # 仅停止容器
    ./deploy.sh --logs             # 显示日志
EOF
}

# 主函数
main() {
    local skip_git=false
    local skip_health=false
    local stop_only=false
    local show_logs=false
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_help
                exit 0
                ;;
            --no-git)
                skip_git=true
                shift
                ;;
            --no-health)
                skip_health=true
                shift
                ;;
            --stop-only)
                stop_only=true
                shift
                ;;
            --logs)
                show_logs=true
                shift
                ;;
            *)
                print_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    echo ""
    echo "========================================"
    echo "STALAB 火灾检测系统 - 一键部署"
    echo "========================================"
    echo ""
    
    if [ "$show_logs" = true ]; then
        docker compose logs -f
        exit 0
    fi
    
    if [ "$stop_only" = true ]; then
        stop_containers
        print_success "容器已停止"
        exit 0
    fi
    
    check_docker
    check_directories
    
    if [ "$skip_git" = false ]; then
        git_update
    fi
    
    check_config_files
    stop_containers
    build_and_start
    
    if [ "$skip_health" = false ]; then
        health_check
    else
        print_success "部署完成（跳过健康检查）"
        docker compose ps
    fi
}

main "$@"