### Модуль для отправки уведомлений владельцу бота
##"""
##Модуль для отправки уведомлений владельцу бота
##"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import os
from pathlib import Path

# Настройка логирования
logger = logging.getLogger(__name__)


class NotificationManager:
    """Менеджер уведомлений для отправки запросов владельцу"""
    
    def __init__(self, owner_telegram_id: Optional[str] = None, owner_email: Optional[str] = None):
        """
        Инициализация менеджера уведомлений
        
        Args:
            owner_telegram_id: Telegram ID владельца для отправки сообщений
            owner_email: Email владельца для отправки уведомлений
        """
        self.owner_telegram_id = owner_telegram_id
        self.owner_email = owner_email
        self.notifications_log_file = Path("notifications_log.json")
        self._ensure_log_file()
    
    def _ensure_log_file(self):
        """Создает файл лога уведомлений, если он не существует"""
        if not self.notifications_log_file.exists():
            initial_data = {
                "notifications": [],
                "settings": {
                    "telegram_enabled": self.owner_telegram_id is not None,
                    "email_enabled": False,  # Пока не реализовано
                    "created_at": datetime.now().isoformat()
                }
            }
            import json
            self.notifications_log_file.write_text(json.dumps(initial_data, ensure_ascii=False, indent=2))
    
    async def send_to_owner(
        self, 
        message: str, 
        user_info: Dict[str, Any],
        bot_instance = None,
        notification_type: str = "user_question"
    ) -> Dict[str, Any]:
        """
        Основной метод отправки уведомления владельцу
        
        Args:
            message: Текст сообщения от пользователя
            user_info: Информация о пользователе (id, username, first_name, last_name)
            bot_instance: Экземпляр бота для отправки Telegram сообщений
            notification_type: Тип уведомления (user_question, feedback, etc.)
            
        Returns:
            Словарь с результатами отправки
        """
        results = {
            "telegram_sent": False,
            "email_sent": False,
            "logged": False,
            "errors": []
        }
        
        # Логируем уведомление
        log_result = self._log_notification(message, user_info, notification_type)
        results["logged"] = log_result["success"]
        if not log_result["success"]:
            results["errors"].append(f"Log error: {log_result.get('error')}")
        
        # Отправляем в Telegram, если есть ID владельца и экземпляр бота
        if self.owner_telegram_id and bot_instance:
            telegram_result = await self._send_telegram_notification(
                message, user_info, bot_instance, notification_type
            )
            results["telegram_sent"] = telegram_result["success"]
            if not telegram_result["success"]:
                results["errors"].append(f"Telegram error: {telegram_result.get('error')}")
        
        # TODO: Добавить отправку на email
        # if self.owner_email:
        #     email_result = await self._send_email_notification(message, user_info, notification_type)
        #     results["email_sent"] = email_result["success"]
        
        return results
    
    async def _send_telegram_notification(
        self, 
        message: str, 
        user_info: Dict[str, Any],
        bot_instance,
        notification_type: str
    ) -> Dict[str, Any]:
        """Отправляет уведомление владельцу в Telegram"""
        try:
            # Форматируем сообщение для владельца
            formatted_message = self._format_notification_message(message, user_info, notification_type)
            
            # Отправляем сообщение
            await bot_instance.send_message(
                chat_id=self.owner_telegram_id,
                text=formatted_message,
                parse_mode="HTML"
            )
            
            logger.info(f"Notification sent to owner (Telegram ID: {self.owner_telegram_id})")
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {type(e).__name__}")
            return {"success": False, "error": str(e)}
    
    def _format_notification_message(
        self, 
        message: str, 
        user_info: Dict[str, Any],
        notification_type: str
    ) -> str:
        """Форматирует сообщение для отправки владельцу"""
        user_id = user_info.get('id', 'N/A')
        username = user_info.get('username', 'N/A')
        first_name = user_info.get('first_name', 'N/A')
        last_name = user_info.get('last_name', 'N/A')
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        notification_types = {
            "user_question": "❓ ВОПРОС ОТ ПОЛЬЗОВАТЕЛЯ",
            "feedback": "📝 ОБРАТНАЯ СВЯЗЬ",
            "urgent": "🚨 СРОЧНОЕ УВЕДОМЛЕНИЕ"
        }
        
        header = notification_types.get(notification_type, "📨 УВЕДОМЛЕНИЕ")
        
        formatted = f"""<b>{header}</b>

👤 <b>Пользователь:</b>
ID: {user_id}
Username: @{username}
Имя: {first_name}
Фамилия: {last_name}

💬 <b>Сообщение:</b>
{message}

⏰ <b>Время:</b> {timestamp}
"""
        return formatted
    
    def _log_notification(
        self, 
        message: str, 
        user_info: Dict[str, Any],
        notification_type: str
    ) -> Dict[str, Any]:
        """Логирует уведомление в JSON файл"""
        try:
            import json
            from datetime import datetime
            
            # Читаем существующие данные
            if self.notifications_log_file.exists():
                data = json.loads(self.notifications_log_file.read_text())
            else:
                data = {"notifications": []}
            
            # Создаем новую запись
            notification = {
                "id": len(data["notifications"]) + 1,
                "timestamp": datetime.now().isoformat(),
                "type": notification_type,
                "user_info": user_info,
                "message": message,
                "status": "pending"  # pending, reviewed, responded, archived
            }
            
            # Добавляем в лог (сохраняем последние 100 уведомлений)
            data["notifications"].append(notification)
            if len(data["notifications"]) > 100:
                data["notifications"] = data["notifications"][-100:]
            
            # Сохраняем
            self.notifications_log_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2)
            )
            
            return {"success": True, "notification_id": notification["id"]}
            
        except Exception as e:
            logger.error(f"Failed to log notification: {type(e).__name__}")
            return {"success": False, "error": str(e)}
    
    def get_pending_notifications(self) -> list:
        """Возвращает список ожидающих уведомлений"""
        try:
            import json
            if self.notifications_log_file.exists():
                data = json.loads(self.notifications_log_file.read_text())
                return [n for n in data["notifications"] if n.get("status") == "pending"]
            return []
        except Exception as e:
            logger.error(f"Failed to get pending notifications: {type(e).__name__}")
            return []
    
    def mark_notification_as_reviewed(self, notification_id: int) -> bool:
        """Отмечает уведомление как просмотренное"""
        try:
            import json
            if self.notifications_log_file.exists():
                data = json.loads(self.notifications_log_file.read_text())
                
                for notification in data["notifications"]:
                    if notification.get("id") == notification_id:
                        notification["status"] = "reviewed"
                        notification["reviewed_at"] = datetime.now().isoformat()
                        
                        self.notifications_log_file.write_text(
                            json.dumps(data, ensure_ascii=False, indent=2)
                        )
                        return True
            return False
        except Exception as e:
            logger.error(f"Failed to mark notification as reviewed: {type(e).__name__}")
            return False


# Фабричная функция для удобного создания менеджера
def create_notification_manager():
    """Создает экземпляр менеджера уведомлений из переменных окружения"""
    from dotenv import load_dotenv
    load_dotenv()
    
    owner_telegram_id = os.getenv("OWNER_TELEGRAM_ID")
    owner_email = os.getenv("OWNER_EMAIL")
    
    return NotificationManager(
        owner_telegram_id=owner_telegram_id,
        owner_email=owner_email
    )