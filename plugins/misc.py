import os
import logging
import time
from datetime import datetime
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors.exceptions.bad_request_400 import (
    UserNotParticipant,
    MediaEmpty,
    PhotoInvalidDimensions,
    WebpageMediaEmpty
)
from info import IMDB_TEMPLATE
from utils import extract_user, get_file_id, get_poster, last_online


# Set logging level to ERROR
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


@Client.on_message(filters.command('id'))
async def showid(client, message):
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        user_id = message.chat.id
        first = message.from_user.first_name
        last = message.from_user.last_name or ""
        username = message.from_user.username
        dc_id = message.from_user.dc_id or ""
        await message.reply_text(
            f"<b>➲ First Name:</b> {first}\n"
            f"<b>➲ Last Name:</b> {last}\n"
            f"<b>➲ Username:</b> {username}\n"
            f"<b>➲ Telegram ID:</b> <code>{user_id}</code>\n"
            f"<b>➲ Data Centre:</b> <code>{dc_id}</code>",
            quote=True
        )
    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        _id = ""
        _id += (
            "<b>➲ Chat ID</b>: "
            f"<code>{message.chat.id}</code>\n"
        )
        if message.reply_to_message:
            _id += (
                "<b>➲ User ID</b>: "
                f"<code>{message.from_user.id if message.from_user else 'Anonymous'}</code>\n"
                "<b>➲ Replied User ID</b>: "
                f"<code>{message.reply_to_message.from_user.id if message.reply_to_message.from_user else 'Anonymous'}</code>\n"
            )
            file_info = get_file_id(message.reply_to_message)
        else:
            _id += (
                "<b>➲ User ID</b>: "
                f"<code>{message.from_user.id if message.from_user else 'Anonymous'}</code>\n"
            )
            file_info = get_file_id(message)
        if file_info:
            _id += (
                f"<b>{file_info.message_type}</b>: "
                f"<code>{file_info.file_id}</code>\n"
            )
        await message.reply_text(
            _id,
            quote=True
        )

@Client.on_message(filters.command('info'))
async def who_is(client, message):
    status_message = await message.reply_text("`Fetching user info...`")
    await status_message.edit("`Processing user info...`")
    
    from_user = None
    from_user_id, _ = extract_user(message)
    
    try:
        from_user = await client.get_users(from_user_id)
    except Exception as error:
        await status_message.edit(str(error))
        return
    
    if from_user is None:
        return await status_message.edit("No valid user_id / message specified")
    
    message_out_str = ""
    message_out_str += f"<b>➲ First Name:</b> {from_user.first_name}\n"
    last_name = from_user.last_name or "<b>None</b>"
    message_out_str += f"<b>➲ Last Name:</b> {last_name}\n"
    message_out_str += f"<b>➲ Telegram ID:</b> <code>{from_user.id}</code>\n"
    username = from_user.username or "<b>None</b>"
    dc_id = from_user.dc_id or "<b>[User Doesn't Have A Valid DP]</b>"
    message_out_str += f"<b>➲ Data Centre:</b> <code>{dc_id}</code>\n"
    message_out_str += f"<b>➲ User Name:</b> @{username}\n"
    message_out_str += f"<b>➲ User Link:</b> <a href='tg://user?id={from_user.id}'><b>Click Here</b></a>\n"
    
    if message.chat.type in (enums.ChatType.SUPERGROUP, enums.ChatType.CHANNEL):
        try:
            chat_member_p = await message.chat.get_member(from_user.id)
            joined_date = (chat_member_p.joined_date or datetime.now()).strftime("%Y.%m.%d %H:%M:%S")
            message_out_str += f"<b>➲ Joined this Chat on:</b> <code>{joined_date}</code>\n"
        except UserNotParticipant:
            pass
    
    chat_photo = from_user.photo
    if chat_photo:
        local_user_photo = await client.download_media(message=chat_photo.big_file_id)
        buttons = [[InlineKeyboardButton('🔐 Close', callback_data='close_data')]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo=local_user_photo,
            quote=True,
            reply_markup=reply_markup,
            caption=message_out_str,
            parse_mode=enums.ParseMode.HTML,
            disable_notification=True
        )
        os.remove(local_user_photo)
    else:
        buttons = [[InlineKeyboardButton('🔐 Close', callback_data='close_data')]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_text(
            text=message_out_str,
            reply_markup=reply_markup,
            quote=True,
            parse_mode=enums.ParseMode.HTML,
            disable_notification=True
        )
    await status_message.delete()

@Client.on_message(filters.command("imdb"))
async def imdb_search(client, message):
    if ' ' in message.text:
        search_msg = await message.reply('Searching IMDb...')
        command, title = message.text.split(None, 1)
        movies = await get_poster(title, bulk=True)
        if not movies:
            return await message.reply("No results found")
        buttons = [
            [
                InlineKeyboardButton(
                    text=f"{movie.get('title')} - {movie.get('year')}",
                    callback_data=f"imdb#{movie.movieID}",
                )
            ]
            for movie in movies
        ]
        await search_msg.edit('Here is what I found on IMDb', reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message.reply('Give me a movie or series name')

@Client.on_callback_query(filters.regex('^imdb'))
async def imdb_callback(bot: Client, query: CallbackQuery):
    _, movie_id = query.data.split('#')
    imdb_info = await get_poster(query=movie_id, id=True)
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{imdb_info.get('title')}",
                url=imdb_info['url'],
            )
        ]
    ]
    message = query.message.reply_to_message or query.message
    if imdb_info:
        caption = IMDB_TEMPLATE.format(
            query=imdb_info['title'],
            title=imdb_info['title'],
            votes=imdb_info['votes'],
            aka=imdb_info["aka"],
            seasons=imdb_info["seasons"],
            box_office=imdb_info['box_office'],
            localized_title=imdb_info['localized_title'],
            kind=imdb_info['kind'],
            imdb_id=imdb_info["imdb_id"],
            cast=imdb_info["cast"],
            runtime=imdb_info["runtime"],
            countries=imdb_info["countries"],
            certificates=imdb_info["certificates"],
            languages=imdb_info["languages"],
            director=imdb_info["director"],
            writer=imdb_info["writer"],
            producer=imdb_info["producer"],
            composer=imdb_info["composer"],
            cinematographer=imdb_info["cinematographer"],
            music_team=imdb_info["music_team"],
            distributors=imdb_info["distributors"],
            release_date=imdb_info['release_date'],
            year=imdb_info['year'],
            genres=imdb_info['genres'],
            poster=imdb_info['poster'],
            plot=imdb_info['plot'],
            rating=imdb_info['rating'],
            url=imdb_info['url'],
            **locals()
        )
    else:
        caption = "No results"
    try:
        if imdb_info.get('poster'):
            await query.message.reply_photo(photo=imdb_info['poster'], caption=caption, reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await query.message.edit(caption, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=False)
    except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
        pic = imdb_info.get('poster')
        poster = pic.replace('.jpg', "._V1_UX360.jpg")
        await query.message.reply_photo(photo=poster, caption=caption, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.exception(e)
        await query.message.reply(caption, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=False)
    await query.message.delete()
    await query.answer()

        
