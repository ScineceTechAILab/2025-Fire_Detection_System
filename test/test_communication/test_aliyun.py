import time

from core.communication.aliyun import AliyunNotifier


def test_send_sms():
    notifier = AliyunNotifier()

    # 假设你的模板变量是 ${code} 和 ${product}
    # 如果你的模板没有变量，params 传 {} 或者 None 即可
    test_params = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    result = notifier.send_sms_to_all(params=test_params)

    assert result is True
