"""
类级注释：系统参数管理模块
提供从 system.json 读取和监听系统参数的功能，支持热更新回调
"""
import logging
from typing import Any, Optional, Callable
from pathlib import Path

from .config_hot_loader import ConfigHotLoader


class SystemConfig:
    """
    类级注释：系统参数管理类
    提供系统参数的读取、监听和热更新回调机制
    """
    
    def __init__(self, config_loader: Optional[ConfigHotLoader] = None):
        """
        函数级注释：初始化系统参数管理
        :param config_loader: 配置热加载器实例
        """
        self.logger = logging.getLogger("SystemConfig")
        self.config_loader = config_loader or ConfigHotLoader()
        
        # 注册配置变更回调
        self.config_loader.register_change_callback(self._on_config_change)
        
        # 缓存当前参数
        self._current_params = {}
        self._change_callbacks: list = []
        self._load_current_params()
        
        self.logger.info("系统参数管理初始化完成")
    
    def _load_current_params(self):
        """
        函数级注释：加载当前所有系统参数到缓存
        """
        all_keys = [
            "yolo_weights",
            "yolo_confidence",
            "yolo_iou_threshold",
            "yolo_imgsz",
            "yolo_device",
            "fire_small_area_threshold",
            "fire_medium_area_threshold",
            "fire_small_target_motion_min",
            "fire_small_target_fire_ratio_min",
            "fire_track_match_dist_px",
            "fire_track_min_iou",
            "fire_track_area_change_max",
            "detection_interval",
            "consecutive_threshold",
            "alert_cooldown_seconds",
            "confirm_wait_seconds",
            "camera_index",
            "rtsp_url",
            "min_box_area",
            "max_box_area"
        ]
        
        for key in all_keys:
            value = self.config_loader.get_config(key)
            if value is not None:
                self._current_params[key] = value
    
    def _on_config_change(self):
        """
        函数级注释：配置变更时的回调处理
        """
        old_params = self._current_params.copy()
        self._load_current_params()
        
        changed_params = {}
        
        for key, new_val in self._current_params.items():
            old_val = old_params.get(key)
            if old_val != new_val:
                changed_params[key] = {"old": old_val, "new": new_val}
                self.logger.info(f"参数变更: {key} = {old_val} -> {new_val}")
        
        if changed_params:
            self._notify_callbacks(changed_params)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        函数级注释：获取系统参数
        :param key: 参数键名
        :param default: 默认值
        :return: 参数值
        """
        return self._current_params.get(key, default)
    
    def register_change_callback(self, callback: Callable[[dict], None]):
        """
        函数级注释：注册参数变更回调
        :param callback: 回调函数，接收变更参数变更字典 {key: {"old": val, "new": val}
        """
        if callback not in self._change_callbacks:
            self._change_callbacks.append(callback)
            self.logger.debug(f"注册回调已注册: {callback.__name__}")
    
    def unregister_change_callback(self, callback: Callable[[dict], None]):
        """
        函数级注释：注销参数变更回调
        :param callback: 回调函数
        """
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)
            self.logger.debug(f"回调已注销: {callback.__name__}")
    
    def _notify_callbacks(self, changed_params: dict):
        """
        函数级注释：通知所有变更回调
        :param changed_params: 变更参数字典
        """
        for callback in self._change_callbacks:
            try:
                callback(changed_params)
            except Exception as e:
                self.logger.error(f"执行回调失败: {e}")
    
    def get_yolo_confidence(self) -> float:
        """
        函数级注释：获取 YOLO 置信度
        :return: 置信度阈值
        """
        return self.get("yolo_confidence", 0.5)
    
    def get_consecutive_threshold(self) -> int:
        """
        函数级注释：获取连续检测阈值
        :return: 连续检测次数
        """
        return self.get("consecutive_threshold", 5)
    
    def get_alert_cooldown_seconds(self) -> int:
        """
        函数级注释：获取报警冷却时间
        :return: 冷却时间（秒）
        """
        return self.get("alert_cooldown_seconds", 180)
    
    def get_confirm_wait_seconds(self) -> int:
        """
        函数级注释：获取确认等待时间
        :return: 等待时间（秒）
        """
        return self.get("confirm_wait_seconds", 180)
    
    def get_detection_interval(self) -> int:
        """
        函数级注释：获取检测间隔帧数
        :return: 检测间隔
        """
        return self.get("detection_interval", 5)
    
    def get_yolo_iou_threshold(self) -> float:
        """
        函数级注释：获取 YOLO IOU 阈值
        :return: IOU 阈值
        """
        return self.get("yolo_iou_threshold", 0.45)
    
    def get_yolo_device(self) -> str:
        """
        函数级注释：获取 YOLO 推理设备
        :return: 设备名称
        """
        return self.get("yolo_device", "cpu")
    
    def get_camera_index(self) -> int:
        """
        函数级注释：获取摄像头索引
        :return: 摄像头索引
        """
        return self.get("camera_index", 0)
    
    def get_rtsp_url(self) -> str:
        """
        函数级注释：获取 RTSP 流地址
        :return: RTSP 地址
        """
        return self.get("rtsp_url", "")
    
    def get_min_box_area(self) -> int:
        """
        函数级注释：获取最小检测框面积
        :return: 最小面积
        """
        return self.get("min_box_area", 500)
    
    def get_max_box_area(self) -> int:
        """
        函数级注释：获取最大检测框面积
        :return: 最大面积
        """
        return self.get("max_box_area", 500000)


# 全局系统配置单例
_system_config: Optional[SystemConfig] = None


def get_system_config() -> SystemConfig:
    """
    函数级注释：获取系统配置实例（单例模式）
    :return: 系统配置实例
    """
    global _system_config
    if _system_config is None:
        _system_config = SystemConfig()
    return _system_config
