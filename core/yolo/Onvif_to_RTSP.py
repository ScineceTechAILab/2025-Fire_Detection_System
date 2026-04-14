import sys
import os
import onvif
from onvif import ONVIFCamera


def analysis_rtsp(ip, port, username, password):
    # 寻找 Python 环境里 python-onvif-zeep 库自带的说明书文件（WSDL 文件）
    possible_wsdl_dirs = [
        os.path.join(os.path.dirname(onvif.__file__), "wsdl"),
        "/usr/local/lib/python3.10/site-packages/wsdl",
        "/app/wsdl"
    ]

    wsdl_dir = None
    for d in possible_wsdl_dirs:
        if os.path.exists(os.path.join(d, "devicemgmt.wsdl")):
            wsdl_dir = d
            break

    if not wsdl_dir:
        # 如果实在找不到，报错信息会告诉你搜过哪里
        raise RuntimeError(f"未找到 WSDL 文件: {possible_wsdl_dirs}")
    # 初始化摄像头对象
    cam = ONVIFCamera(ip, port, username, password, wsdl_dir)
    # 创建一个媒体服务实例
    media_service = cam.create_media_service()
    # 获取摄像头配置档位列表
    profiles = media_service.GetProfiles()

    # 遍历每个配置档，对每一个配置档请求播放地址
    for idx, profile in enumerate(profiles):
        req = media_service.create_type("GetStreamUri")
        req.StreamSetup = {"Stream": "RTP-Unicast", "Transport": {"Protocol": "RTSP"}}
        req.ProfileToken = profile.token
        uri_obj = media_service.GetStreamUri(req)

        raw_uri = uri_obj.Uri
        # 把 "rtsp://" 替换成 "rtsp://username:password@"
        auth_uri = raw_uri.replace("rtsp://", f"rtsp://{username}:{password}@")
        return auth_uri
    raise RuntimeError("未获取到可用的 ONVIF RTSP 地址")


if __name__ == "__main__":
    analysis_rtsp(
        ip="192.168.31.94",
        port=8080,
        username="admin",
        password="Qq12345678",
    )
