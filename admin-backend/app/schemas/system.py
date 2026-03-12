"""
类级注释：系统参数管理数据验证模式
定义系统参数配置的数据结构、分类和版本控制
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum


class ParamType(str, Enum):
    """
    类级注释：参数类型枚举
    """
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"


class ParamCategory(str, Enum):
    """
    类级注释：参数分类枚举
    """
    YOLO_DETECTION = "yolo_detection"
    ALARM_LOGIC = "alarm_logic"
    HARDWARE = "hardware"
    GENERAL = "general"


class ParamPermission(str, Enum):
    """
    类级注释：参数权限级别
    """
    READ_ONLY = "read_only"
    EDITABLE = "editable"
    RESTRICTED = "restricted"


class SystemParam(BaseModel):
    """
    类级注释：系统参数模型
    """
    key: str = Field(..., description="参数键名")
    value: Any = Field(..., description="参数值")
    type: ParamType = Field(..., description="参数类型")
    category: ParamCategory = Field(..., description="参数分类")
    description: str = Field("", description="参数描述")
    default_value: Any = Field(None, description="默认值")
    min_value: Optional[float] = Field(None, description="最小值（数值类型）")
    max_value: Optional[float] = Field(None, description="最大值（数值类型）")
    options: Optional[List[Any]] = Field(None, description="可选值列表")
    permission: ParamPermission = Field(ParamPermission.EDITABLE, description="权限级别")
    requires_restart: bool = Field(False, description="是否需要重启才能生效")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    updated_by: Optional[str] = Field(None, description="最后修改人")
    
    @field_validator('value')
    def validate_value_type(cls, v, info):
        """
        函数级注释：验证参数值类型
        """
        param_type = info.data.get('type')
        if param_type == ParamType.INTEGER:
            if not isinstance(v, int):
                raise ValueError(f"参数值必须为整数类型，当前类型: {type(v)}")
        elif param_type == ParamType.FLOAT:
            if not isinstance(v, (int, float)):
                raise ValueError(f"参数值必须为数值类型，当前类型: {type(v)}")
        elif param_type == ParamType.BOOLEAN:
            if not isinstance(v, bool):
                raise ValueError(f"参数值必须为布尔类型，当前类型: {type(v)}")
        return v
    
    @field_validator('value')
    def validate_value_range(cls, v, info):
        """
        函数级注释：验证参数值范围
        """
        min_val = info.data.get('min_value')
        max_val = info.data.get('max_value')
        
        if isinstance(v, (int, float)):
            if min_val is not None and v < min_val:
                raise ValueError(f"参数值不能小于 {min_val}")
            if max_val is not None and v > max_val:
                raise ValueError(f"参数值不能大于 {max_val}")
        
        return v
    
    @field_validator('value')
    def validate_value_options(cls, v, info):
        """
        函数级注释：验证参数值是否在可选列表中
        """
        options = info.data.get('options')
        if options and v not in options:
            raise ValueError(f"参数值必须是以下之一: {options}")
        return v


class ParamVersion(BaseModel):
    """
    类级注释：参数版本记录
    """
    version_id: str = Field(..., description="版本ID")
    param_key: str = Field(..., description="参数键名")
    old_value: Any = Field(None, description="旧值")
    new_value: Any = Field(..., description="新值")
    changed_at: datetime = Field(default_factory=datetime.now)
    changed_by: Optional[str] = Field(None, description="修改人")
    change_reason: Optional[str] = Field(None, description="修改原因")


class ParamAuditLog(BaseModel):
    """
    类级注释：参数审计日志
    """
    log_id: str = Field(..., description="日志ID")
    action: str = Field(..., description="操作类型: create, update, delete, import, export")
    param_key: Optional[str] = Field(None, description="参数键名")
    old_value: Any = Field(None, description="旧值")
    new_value: Any = Field(None, description="新值")
    operator: Optional[str] = Field(None, description="操作人")
    timestamp: datetime = Field(default_factory=datetime.now)
    ip_address: Optional[str] = Field(None, description="IP地址")


class SystemConfigUpdate(BaseModel):
    """
    类级注释：系统配置更新请求
    """
    updates: Dict[str, Any] = Field(..., description="参数更新字典 {key: value}")
    change_reason: Optional[str] = Field(None, description="修改原因")
    operator: Optional[str] = Field(None, description="操作人")


class SystemConfigResponse(BaseModel):
    """
    类级注释：系统配置响应
    """
    params: List[SystemParam] = Field(..., description="参数列表")
    total_count: int = Field(..., description="总参数数量")
    last_updated: Optional[datetime] = Field(None, description="最后更新时间")


class VersionCompareResponse(BaseModel):
    """
    类级注释：版本对比响应
    """
    param_key: str = Field(..., description="参数键名")
    version1: ParamVersion = Field(..., description="版本1")
    version2: ParamVersion = Field(..., description="版本2")
    diff: Dict[str, Any] = Field(..., description="差异对比")
