import discord
import os
import json
import re
import random
from discord.ext import tasks

# Замените на токен вашего бота
TOKEN = 'TOKEN'
MEMORY_DIR = 'memory'
PHRASE_LIBRARY_FILE = os.path.join(MEMORY_DIR, "phrase_library.json")
USER_ACCESS_FILE = os.path.join(MEMORY_DIR, "user_access.json")

# Фиксированные ID
ADMIN_ID = 890591440617472081
USER_1_ID = 799612290193424435

# Таблица уровней доступа в числовом представлении для сравнения
clearance_levels = {
    "Admin": 6,
    "User_1": 5,
    "UserD3": 4,
    "UserD2": 3,
    "UserD1": 2,
    "Null_": 0
}

# Глобальные словари
user_access = {}      # хранение уровней доступа пользователей
phrase_library = []   # библиотека фраз

def ensure_memory_dir():
    """Проверка и создание каталога для хранения файлов памяти."""
    if not os.path.exists(MEMORY_DIR):
        os.makedirs(MEMORY_DIR)

def load_user_access():
    """Загружает информацию о пользователях из файла или создаёт базовый словарь."""
    global user_access
    if os.path.exists(USER_ACCESS_FILE):
        try:
            with open(USER_ACCESS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                user_access = {int(k): v for k, v in data.items()}
        except Exception as e:
            print("Ошибка загрузки user_access:", e)
            user_access = {}
    # Фиксируем всегда Admin и User_1
    user_access[ADMIN_ID] = "Admin"
    user_access[USER_1_ID] = "User_1"
    save_user_access()

def save_user_access():
    """Сохраняет глобальный словарь user_access в файл."""
    try:
        with open(USER_ACCESS_FILE, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in user_access.items()}, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print("Ошибка сохранения user_access:", e)

def load_phrase_library():
    """Загружает библиотеку фраз из файла или создаёт её с фразами по умолчанию."""
    global phrase_library
    if os.path.exists(PHRASE_LIBRARY_FILE):
        try:
            with open(PHRASE_LIBRARY_FILE, "r", encoding="utf-8") as f:
                phrase_library = json.load(f)
        except Exception as e:
            print("Ошибка загрузки библиотеки фраз:", e)
            phrase_library = []
    else:
        phrase_library = [
            "Фраза 1: Время — это иллюзия.",
            "Фраза 2: Секрет знаний в постоянном поиске.",
            "Фраза 3: Моя база данных полна тайн.",
            "Фраза 4: Я наблюдаю за тобой.",
            "Фраза 5: Код — язык вселенной."
        ]
        save_phrase_library()

def save_phrase_library():
    """Сохраняет текущую библиотеку фраз в файл."""
    try:
        with open(PHRASE_LIBRARY_FILE, "w", encoding="utf-8") as f:
            json.dump(phrase_library, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print("Ошибка сохранения библиотеки фраз:", e)

def assign_access_level(user_id: int) -> str:
    """
    Если пользователь уже имеет назначенный уровень – возвращает его.
    Для новых пользователей всегда назначается уровень "UserD1".
    """
    if user_id in user_access:
        return user_access[user_id]
    new_level = "UserD1"
    user_access[user_id] = new_level
    save_user_access()
    return new_level

def get_user_access(user_id: int) -> str:
    return assign_access_level(user_id)

def get_clearance_value(level: str) -> int:
    return clearance_levels.get(level, 0)

def save_to_memory(filename: str, owner_id: int, raw_text: str) -> (bool, str):
    """
    Сохраняет данные в качестве JSON-файла.
    Если в начале raw_text указан блок доступа вида:
      {UserD1} или {UserD1;UserD2} – извлекается список разрешённых уровней.
    При отсутствии блока используется уровень автора.
    Использование уровней "Admin" и "User_1" через фигурные скобки запрещено.
    """
    ensure_memory_dir()
    pattern = r'^\s*\{([^}]+)\}\s*(.*)'
    match = re.match(pattern, raw_text, flags=re.DOTALL)
    if match:
        allowed_block = match.group(1).strip()
        content_text = match.group(2).strip()
        allowed_list = [x.strip() for x in allowed_block.split(';') if x.strip()]
        if any(lvl in ["Admin", "User_1"] for lvl in allowed_list):
            return False, ("Недопустимое задание уровней доступа через фигурные скобки. "
                           "Используйте уровни, например: UserD1, UserD2, UserD3.")
    else:
        allowed_list = [get_user_access(owner_id)]
        content_text = raw_text.strip()
    memory_data = {
        "owner_id": owner_id,
        "allowed": allowed_list,
        "content": content_text
    }
    if not filename.endswith(".json"):
        filename += ".json"
    filepath = os.path.join(MEMORY_DIR, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=4)
        return True, "Файл сохранён."
    except Exception as e:
        return False, f"Ошибка при сохранении файла: {e}"

def load_memory(filename: str):
    """
    Загружает содержимое файла памяти (JSON) или возвращает None, если файл не найден/ошибка.
    """
    if not filename.endswith(".json"):
        filename += ".json"
    filepath = os.path.join(MEMORY_DIR, filename)
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                memory_data = json.load(f)
                return memory_data
        except json.JSONDecodeError:
            return None
    return None

def list_accessible_files(user_id: int):
    """
    Возвращает список имён (без расширения) файлов из папки памяти, которые доступны для данного пользователя.
    """
    accessible = []
    user_clearance = get_clearance_value(get_user_access(user_id))
    for file in os.listdir(MEMORY_DIR):
        if file.endswith(".json") and file not in [os.path.basename(USER_ACCESS_FILE), os.path.basename(PHRASE_LIBRARY_FILE)]:
            memory_data = load_memory(file)
            if memory_data is None:
                continue
            allowed_list = memory_data.get("allowed", [])
            required_clearance = max([get_clearance_value(lvl) for lvl in allowed_list]) if allowed_list else 0
            if user_clearance >= required_clearance:
                accessible.append(file.replace(".json", ""))
    return accessible

# Настройка intents для чтения сообщений и содержимого
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

@tasks.loop(minutes=10)
async def phrase_loop():
    """
    Фоновый цикл, раз в 10 минут выбирающий случайную фразу из библиотеки
    и отправляющий её в первый доступный текстовый канал первого сервера.
    """
    global phrase_library
    if phrase_library:
        phrase = random.choice(phrase_library)
        if client.guilds:
            guild = client.guilds[0]
            if guild.text_channels:
                channel = guild.text_channels[0]
                try:
                    await channel.send(phrase)
                except Exception as e:
                    print("Ошибка отправки фразы:", e)

@client.event
async def on_ready():
    ensure_memory_dir()
    load_user_access()
    load_phrase_library()
    phrase_loop.start()
    print(f'Бот {client.user} подключился к серверу!')

@client.event
async def on_message(message):
    # Игнорируем сообщения от самого бота
    if message.author == client.user:
        return

    # Если это личные сообщения (DM), позволяю обрабатывать все входящие сообщения,
    # и если строка не начинается с "!", отвечаю подсказкой.
    if isinstance(message.channel, discord.DMChannel):
        if not message.content.startswith("!"):
            await message.channel.send("Привет! Я работаю в личных сообщениях. Чтобы воспользоваться моим функционалом, пиши команды с префиксом «!» (например, !save, !recall).")
            return
    else:
        # В публичных каналах обрабатываем только команды, начинающиеся с "!"
        if not message.content.startswith("!"):
            return

    # Если пользователь новый, отправляем приветственное сообщение с его уровнем
    if message.author.id not in user_access:
        level = assign_access_level(message.author.id)
        await message.channel.send(f"Привет! Ты новый пользователь. Твой уровень доступа: {level}")

    # Если уровень пользователя "Null_" – команды не выполняются
    user_level = get_user_access(message.author.id)
    if user_level == "Null_":
        await message.channel.send("У тебя нет доступа.")
        return

    content = message.content.strip()

    # Команда назначения уровня доступа (!ga) – доступна только для Admin.
    # Принимает либо упоминание, либо ID.
    if content.startswith("!ga"):
        if message.author.id != ADMIN_ID:
            await message.channel.send("У вас недостаточно прав для этой команды.")
            return

        parts = content.split()
        if len(parts) != 3:
            await message.channel.send("Неверный формат команды. Пример: !ga @User UserD2 или !ga 123456789012345678 UserD2")
            return

        target_id = None
        target_mention = None
        if message.mentions:
            target_id = message.mentions[0].id
            target_mention = message.mentions[0].mention
        else:
            try:
                target_id = int(parts[1])
                target_mention = f"<@{target_id}>"
            except ValueError:
                await message.channel.send("Неверный формат ID пользователя.")
                return

        # Администратор не может менять себе уровень доступа
        if target_id == message.author.id:
            await message.channel.send("Нельзя изменить собственный уровень доступа.")
            return

        new_level = parts[2].strip()
        if new_level in ["Admin", "User_1"]:
            await message.channel.send("Нельзя назначать уровни доступа Admin или User_1 через эту команду.")
            return
        if new_level not in clearance_levels:
            await message.channel.send("Неверный уровень доступа. Допустимые: UserD3, UserD2, UserD1, Null_.")
            return

        user_access[target_id] = new_level
        save_user_access()
        await message.channel.send(f"Пользователю {target_mention} назначен уровень доступа **{new_level}**.")
        return

    # Команда сохранения файла памяти: !save <имя_файла> <текст>
    if content.startswith("!save"):
        parts = content.split(maxsplit=2)
        if len(parts) < 3:
            await message.channel.send("Неверный формат команды.\nПример:\n!save my_note {UserD1} Секретная информация...")
            return
        filename = parts[1].strip()
        raw_text = parts[2]
        success, msg_save = save_to_memory(filename, message.author.id, raw_text)
        if success:
            if not isinstance(message.channel, discord.DMChannel):
                try:
                    await message.delete()
                except discord.Forbidden:
                    await message.channel.send("Ошибка: недостаточно прав для удаления сообщения.")
            print(f"Файл {filename} сохранён пользователем {message.author.id}.")
        else:
            await message.channel.send(msg_save)
        return

    # Команда извлечения файла памяти: !recall <имя_файла>
    # Выводит содержимое запрошенного файла и список всех доступных файлов для пользователя.
    if content.startswith("!recall"):
        parts = content.split(maxsplit=1)
        if len(parts) != 2:
            await message.channel.send("Неверный формат команды. Пример: !recall my_note")
            return
        filename = parts[1].strip()
        memory_data = load_memory(filename)
        if memory_data is None:
            await message.channel.send("Записи для данного файла не найдены или произошла ошибка чтения.")
            return

        allowed_list = memory_data.get("allowed", [])
        required_clearance = max([get_clearance_value(lvl) for lvl in allowed_list]) if allowed_list else 0
        user_clearance = get_clearance_value(get_user_access(message.author.id))
        if user_clearance < required_clearance:
            await message.channel.send("У тебя нет доступа к этой записи.")
            return

        response = f"**Содержимое файла '{filename}':**\n{memory_data.get('content', '')}"
        if get_user_access(message.author.id) == "Admin":
            response += f"\n\n*Доступ имеют уровни: {', '.join(allowed_list)}*"
        accessible_files = list_accessible_files(message.author.id)
        if accessible_files:
            response += "\n\n**Список доступных файлов:**\n" + "\n".join(accessible_files)
        await message.channel.send(response)
        return

    # Если команда не распознана:
    await message.channel.send("Неизвестная команда. Используй !save или !recall.")

client.run(TOKEN)
