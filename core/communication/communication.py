import threading
import time
import logging
from core.communication.feishu import FeishuNotifier
from core.communication.aliyun import AliyunNotifier  # 导入新模块


def get_sms_phones():
    # 这里返回需要接收短信的管理员手机号列表
    return ["13800138000", "13900139000"]  # 示例手机号列表


class Communication:

    def __init__(self):
        self.logger = logging.getLogger("Communication")
        self.aliyun = AliyunNotifier()  # 初始化阿里云
        self.notifier = FeishuNotifier()

    def run_fire_alarm_process_feishu(self, image_path):
        self.logger.info(f"🔥 [线程启动] 执行群聊报警流程...")
        start_time = time.time()

        # 1. 发送群消息
        self.logger.info("Step 1: 发送群卡片...")
        msg_id = self.notifier.send_card_to_group(
            title="实验室火灾警报",
            content="检测到明火！请成员立即检查!!。",
            image_path=image_path
        )

        if not msg_id:
            self.logger.error("❌ 致命错误：群消息发送失败，无法进行后续加急")
            return

        sms_params = {
            "time": time.strftime("%H:%M")
        }

        self.aliyun.send_sms_to_all(sms_params)

        # 2. 短信加急 (Buzz)
        # 虽然消息在群里，但我们可以指定“只提醒这几个管理员”
        if self.notifier.admin_ids:
            self.logger.info(f"Step 2: 对 {len(self.notifier.admin_ids)} 位管理员发起 [短信] 加急...")
            self.notifier.buzz_message(msg_id, self.notifier.admin_ids, urgent_type="sms")
        else:
            self.logger.info("⚠️ 无管理员 ID，跳过加急")

        # 3. 等待回复 (3分钟)
        wait_seconds = 180
        is_confirmed = False
        self.logger.info(f"Step 3: 等待群回复 (限时 {wait_seconds} 秒)...")

        for i in range(wait_seconds // 5):
            if self.notifier.check_chat_reply(start_time):
                is_confirmed = True
                break
            time.sleep(5)

        # 4. 结果判断
        if is_confirmed:
            self.logger.info("✅ 警报解除：管理员已在群内响应。")
            # 可选：再发一条群消息告知大家
            # notifier.send_card_to_group("警报解除", "管理员已确认。")
        else:
            self.logger.info("⚠️ 超时未回复！")
            self.logger.info("Step 4: 升级为 [电话] 加急报警！")

            # 对同一条消息发起电话加急 (或者你可以发一条新的再加急)
            if self.notifier.admin_ids:
                self.notifier.buzz_message(msg_id, self.notifier.admin_ids, urgent_type="phone")

    def test_logging_notification(self, phone_number="18903690733", image_path=None):
        """
        测试日志功能的通知方法
        只发送短信和飞书管理员通知，不发送群聊消息
        :param phone_number: 接收通知的手机号，默认为 18903690733
        :param image_path: 图片路径（可选）
        """
        self.logger.info("=" * 50)
        self.logger.info("🧪 [测试模式] 开始测试日志通知功能...")
        self.logger.info(f"📱 目标手机号: {phone_number}")
        
        # 1. 发送短信通知
        self.logger.info("Step 1: 发送短信通知...")
        sms_params = {
            "time": time.strftime("%H:%M")
        }
        sms_result = self.aliyun.send_sms([phone_number], sms_params)
        if sms_result:
            self.logger.info("✅ 短信发送成功")
        else:
            self.logger.error("❌ 短信发送失败")
        
        # 2. 获取用户的飞书 open_id
        self.logger.info("Step 2: 通过手机号获取飞书用户ID...")
        feishu_test_phone = "+8618903690733"  # 飞书手机号格式，注意加国家码
        user_open_id = self.notifier.get_open_id_by_mobile(feishu_test_phone)
        
        if not user_open_id:
            self.logger.error("❌ 无法获取用户飞书ID，跳过飞书通知")
            self.logger.info("=" * 50)
            return
        
        self.logger.info(f"✅ 成功获取用户ID: {user_open_id}")
        
        # 3. 发送飞书消息给该用户
        self.logger.info("Step 3: 发送飞书消息给用户...")
        msg_id = self.notifier.send_card_to_user(
            user_open_id=user_open_id,
            title="【测试】日志功能测试通知",
            content="这是一条测试消息，用于测试日志功能。如果您收到此消息，说明日志和通知功能正常工作。",
            image_path=image_path
        )
        
        if msg_id:
            self.logger.info(f"✅ 飞书消息发送成功，消息ID: {msg_id}")
        else:
            self.logger.error("❌ 飞书消息发送失败")
        
        self.logger.info("=" * 50)
        self.logger.info("🎉 测试完成！")
