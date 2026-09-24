import asyncio
import re

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from sqlalchemy import select

from config import BOT_TOKEN, CHANNEL_ID, ADMIN_ID
from database import SessionLocal, init_db
from models import User, Movie


# ============================================
# BOT
# ============================================

bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher()


# ============================================
# ADMIN STATE
# ============================================

class BroadcastState(StatesGroup):

    waiting_for_message = State()


# ============================================
# ADMIN KEYBOARD
# ============================================

admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🎬 Kinolar"),
            KeyboardButton(text="👥 Foydalanuvchilar")
        ],
        [
            KeyboardButton(text="📊 Statistika"),
            KeyboardButton(text="📩 Xabar yuborish")
        ]
    ],
    resize_keyboard=True
)


# ============================================
# /start
# ============================================

@dp.message(CommandStart())
async def start(message: Message):

    async with SessionLocal() as session:

        result = await session.execute(
            select(User).where(
                User.telegram_id == message.from_user.id
            )
        )

        user = result.scalar_one_or_none()

        if not user:

            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username
            )

            session.add(user)

            await session.commit()

    # ADMIN

    if message.from_user.id == ADMIN_ID:

        await message.answer(
            "👨‍💻 Admin panel",
            reply_markup=admin_keyboard
        )

    # ODDIY USER

    else:

        await message.answer(
            "🎬 Assalomu alaykum!\n\n"
            "Kino kodini yuboring."
        )


# ============================================
# ADMIN — KINOLAR RO'YXATI
# ============================================

