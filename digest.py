import asyncio
import os
from datetime import datetime, timedelta, timezone
from pyrogram import Client
from pyrogram.errors import FloodWait, ChannelInvalid, ChannelPrivate

# ============================================================
#  НАСТРОЙКИ
#  Локально: заполни переменные прямо здесь.
#  На GitHub Actions: значения приходят из Secrets автоматически.
# ============================================================

API_ID          = os.environ.get("API_ID",          "ВАШ_API_ID")
API_HASH        = os.environ.get("API_HASH",         "ВАШ_API_HASH")
SESSION_STRING  = os.environ.get("SESSION_STRING",   "")   # из auth.py
OUTPUT_CHAT     = os.environ.get("OUTPUT_CHAT",      "@ваш_канал_для_дайджеста")

# Список каналов для мониторинга (добавляй сюда)
CHANNELS = [
    "tochka_live",
    "teamleadleonid",
    "tech_kuper",
    "itshka_v_sbere",
    "latech",
    "magnittech",
    "SberDeveloperNews",
    "crocteam",
    "kod_zheltyi",
    "dododev",
    "magnit_omni_team",
    "rnd2GIS",
    "kontur_live",
    "kaspersky_career",
    "ya_verticals_tech",
    "KonturTech",
    "garage_eight",
    "Yandex4Developers",
    "wb_tech",
    "career_ostrovok",
    "sdc_channel",
    "x5_tech",
    "ostrovok_tech",
    "rustoredev",
    "t_crew",
    "vkjobs",
    "TeamAvito",
    "alfadigital_jobs",
    "MWS_Cloud",
    "truetechcommunity",
    "croc_it",
    "Positive_Technologies",
    "yandexcloudnews",
    "selectelcareers",
    "ozon_tech",
    "avitotech",
    "mtsfintechjobs",
    "yandex",
    "beelinetech",
    "ecom_tech_channel",
    "cloudruprovider"
    # ...
]

TOP_N     = 10   # постов в дайджесте
MIN_VIEWS = 50   # минимум просмотров (отсекает совсем слабые посты)

# ============================================================

def get_post_text(msg) -> str:
    text = msg.text or msg.caption or ""
    if text:
        return text
    if msg.photo:
        return "📷 [пост с изображением]"
    if msg.video or msg.video_note:
        return "🎥 [пост с видео]"
    if msg.document:
        return "📎 [пост с файлом]"
    if msg.poll:
        return f"📊 [опрос: {msg.poll.question}]"
    return "[медиа без подписи]"

def make_summary(text: str, max_len: int = 250) -> str:
    if not text:
        return "_(без текста)_"
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    trimmed = text[:max_len]
    last_space = trimmed.rfind(" ")
    return trimmed[:last_space] + "…"


def make_post_link(channel: str, message_id: int) -> str:
    username = channel.lstrip("@")
    return f"https://t.me/{username}/{message_id}"


async def fetch_channel_posts(client: Client, channel: str, since: datetime) -> list:
    posts = []
    try:
        async for msg in client.get_chat_history(channel):
            if msg.date.replace(tzinfo=timezone.utc) < since:
                break
            if not msg.views or msg.views < MIN_VIEWS:
                continue

            reactions_total = 0
            if msg.reactions:
                for r in msg.reactions.reactions:
                    reactions_total += r.count

            if reactions_total == 0:
                continue

            er = reactions_total / msg.views

            posts.append({
                "channel":   channel,
                "id":        msg.id,
                "text":      get_post_text(msg),
                "views":     msg.views,
                "reactions": reactions_total,
                "er":        er,
                "date":      msg.date,
                "link":      make_post_link(channel, msg.id),
            })

    except (ChannelInvalid, ChannelPrivate) as e:
        print(f"  ⚠️  Нет доступа к {channel}: {e}")
    except FloodWait as e:
        print(f"  ⏳ FloodWait {e.value}с для {channel}, жду...")
        await asyncio.sleep(e.value)
    except Exception as e:
        print(f"  ❌ Ошибка при чтении {channel}: {e}")

    return posts


def format_digest(posts: list, since: datetime, until: datetime) -> str:
    date_from = since.strftime("%d.%m")
    date_to   = until.strftime("%d.%m.%Y")

    lines = [
        f"📊 **дайджест за неделю** {date_from}–{date_to}\n",
    ]

    
    for i, p in enumerate(posts, start=1):
        er_pct  = p["er"] * 100
        summary = make_summary(p["text"])
        channel_display = p["channel"].lstrip("@")

        lines.append(
            f"**{i}. {channel_display}**\n"
            f"👁 {p['views']:,}   ❤️ {p['reactions']}   ER: {er_pct:.1f}%\n"
            f"{summary}\n"
            f"[Открыть пост]({p['link']})\n"
        )

    return "\n".join(lines)


async def main():
    now      = datetime.now(timezone.utc)
    one_week = now - timedelta(days=7)

    # StringSession позволяет работать без файла сессии —
    # строка передаётся прямо из переменной окружения (GitHub Secret)
    from pyrogram.errors import AuthKeyUnregistered
    from pyrogram import Client

    async with Client(
        name=":memory:",
        api_id=int(API_ID),
        api_hash=API_HASH,
        session_string=SESSION_STRING,
    ) as client:
        print(f"Запущено. Собираю посты за {one_week.strftime('%d.%m')}–{now.strftime('%d.%m.%Y')}...")
        print(f"Каналов в списке: {len(CHANNELS)}\n")

        all_posts = []

        for i, channel in enumerate(CHANNELS, start=1):
            print(f"[{i}/{len(CHANNELS)}] {channel}")
            posts = await fetch_channel_posts(client, channel, one_week)
            print(f"  → найдено постов: {len(posts)}")
            all_posts.extend(posts)
            await asyncio.sleep(1.5)

        if not all_posts:
            print("\nПостов с реакциями за эту неделю не найдено.")
            return

        top = sorted(all_posts, key=lambda x: x["er"], reverse=True)[:TOP_N]

        print(f"\nВсего постов с реакциями: {len(all_posts)}")
        print(f"Отобрано в топ: {len(top)}")

        digest_text = format_digest(top, one_week, now)

        await client.send_message(
            OUTPUT_CHAT,
            digest_text,
            disable_web_page_preview=True,
        )
        print(f"\n✅ Дайджест отправлен в {OUTPUT_CHAT}")


if __name__ == "__main__":
    asyncio.run(main())
