"""
类级注释：通信模块（支持配置热加载）
负责火灾报警时的飞书和短信通知流程
"""
import threading
import time
import logging

from core.communication.feishu import FeishuNotifier
from core.communication.aliyun import AliyunNotifier
from core.communication.config_hot_loader import get_config_hot_loader


class Communication:
    """
    类级注释：通信模块
    """
    
    def __init__(self):
        self.logger = logging.getLogger("Communication")
        
        # 初始化配置热加载器
        self.config_loader = get_config_hot_loader()
        
        # 初始化通知器
        self.aliyun = AliyunNotifier()
        self.notifier = FeishuNotifier()
        
        self.logger.info("通信模块初始化完成")
    
    def run_fire_alarm_process_feishu(self, image_path):
        """
        函数级注释：执行火灾报警流程
        """
        self.logger.info(f"🔥 [线程启动] 执行群聊报警流程...")
        start_time = time.time()
        
        # 获取报警冷却时间配置
        alert_cooldown = self.config_loader.get_config('alert_cooldown_seconds', 180)
        confirm_wait = self.config_loader.get_config('confirm_wait_seconds', 180)
        
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
        
        # 发送短信给所有短信接收人
        sms_params = {
            "time": time.strftime("%H:%M")
        }
        self.aliyun.send_sms_to_all(sms_params)
        
        # 2. 短信加急 (Buzz)
        admin_ids = self.notifier.admin_ids
        if admin_ids:
            self.logger.info(f"Step 2: 对 {len(admin_ids)} 位管理员发起 [短信] 加急...")
            self.notifier.buzz_message(msg_id, admin_ids, urgent_type="sms")
        else:
            self.logger.info("⚠️ 无管理员 ID，跳过加急")
        
        # 3. 等待回复
        wait_seconds = confirm_wait
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
        else:
            self.logger.info("⚠️ 超时未回复！")
            self.logger.info("Step 4: 升级为 [电话] 加急报警！")
            
            if admin_ids:
                self.notifier.buzz_message(msg_id, admin_ids, urgent_type="phone")
    
    def test_logging_notification(self, phone_number="18903690733", image_path=None):
        """
        函数级注释：测试日志通知功能
        只发送短信和飞书管理员通知
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
        feishu_test_phone = "+8618903690733"
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
