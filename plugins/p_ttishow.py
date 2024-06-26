from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired
from pyrogram.errors.exceptions.bad_request_400 import MessageTooLong, PeerIdInvalid, ChatIdInvalid
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.users_chats_db import db
from database.ia_filterdb import Media
from info import ADMINS, LOG_CHANNEL, GROUP_LOGS, SUPPORT_CHAT, SUPPORT_CHAT_ID, UPDATE_CHANNEL, MELCOW_NEW_USERS
from utils import get_size, temp, get_settings
from Script import script


@Client.on_message(filters.new_chat_members & filters.group)
async def save_group(bot, message):
    new_members = [member.id for member in message.new_chat_members]
    if temp.ME in new_members:
        if not await db.get_chat(message.chat.id):
            total = await bot.get_chat_members_count(message.chat.id)
            referrer = message.from_user.mention if message.from_user else "Anonymous" 
            await bot.send_message(LOG_CHANNEL, script.LOG_TEXT_G.format(message.chat.title, message.chat.id, total, referrer))       
            await db.add_chat(message.chat.id, message.chat.title)
        if message.chat.id in temp.BANNED_CHATS:
            buttons = [[
                InlineKeyboardButton('Support', url=(SUPPORT_CHAT))
            ]]
            reply_markup = InlineKeyboardMarkup(buttons)
            msg = await message.reply(
                text='<b>CHAT NOT ALLOWED 🐞\n\nMy admins have restricted me from working here! If you want to know more about it, contact support.</b>',
                reply_markup=reply_markup,
            )
            try:
                await msg.pin()
            except Exception as e:
                print(e)
            await bot.leave_chat(message.chat.id)
            return
        buttons = [[
            InlineKeyboardButton('ℹ️ Help', url=f"https://t.me/{temp.U_NAME}?start=help"),
            InlineKeyboardButton('📢 Updates', url=(UPDATE_CHANNEL))
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_text(
            text=f"<b>Thank you for adding me to {message.chat.title}\n\nIf you have any questions or doubts about using me, contact support.</b>",
            reply_markup=reply_markup
        )
    else:
        settings = await get_settings(message.chat.id)
        if settings["welcome"]:
            for member in message.new_chat_members:
                if temp.MELCOW.get('welcome') is not None:
                    try:
                        await (temp.MELCOW['welcome']).delete()
                    except Exception as e:
                        print(e)
                temp.MELCOW['welcome'] = await message.reply(f"<b>Hey, {member.mention}, welcome to {message.chat.title}</b>")


@Client.on_message(filters.command('leave') & filters.user(ADMINS))
async def leave_chat(bot, message):
    if len(message.command) == 1:
        return await message.reply('Give me a chat id')
    chat = message.command[1]
    try:
        chat = int(chat)
    except ValueError:
        pass
    try:
        buttons = [[
            InlineKeyboardButton('Support', url=(SUPPORT_CHAT))
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await bot.send_message(
            chat_id=chat,
            text='<b>Hello Friends,\nMy admin has told me to leave from the group so I go! If you want to add me again, contact my support group.</b>',
            reply_markup=reply_markup,
        )
        await bot.leave_chat(chat)
        await message.reply(f"Left the chat `{chat}`")
    except Exception as e:
        await message.reply(f'Error - {e}')

@Client.on_message(filters.command('disable') & filters.user(ADMINS))
async def disable_chat(bot, message):
    if len(message.command) == 1:
        return await message.reply('Give me a chat id')    
    args = message.text.split(None)
    if len(args) > 2:
        reason = message.text.split(None, 2)[2]
        chat = message.text.split(None, 2)[1]
    else:
        chat = message.command[1]
        reason = "No reason provided"    
    try:
        chat_ = int(chat)
    except ValueError:
        return await message.reply('Give me a valid chat ID')    
    chat = await db.get_chat(int(chat_))
    if not chat:
        return await message.reply("Chat not found in the database")    
    if chat['is_disabled']:
        return await message.reply(f"This chat is already disabled:\nReason: <code>{chat['reason']}</code>")    
    await db.disable_chat(int(chat_), reason)
    temp.BANNED_CHATS.append(int(chat_))    
    await message.reply('Chat successfully disabled')
    try:
        buttons = [[
            InlineKeyboardButton('Support', url=(SUPPORT_CHAT))
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await bot.send_message(
            chat_id=chat_, 
            text=f'<b>Hello friends, \nMy admin has instructed me to leave this group, so I am leaving. If you want to add me again, contact our support group.</b>\nReason: <code>{reason}</code>',
            reply_markup=reply_markup
        )
        await bot.leave_chat(chat_)
    except Exception as e:
        await message.reply(f"Error - {e}")

@Client.on_message(filters.command('enable') & filters.user(ADMINS))
async def re_enable_chat(bot, message):
    if len(message.command) == 1:
        return await message.reply('Give me a chat id')    
    chat = message.command[1]
    try:
        chat_ = int(chat)
    except ValueError:
        return await message.reply('Give me a valid chat ID')    
    sts = await db.get_chat(int(chat))
    if not sts:
        return await message.reply("Chat not found in the database!")    
    if not sts.get('is_disabled'):
        return await message.reply('This chat is not disabled.')
    await db.re_enable_chat(int(chat_))
    temp.BANNED_CHATS.remove(int(chat_))
    await message.reply("Chat successfully re-enabled")

@Client.on_message(filters.command('stats') & filters.incoming)
async def get_stats(bot, message):
    msg = await message.reply('Fetching stats...')
    total_users = await db.total_users_count()
    total_chats = await db.total_chat_count()
    files = await Media.count_documents()
    size = await db.get_db_size()
    free = 536870912 - size
    size = get_size(size)
    free = get_size(free)
    await msg.edit(script.STATUS_TXT.format(files, total_users, total_chats, size, free))

@Client.on_message(filters.command('invite') & filters.user(ADMINS))
async def gen_invite(bot, message):
    if len(message.command) == 1:
        return await message.reply('Give me a chat id')
    chat = message.command[1]
    try:
        chat = int(chat)
    except:
        return await message.reply('Give Me A Valid Chat ID')
    try:
        link = await bot.create_chat_invite_link(chat)
    except ChatAdminRequired:
        return await message.reply("Invite Link Generation Failed, Iam Not Having Sufficient Rights")
    except Exception as e:
        return await message.reply(f'Error {e}')
    await message.reply(f'Here is your Invite Link {link.invite_link}')

@Client.on_message(filters.command('ban') & filters.user(ADMINS))
async def ban_user(bot, message):
    if len(message.command) == 1:
        return await message.reply('Give me a user id or username')
    args = message.text.split(None)
    if len(args) > 2:
        reason = message.text.split(None, 2)[2]
        user_id = message.text.split(None, 2)[1]
    else:
        user_id = message.command[1]
        reason = "No reason provided"
    try:
        user_id = int(user_id)
    except ValueError:
        pass
    try:
        user = await bot.get_users(user_id)
    except PeerIdInvalid:
        return await message.reply("This is an invalid user, make sure I have met them before.")
    except IndexError:
        return await message.reply("This might be a channel, make sure it's a user.")
    except Exception as e:
        return await message.reply(f'Error - {e}')    
    else:
        ban_info = await db.get_ban_status(user.id)
        if ban_info['is_banned']:
            return await message.reply(f"{user.mention} is already banned.\nReason: {ban_info['ban_reason']}")
        await db.ban_user(user.id, reason)
        temp.BANNED_USERS.append(user.id)
        await message.reply(f"Successfully banned {user.mention}")
   
@Client.on_message(filters.command('unban') & filters.user(ADMINS))
async def unban_user(bot, message):
    if len(message.command) == 1:
        return await message.reply('Give me a user id or username')
    args = message.text.split(None)
    if len(args) > 2:
        reason = message.text.split(None, 2)[2]
        user_id = message.text.split(None, 2)[1]
    else:
        user_id = message.command[1]
        reason = "No reason provided"
    try:
        user_id = int(user_id)
    except ValueError:
        pass
    try:
        user = await bot.get_users(user_id)
    except PeerIdInvalid:
        return await message.reply("This is an invalid user, make sure I have met them before.")
    except IndexError:
        return await message.reply("This might be a channel, make sure it's a user.")
    except Exception as e:
        return await message.reply(f'Error - {e}')
    else:
        ban_info = await db.get_ban_status(user.id)
        if not ban_info['is_banned']:
            return await message.reply(f"{user.mention} is not yet banned.")
        await db.remove_ban(user.id)
        temp.BANNED_USERS.remove(user.id)
        await message.reply(f"Successfully unbanned {user.mention}")

@Client.on_message(filters.command('users') & filters.user(ADMINS))
async def list_users(bot, message):
    msg = await message.reply('Getting List Of Users')
    users = await db.get_all_users()
    out = "Users Saved In DB Are:\n\n"
    async for user in users:
        out += f"<a href=tg://user?id={user['id']}>{user['name']}</a>"
        if user['ban_status']['is_banned']:
            out += '( Banned User )'
        out += '\n'
    try:
        await msg.edit_text(out)
    except MessageTooLong:
        with open('users.txt', 'w+') as outfile:
            outfile.write(out)
        await message.reply_document('users.txt', caption="List Of Users")

@Client.on_message(filters.command('chats') & filters.user(ADMINS))
async def list_chats(bot, message):
    msg = await message.reply('Getting List Of chats')
    chats = await db.get_all_chats()
    out = "Chats Saved In DB Are:\n\n"
    async for chat in chats:
        try:
            chat_info = await bot.get_chat(chat['id'])
            out += f"**Title:** `{chat_info.title}`\n**- ID:** `{chat['id']}`\n**Members:** `{chat_info.members_count}`"
            if chat['chat_status']['is_disabled']:
                out += '( Disabled Chat )'
            out += '\n'
        except ChatIdInvalid:
            out += f"**- ID:** `{chat['id']}` - This chat is invalid or inaccessible\n"
            continue
    try:
        await msg.edit_text(out)
    except MessageTooLong:
        with open('chats.txt', 'w+') as outfile:
            outfile.write(out)
        await message.reply_document('chats.txt', caption="List Of Chats")
        
