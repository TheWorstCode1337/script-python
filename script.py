import asyncio
import datetime
from telethon import TelegramClient, events, functions
from telethon.errors import FloodWaitError, RPCError

#----- Const --------
api_id = 12345678 # here your api id
api_hash = ''
session_name = 'session_autoread'
KEEPONLINE_INTERVAL = 45
#--------------------

#-------Day Setting --------
DAY_START = 8
DAY_END = 23

def is_day() -> bool:
    hour = datetime.datetime.now().hour
    return DAY_START <= hour < DAY_END
#---------------------------

client = TelegramClient(session_name, api_id, api_hash)
stop_request = False
async def keep_online_task():
    if not is_day():
        return
    else:
        global stop_request
        while not stop_request:
            try:
                await client(functions.account.UpdateStatusRequest(offline=False))
            except FloodWaitError as e:
                print(f'FloodWait: ждать {e.seconds}c.')
                await asyncio.sleep(e.seconds + 1)
            except RPCError as e:
                print('RPCError при UpdateStatus:', e)
            except Exception as e:
                print('Ошибка в keep_online:', e)
            await asyncio.sleep(KEEPONLINE_INTERVAL)

@client.on(events.NewMessage(incoming=True))
async def auto_mark_read(event):
    if not is_day():
        return
    else:
        try:
            await event.mark_read()
            print(f'Прочитано: {event.sender_id} -> {event.chat_id} (msg_id={event.message.id})')
        except FloodWaitError as e:
            print('FloodWaitError при чтении, ждать', e.seconds)
            await asyncio.sleep(e.seconds + 1)
        except Exception as e:
            print('Ошибка при пометке:', e)

async def on_startup():
    asyncio.create_task(keep_online_task())

async def main():
    await client.start()
    print('Клиент запущен: ID:', (await client.get_me()).id)
    try:
        await client(functions.account.UpdateStatusRequest(offline=False))
    except Exception:
        pass
    await on_startup()
    
    while not stop_request:
        await asyncio.sleep(1)
    try:
        await client(functions.account.UpdateStatusRequest(offline=True))
    except Exception:
        pass
    await client.disconnect()
    print('Отключено')
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Остановлено пользователем.')