@dp.message(F.text == "🎬 Kinolar")
async def show_movies(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    async with SessionLocal() as session:

        result = await session.execute(
            select(Movie).order_by(Movie.code)
        )

        movies = result.scalars().all()

    if not movies:

        await message.answer(
            "🎬 Hozircha kinolar mavjud emas."
        )

        return

    text = "🎬 <b>Kinolar ro'yxati:</b>\n\n"

    for movie in movies:

        text += (
            f"🔢 <b>{movie.code}</b> — "
            f"{movie.title}\n"
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )


# ============================================
# ADMIN — FOYDALANUVCHILAR
# ============================================

@dp.message(F.text == "👥 Foydalanuvchilar")
async def show_users(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    async with SessionLocal() as session:

        result = await session.execute(
            select(User).order_by(User.id)
        )

        users = result.scalars().all()

    if not users:

        await message.answer(
            "👥 Hozircha foydalanuvchilar mavjud emas."
        )

        return

    text = (
        f"👥 <b>Foydalanuvchilar:</b> "
        f"{len(users)} ta\n\n"
    )

    for user in users:

        username = (
            f"@{user.username}"
            if user.username
            else "username yo'q"
        )

        text += (
            f"🆔 <code>{user.telegram_id}</code> — "
            f"{username}\n"
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )


# ============================================
# ADMIN — STATISTIKA
# ============================================

@dp.message(F.text == "📊 Statistika")
async def show_statistics(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    async with SessionLocal() as session:

        users_result = await session.execute(
            select(User)
        )

        users = users_result.scalars().all()

        movies_result = await session.execute(
            select(Movie)
        )

        movies = movies_result.scalars().all()

    await message.answer(
        "📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{len(users)}</b> ta\n"
        f"🎬 Kinolar: <b>{len(movies)}</b> ta",
        parse_mode="HTML"
    )


# ============================================
# ADMIN — XABAR YUBORISHNI BOSHLASH
# ============================================

@dp.message(F.text == "📩 Xabar yuborish")
async def start_broadcast(
    message: Message,
    state: FSMContext
):

    if message.from_user.id != ADMIN_ID:
        return

    await state.set_state(
        BroadcastState.waiting_for_message
    )

    await message.answer(
        "📩 Yubormoqchi bo‘lgan xabaringizni yuboring."
    
    )


# ============================================
# ADMIN — XABARNI BARCHA USERLARGA YUBORISH
# ============================================

@dp.message(BroadcastState.waiting_for_message)
async def send_broadcast(
    message: Message,
    state: FSMContext
):

    if message.from_user.id != ADMIN_ID:
        return

    async with SessionLocal() as session:

        result = await session.execute(
            select(User)
        )

        users = result.scalars().all()

    total = len(users)

    success = 0
    failed = 0

    await message.answer(
        f"📤 Xabar yuborilmoqda...\n\n"
        f"👥 Jami: {total} ta"
    )

    for user in users:

        try:

            await bot.copy_message(
                chat_id=user.telegram_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )

            success += 1

        except Exception as e:

            failed += 1

            print(
                f"❌ {user.telegram_id} ga yuborilmadi: {e}"
            )

    await state.clear()

    await message.answer(
        "✅ <b>Xabar yuborish tugadi!</b>\n\n"
        f"👥 Jami: {total} ta\n"
        f"✅ Yetkazildi: {success} ta\n"
        f"❌ Xatolik: {failed} ta",
        parse_mode="HTML",
        reply_markup=admin_keyboard
    )


# ============================================
# ADMIN — XABAR YUBORISHNI BEKOR QILISH
# ============================================

@dp.message(Command("cancel"))
async def cancel_broadcast(
    message: Message,
    state: FSMContext
):

    if message.from_user.id != ADMIN_ID:
        return

    await state.clear()

    await message.answer(
        "❌ Xabar yuborish bekor qilindi.",
        reply_markup=admin_keyboard
    )


# ============================================
# KINO MA'LUMOTLARINI AJRATISH
# ============================================

def get_movie_data(message: Message):

    text = message.caption or message.text or ""

    match = re.search(
        r"[Kk]od\s*[:\-]?\s*(\d+)",
        text
    )

    if not match:
        return None

    code = int(match.group(1))

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    title = lines[0] if lines else "Noma'lum kino"

    return code, title


# ============================================
# YANGI KANAL POSTI
# ============================================

@dp.channel_post()
async def channel_post(message: Message):

    if message.chat.id != CHANNEL_ID:
        return

    data = get_movie_data(message)

    if not data:

        print(
            "❌ Postda kino kodi topilmadi."
        )

        return

    code, title = data

    async with SessionLocal() as session:

        result = await session.execute(
            select(Movie).where(
                Movie.code == code
            )
        )

        movie = result.scalar_one_or_none()

        if movie:

            movie.title = title

            movie.channel_message_id = (
                message.message_id
            )

            print(
                f"🔄 Kod {code} yangilandi: {title}"
            )

        else:

            movie = Movie(
                code=code,
                title=title,
                channel_message_id=message.message_id
            )

            session.add(movie)

            print(
                f"✅ Yangi kino qo'shildi: "
                f"{code} - {title}"
            )

        await session.commit()


# ============================================
# KANAL POSTI EDIT QILINGANDA
# ============================================

@dp.edited_channel_post()
async def edited_channel_post(message: Message):

    if message.chat.id != CHANNEL_ID:
        return

    data = get_movie_data(message)

    if not data:

        print(
            f"⚠️ Edit qilingan postda kod topilmadi: "
            f"{message.message_id}"
        )

        return

    code, title = data

    async with SessionLocal() as session:

        # Shu message_id bo'yicha eski kino

        result = await session.execute(
            select(Movie).where(
                Movie.channel_message_id
                == message.message_id
            )
        )

        old_movie = result.scalar_one_or_none()

        # Shu kod boshqa kinoda ishlatilganmi?

        result = await session.execute(
            select(Movie).where(
                Movie.code == code
            )
        )

        same_code_movie = result.scalar_one_or_none()

        if old_movie:

            old_movie.code = code

            old_movie.title = title

            old_movie.channel_message_id = (
                message.message_id
            )

            # Agar boshqa yozuv shu kodda bo'lsa

            if (
                same_code_movie
                and same_code_movie.id
                != old_movie.id
            ):

                await session.delete(
                    same_code_movie
                )

        else:

            # Telegramdagi post DBda yo'q bo'lsa

            if same_code_movie:

                same_code_movie.title = title

                same_code_movie.channel_message_id = (
                    message.message_id
                )

            else:

                session.add(
                    Movie(
                        code=code,
                        title=title,
                        channel_message_id=(
                            message.message_id
                        )
                    )
                )

        await session.commit()

    print(
        f"✏️ Kino yangilandi: "
        f"{code} - {title}"
    )


# ============================================
# KINO KODI ORQALI KINO OLISH
# ============================================

@dp.message()
async def get_movie(message: Message):

    if not message.text:
        return

    text = message.text.strip()

    if not text.isdigit():
        return

    code = int(text)

    async with SessionLocal() as session:

        result = await session.execute(
            select(Movie).where(
                Movie.code == code
            )
        )

        movie = result.scalar_one_or_none()

        if not movie:

            await message.answer(
                "❌ Bunday koddagi kino topilmadi."
            )

            return

        movie_id = movie.id

        title = movie.title

        message_id = movie.channel_message_id

    # ========================================
    # KANALDAGI POSTNI NUSXALASH
    # ========================================

    try:

        await bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=CHANNEL_ID,
            message_id=message_id
        )

        print(
            f"🎬 Kino yuborildi: "
            f"{code} - {title}"
        )

    except Exception as e:

        print(
            f"❌ Kino yuborishda xatolik: {e}"
        )

        # Agar kanal post o'chirilgan bo'lsa

        if "MESSAGE_ID_INVALID" in str(e):

            async with SessionLocal() as session:

                result = await session.execute(
                    select(Movie).where(
                        Movie.id == movie_id
                    )
                )

                deleted_movie = (
                    result.scalar_one_or_none()
                )

                if deleted_movie:

                    await session.delete(
                        deleted_movie
                    )

                    await session.commit()

            await message.answer(
                "❌ Bu kino kanaldan o‘chirilgan."
            )

        else:

            await message.answer(
                "❌ Kinoni yuborishda "
                "xatolik yuz berdi."
            )


# ============================================
# MAIN
# ============================================

async def main():

    await init_db()

    print("🤖 Bot ishga tushdi...")

    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())