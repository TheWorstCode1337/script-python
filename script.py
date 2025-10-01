import asyncio
import datetime
import logging
from telethon import TelegramClient, events, functions
from telethon.errors import FloodWaitError, RPCError

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("telegram_bot.log")]
)
logger = logging.getLogger(__name__)

# Константы
API_ID = 12345678
API_HASH = 'your-api-hash'
SESSION_NAME = 'session_autoread'
KEEPONLINE_INTERVAL = 45
DAY_START = 8
DAY_END = 23

# Глобальный флаг для остановки
stop_request = False

#---------- Day Settings ------------
def is_day() -> bool:
    """Проверяет, находится ли текущее время в дневном диапазоне (8:00–23:00)."""
    hour = datetime.datetime.now().hour
    return DAY_START <= hour < DAY_END
#------------------------------------

async def keep_online_task(client: TelegramClient):
    """Поддерживает статус 'онлайн' в дневное время с заданным интервалом."""
    global stop_request
    while not stop_request:
        try:
            if not client.is_connected():
                logger.warning("Клиент не подключен, попытка переподключения...")
                await client.connect()
            offline = not is_day()
            await client(functions.account.UpdateStatusRequest(offline=offline))
            logger.debug(f"Статус обновлен: {'offline' if offline else 'online'}")
        except FloodWaitError as e:
            logger.warning(f"FloodWait: ожидание {e.seconds} секунд")
            await asyncio.sleep(e.seconds + 1)
        except RPCError as e:
            logger.error(f"RPCError при обновлении статуса: {e}")
        except Exception as e:
            logger.error(f"Ошибка в keep_online_task: {e}")
        await asyncio.sleep(KEEPONLINE_INTERVAL)

@events.register(events.NewMessage(incoming=True, func=lambda x: not x.via_bot))
async def auto_mark_read(event):
    if not is_day():
        return
    try:
        await event.mark_read()
        logger.info(f"Прочитано: {event.sender_id} -> {event.chat_id} (msg_id={event.message.id})")
    except FloodWaitError as e:
        logger.warning(f"FloodWaitError при чтении, ожидание {e.seconds} секунд")
        await asyncio.sleep(e.seconds + 1)
    except Exception as e:
        logger.error(f"Ошибка при пометке сообщения: {e}")

async def main():
    global stop_request
    stop_request = False
    
    # Инициализация клиента
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    client.add_event_handler(auto_mark_read, events.NewMessage)
    
    try:
        await client.start()
        user = await client.get_me()
        logger.info(f"Клиент запущен: ID {user.id}, username @{user.username}")
        
        # Установить статус "онлайн" при старте
        try:
            await client(functions.account.UpdateStatusRequest(offline=False))
            logger.debug("Начальный статус установлен: online")
        except Exception as e:
            logger.error(f"Ошибка при установке начального статуса: {e}")
        
        # Запуск задачи обновления статуса
        asyncio.create_task(keep_online_task(client))
        
        # Ожидание завершения
        while not stop_request:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Остановлено пользователем")
        stop_request = True
    except Exception as e:
        logger.error(f"Ошибка в main: {e}")
    finally:
        # Установить статус "оффлайн" при завершении
        try:
            if client.is_connected():
                await client(functions.account.UpdateStatusRequest(offline=True))
                logger.debug("Статус установлен: offline")
        except Exception as e:
            logger.error(f"Ошибка при установке статуса offline: {e}")
        await client.disconnect()
        logger.info("Клиент отключен")

if __name__ == '__main__':
    asyncio.run(main())