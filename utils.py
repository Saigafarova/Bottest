from aiogram import types

GROUP_ID_FOR_CHECK = -1002919690674

async def check_user_in_group(user_id: int, bot) -> bool:
    try:
        member = await bot.get_chat_member(GROUP_ID_FOR_CHECK, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Не удалось проверить участника {user_id}: {e}")
        return False