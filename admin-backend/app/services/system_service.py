"""
类级注释：系统参数管理服务
提供系统参数的 CRUD、版本控制、审计日志等功能
"""
import json
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from ..schemas.system import (
    SystemParam, ParamType, ParamCategory, ParamPermission,
    ParamVersion, ParamAuditLog, SystemConfigUpdate
)
from ..core.storage import get_storage_manager


def safe_model_dump(obj):
    """
    函数级注释：安全的模型序列化，处理 datetime 等特殊类型
    """
    data = obj.model_dump()
    for key, value in data.items():
        if isinstance(value, datetime):
            data[key] = value.isoformat()
    return data


class SystemParamService:
    """
    类级注释：系统参数管理服务
    """
    
    def __init__(self):
        self.storage = get_storage_manager()
        self.config_file = "system.json"
        self.versions_file = "system_versions.json"
        self.audit_file = "system_audit.json"
        self._init_default_config()
    
    def _init_default_config(self):
        """
        函数级注释：初始化默认系统参数配置
        """
        default_params = [
            # YOLO 检测参数
            {
                "key": "yolo_weights",
                "value": "core/yolo/weights/best.pt",
                "type": ParamType.STRING,
                "category": ParamCategory.YOLO_DETECTION,
                "description": "YOLO 模型权重文件路径",
                "permission": ParamPermission.RESTRICTED,
                "requires_restart": True
            },
            {
                "key": "yolo_confidence",
                "value": 0.5,
                "type": ParamType.FLOAT,
                "category": ParamCategory.YOLO_DETECTION,
                "description": "YOLO 检测置信度阈值",
                "default_value": 0.5,
                "min_value": 0.1,
                "max_value": 1.0,
                "permission": ParamPermission.EDITABLE,
                "requires_restart": False
            },
            {
                "key": "yolo_iou_threshold",
                "value": 0.45,
                "type": ParamType.FLOAT,
                "category": ParamCategory.YOLO_DETECTION,
                "description": "YOLO NMS IOU 阈值",
                "default_value": 0.45,
                "min_value": 0.1,
                "max_value": 1.0,
                "permission": ParamPermission.EDITABLE,
                "requires_restart": False
            },
            {
                "key": "yolo_imgsz",
                "value": 640,
                "type": ParamType.INTEGER,
                "category": ParamCategory.YOLO_DETECTION,
                "description": "YOLO 输入图像尺寸",
                "default_value": 640,
                "options": [416, 640, 832, 1024],
                "permission": ParamPermission.RESTRICTED,
                "requires_restart": True
            },
            # 报警逻辑参数
            {
                "key": "fire_small_area_threshold",
                "value": 1500,
                "type": ParamType.INTEGER,
                "category": ParamCategory.YOLO_DETECTION,
                "description": "Small-target area threshold for fire validation (pixels)",
                "default_value": 1500,
                "min_value": 100,
                "max_value": 50000,
                "permission": ParamPermission.EDITABLE,
                "requires_restart": False
            },
            {
                "key": "fire_medium_area_threshold",
                "value": 6000,
                "type": ParamType.INTEGER,
                "category": ParamCategory.YOLO_DETECTION,
                "description": "Medium-target area threshold for fire validation (pixels)",
                "default_value": 6000,
                "min_value": 500,
                "max_value": 300000,
                "permission": ParamPermission.EDITABLE,
                "requires_restart": False
            },
            {
                "key": "fire_small_target_motion_min",
                "value": 0.08,
                "type": ParamType.FLOAT,
                "category": ParamCategory.YOLO_DETECTION,
                "description": "Minimum motion ratio required for small fire targets",
                "default_value": 0.08,
                "min_value": 0.0,
                "max_value": 1.0,
                "permission": ParamPermission.EDITABLE,
                "requires_restart": False
            },
            {
                "key": "fire_small_target_fire_ratio_min",
                "value": 0.10,
                "type": ParamType.FLOAT,
                "category": ParamCategory.YOLO_DETECTION,
                "description": "Minimum fire-color ratio required for small fire targets",
                "default_value": 0.10,
                "min_value": 0.0,
                "max_value": 1.0,
                "permission": ParamPermission.EDITABLE,
                "requires_restart": False
            },
            {
                "key": "fire_track_match_dist_px",
                "value": 80,
                "type": ParamType.INTEGER,
                "category": ParamCategory.YOLO_DETECTION,
                "description": "Max centroid distance (pixels) for fire track association",
                "default_value": 80,
                "min_value": 20,
                "max_value": 500,
                "permission": ParamPermission.EDITABLE,
                "requires_restart": False
            },
            {
                "key": "fire_track_min_iou",
                "value": 0.10,
                "type": ParamType.FLOAT,
                "category": ParamCategory.YOLO_DETECTION,
                "description": "Minimum IoU for fire track association",
                "default_value": 0.10,
                "min_value": 0.0,
                "max_value": 1.0,
                "permission": ParamPermission.EDITABLE,
                "requires_restart": False
            },
            {
                "key": "fire_track_area_change_max",
                "value": 2.0,
                "type": ParamType.FLOAT,
                "category": ParamCategory.YOLO_DETECTION,
                "description": "Maximum area ratio change allowed for fire track association",
                "default_value": 2.0,
                "min_value": 1.0,
                "max_value": 20.0,
                "permission": ParamPermission.EDITABLE,
                "requires_restart": False
            },
            {
                "key": "detection_interval",
                "value": 5,
                "type": ParamType.INTEGER,
                "category": ParamCategory.ALARM_LOGIC,
                "description": "检测间隔帧数",
                "default_value": 5,
                "min_value": 1,
                "max_value": 30,
                "permission": ParamPermission.EDITABLE,
                "requires_restart": False
            },
            {
                "key": "consecutive_threshold",
                "value": 5,
                "type": ParamType.INTEGER,
                "category": ParamCategory.ALARM_LOGIC,
                "description": "连续检测触发报警次数",
                "default_value": 5,
                "min_value": 1,
                "max_value": 50,
                "permission": ParamPermission.EDITABLE,
                "requires_restart": False
            },
            {
                "key": "alert_cooldown_seconds",
                "value": 180,
                "type": ParamType.INTEGER,
                "category": ParamCategory.ALARM_LOGIC,
                "description": "报警冷却时间（秒）",
                "default_value": 180,
                "min_value": 30,
                "max_value": 3600,
                "permission": ParamPermission.EDITABLE,
                "requires_restart": False
            },
            {
                "key": "confirm_wait_seconds",
                "value": 180,
                "type": ParamType.INTEGER,
                "category": ParamCategory.ALARM_LOGIC,
                "description": "确认等待时间（秒）",
                "default_value": 180,
                "min_value": 30,
                "max_value": 600,
                "permission": ParamPermission.EDITABLE,
                "requires_restart": False
            },
            # 硬件参数
            {
                "key": "yolo_device",
                "value": "cpu",
                "type": ParamType.STRING,
                "category": ParamCategory.HARDWARE,
                "description": "YOLO 推理设备",
                "default_value": "cpu",
                "options": ["cpu", "cuda", "cuda:0", "cuda:1"],
                "permission": ParamPermission.RESTRICTED,
                "requires_restart": True
            },
            {
                "key": "camera_index",
                "value": 0,
                "type": ParamType.INTEGER,
                "category": ParamCategory.HARDWARE,
                "description": "摄像头索引",
                "default_value": 0,
                "min_value": 0,
                "max_value": 10,
                "permission": ParamPermission.EDITABLE,
                "requires_restart": True
            },
            {
                "key": "rtsp_url",
                "value": "",
                "type": ParamType.STRING,
                "category": ParamCategory.HARDWARE,
                "description": "RTSP 流地址（为空时使用摄像头）",
                "permission": ParamPermission.EDITABLE,
                "requires_restart": True
            },
            # 后处理参数
            {
                "key": "min_box_area",
                "value": 500,
                "type": ParamType.INTEGER,
                "category": ParamCategory.YOLO_DETECTION,
                "description": "最小检测框面积（像素）",
                "default_value": 500,
                "min_value": 100,
                "max_value": 50000,
                "permission": ParamPermission.EDITABLE,
                "requires_restart": False
            },
            {
                "key": "max_box_area",
                "value": 500000,
                "type": ParamType.INTEGER,
                "category": ParamCategory.YOLO_DETECTION,
                "description": "最大检测框面积（像素）",
                "default_value": 500000,
                "min_value": 10000,
                "max_value": 5000000,
                "permission": ParamPermission.EDITABLE,
                "requires_restart": False
            }
        ]
        
        # 初始化配置文件
        config_data = self.storage.read(self.config_file)
        if not config_data:
            param_dict = {}
            for param in default_params:
                param_dict[param["key"]] = param
            self.storage.write(self.config_file, {"params": param_dict, "version": 1})
        
        # 初始化版本记录
        if not self.storage.read(self.versions_file):
            self.storage.write(self.versions_file, {"versions": []})
        
        # 初始化审计日志
        if not self.storage.read(self.audit_file):
            self.storage.write(self.audit_file, {"logs": []})
    
    def get_all_params(self, category: Optional[ParamCategory] = None) -> List[SystemParam]:
        """
        函数级注释：获取所有系统参数
        :param category: 参数分类，None 则返回所有
        :return: 参数列表
        """
        config_data = self.storage.read(self.config_file)
        if not config_data:
            return []
        
        params = []
        for param_data in config_data.get("params", {}).values():
            param = SystemParam(**param_data)
            if category is None or param.category == category:
                params.append(param)
        
        return params
    
    def get_param(self, key: str) -> Optional[SystemParam]:
        """
        函数级注释：获取单个参数
        :param key: 参数键名
        :return: 参数对象，不存在则返回 None
        """
        config_data = self.storage.read(self.config_file)
        if not config_data:
            return None
        
        param_data = config_data.get("params", {}).get(key)
        if not param_data:
            return None
        
        return SystemParam(**param_data)
    
    def update_params(self, update: SystemConfigUpdate, ip_address: Optional[str] = None) -> List[SystemParam]:
        """
        函数级注释：批量更新参数
        :param update: 更新请求
        :param ip_address: 操作人 IP
        :return: 更新后的参数列表
        """
        config_data = self.storage.read(self.config_file)
        if not config_data:
            raise ValueError("配置文件不存在")
        
        updated_params = []
        versions = []
        audit_logs = []
        
        for key, new_value in update.updates.items():
            param_data = config_data.get("params", {}).get(key)
            if not param_data:
                continue
            
            old_value = param_data.get("value")
            if old_value == new_value:
                continue
            
            param = SystemParam(**param_data)
            
            if param.permission == ParamPermission.READ_ONLY:
                continue
            
            # 记录版本
            version = ParamVersion(
                version_id=str(uuid.uuid4()),
                param_key=key,
                old_value=old_value,
                new_value=new_value,
                changed_by=update.operator,
                change_reason=update.change_reason
            )
            versions.append(version)
            
            # 记录审计日志
            audit_log = ParamAuditLog(
                log_id=str(uuid.uuid4()),
                action="update",
                param_key=key,
                old_value=old_value,
                new_value=new_value,
                operator=update.operator,
                ip_address=ip_address
            )
            audit_logs.append(audit_log)
            
            # 更新参数
            param.value = new_value
            param.updated_at = datetime.now()
            param.updated_by = update.operator
            config_data["params"][key] = safe_model_dump(param)
            updated_params.append(param)
        
        # 保存配置
        config_data["version"] = config_data.get("version", 1) + 1
        self.storage.write(self.config_file, config_data)
        
        # 保存版本记录
        versions_data = self.storage.read(self.versions_file) or {"versions": []}
        versions_data["versions"].extend([safe_model_dump(v) for v in versions])
        self.storage.write(self.versions_file, versions_data)
        
        # 保存审计日志
        audit_data = self.storage.read(self.audit_file) or {"logs": []}
        audit_data["logs"].extend([safe_model_dump(l) for l in audit_logs])
        self.storage.write(self.audit_file, audit_data)
        
        return updated_params
    
    def get_param_versions(self, param_key: str, limit: int = 20) -> List[ParamVersion]:
        """
        函数级注释：获取参数的历史版本
        :param param_key: 参数键名
        :param limit: 返回数量限制
        :return: 版本列表
        """
        versions_data = self.storage.read(self.versions_file) or {"versions": []}
        versions = []
        for v in versions_data.get("versions", []):
            if v.get("param_key") == param_key:
                versions.append(ParamVersion(**v))
        versions.sort(key=lambda x: x.changed_at, reverse=True)
        return versions[:limit]
    
    def get_audit_logs(self, limit: int = 100) -> List[ParamAuditLog]:
        """
        函数级注释：获取审计日志
        :param limit: 返回数量限制
        :return: 审计日志列表
        """
        audit_data = self.storage.read(self.audit_file) or {"logs": []}
        logs = [ParamAuditLog(**l) for l in audit_data.get("logs", [])]
        logs.sort(key=lambda x: x.timestamp, reverse=True)
        return logs[:limit]
    
    def export_config(self) -> Dict[str, Any]:
        """
        函数级注释：导出配置
        :return: 配置字典
        """
        config_data = self.storage.read(self.config_file)
        return config_data or {}
    
    def import_config(self, config_data: Dict[str, Any], operator: Optional[str] = None, ip_address: Optional[str] = None):
        """
        函数级注释：导入配置
        :param config_data: 配置数据
        :param operator: 操作人
        :param ip_address: IP 地址
        """
        self.storage.write(self.config_file, config_data)
        
        audit_log = ParamAuditLog(
            log_id=str(uuid.uuid4()),
            action="import",
            operator=operator,
            ip_address=ip_address
        )
        audit_data = self.storage.read(self.audit_file) or {"logs": []}
        audit_data["logs"].append(safe_model_dump(audit_log))
        self.storage.write(self.audit_file, audit_data)
    
    def rollback_param(self, param_key: str, version_id: str, operator: Optional[str] = None) -> Optional[SystemParam]:
        """
        函数级注释：回滚参数到指定版本
        :param param_key: 参数键名
        :param version_id: 版本 ID
        :param operator: 操作人
        :return: 回滚后的参数
        """
        versions_data = self.storage.read(self.versions_file) or {"versions": []}
        target_version = None
        for v in versions_data.get("versions", []):
            if v.get("version_id") == version_id and v.get("param_key") == param_key:
                target_version = ParamVersion(**v)
                break
        
        if not target_version:
            return None
        
        config_data = self.storage.read(self.config_file)
        if not config_data or param_key not in config_data.get("params", {}):
            return None
        
        param_data = config_data["params"][param_key]
        old_value = param_data.get("value")
        
        param = SystemParam(**param_data)
        param.value = target_version.old_value
        param.updated_at = datetime.now()
        param.updated_by = operator
        
        config_data["params"][param_key] = safe_model_dump(param)
        config_data["version"] = config_data.get("version", 1) + 1
        self.storage.write(self.config_file, config_data)
        
        version = ParamVersion(
            version_id=str(uuid.uuid4()),
            param_key=param_key,
            old_value=old_value,
            new_value=target_version.old_value,
            changed_by=operator,
            change_reason="回滚操作"
        )
        versions_data["versions"].append(safe_model_dump(version))
        self.storage.write(self.versions_file, versions_data)
        
        audit_log = ParamAuditLog(
            log_id=str(uuid.uuid4()),
            action="update",
            param_key=param_key,
            old_value=old_value,
            new_value=target_version.old_value,
            operator=operator
        )
        audit_data = self.storage.read(self.audit_file) or {"logs": []}
        audit_data["logs"].append(safe_model_dump(audit_log))
        self.storage.write(self.audit_file, audit_data)
        
        return param


# 全局服务实例
_system_param_service: Optional[SystemParamService] = None


def get_system_param_service() -> SystemParamService:
    """
    函数级注释：获取系统参数服务实例（单例模式）
    """
    global _system_param_service
    if _system_param_service is None:
        _system_param_service = SystemParamService()
    return _system_param_service
