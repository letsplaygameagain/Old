import requests
import os

import random

import asyncio
import yt_dlp
import shutil
from Yukki.Utilities.spotify import get_spotify_url, getsp_album_info, getsp_artist_info, getsp_playlist_info, getsp_track_info
from Yukki.Plugins.custom.func import mplay_stream
from Yukki.Utilities.resso import get_resso_album, get_resso_artist, get_resso_playlist, get_resso_track, get_resso_url
from Yukki.Plugins.Resso import resso_buttons, resso_play
from Yukki.Plugins.Spotify import spotify_buttons, spotify_play
import asyncio
from os import path

from pyrogram import filters
from pyrogram.types import (InlineKeyboardMarkup, InputMediaPhoto, Message,
                            Voice)
from youtube_search import YoutubeSearch

import Yukki
from Yukki import (BOT_USERNAME, DURATION_LIMIT, DURATION_LIMIT_MIN,
                   MUSIC_BOT_NAME, app, db_mem)
from Yukki.Core.PyTgCalls.Converter import convert
from Yukki.Core.PyTgCalls.Downloader import download
from Yukki.Core.PyTgCalls.Tgdownloader import telegram_download
from Yukki.Database import (get_active_video_chats, get_video_limit,
                            is_active_video_chat)
from Yukki.Decorators.assistant import AssistantAdd
from Yukki.Decorators.checker import checker
from Yukki.Decorators.logger import logging
from Yukki.Decorators.permission import PermissionCheck
from Yukki.Inline import (livestream_markup, playlist_markup, search_markup,
                          search_markup2, url_markup, url_markup2)
from Yukki.Utilities.changers import seconds_to_min, time_to_seconds
from Yukki.Utilities.chat import specialfont_to_normal
from Yukki.Utilities.stream import start_stream, start_stream_audio
from Yukki.Utilities.theme import check_theme
from Yukki.Utilities.thumbnails import gen_thumb
from Yukki.Utilities.url import get_url
from Yukki.Utilities.videostream import start_stream_video
from Yukki.Utilities.youtube import (get_yt_info_id, get_yt_info_query,
                                     get_yt_info_query_slider)
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from pyrogram.errors import UserNotParticipant
from typing import Union

loop = asyncio.get_event_loop()

UPDATES_CHANNEL = "kontenfilm"

def time_to_seconds(time):
    stringt = str(time)
    return sum(int(x) * 60**i for i, x in enumerate(reversed(stringt.split(":"))))


def convert_seconds(seconds):
    seconds = seconds % (24 * 3600)
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%02d:%02d" % (minutes, seconds)


def ytsearch(query):
    try:
        search = VideosSearch(query, limit=1).result()
        data = search["result"][0]
        songname = data["title"]
        url = data["link"]
        duration = data["duration"]
        thumbnail = f"https://i.ytimg.com/vi/{data['id']}/hqdefault.jpg"
        return [songname, url, duration, thumbnail]
    except Exception as e:
        print(e)
        return 0


async def ytdl(link):
    proc = await asyncio.create_subprocess_exec(
        "yt-dlp",
        "-g",
        "-f",
        "best[height<=?720][width<=?1280]",
        f"{link}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if stdout:
        return 1, stdout.decode().split("\n")[0]
    else:
        return 0, stderr.decode()


def get_text(message: Message) -> Union[None, str]:
    text_to_return = message.text
    if message.text is None:
        return None
    if " " in text_to_return:
        try:
            return message.text.split(None, 1)[1]
        except IndexError:
            return None
    else:
        return None

@app.on_message(
    filters.command(["play", f"play@{BOT_USERNAME}"]) & filters.group
)
@checker
@logging
@PermissionCheck
@AssistantAdd
async def play(_, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    rpk = "[" + user_name + "](tg://user?id=" + str(user_id) + ")"
    update_channel = UPDATES_CHANNEL
    if update_channel:
        try:
            user = await app.get_chat_member(update_channel, user_id)
            if user.status == "kicked":
                await app.send_message(
                    chat_id,
                    text=f"**❌ {rpk} anda telah di blokir dari grup dukungan\n\n😎 Klik tombol dibawah untuk menghubungi admin grup**",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "𝗗𝗼𝗻𝗮𝘀𝗶 ❤️",
                                    url="https://t.me/Riizzvbss",
                                )
                            ]
                        ]
                    ),
                    parse_mode="markdown",
                    disable_web_page_preview=True,
                )
                return
        except UserNotParticipant:
            await app.send_message(
                chat_id,
                text=f"**👋🏻 Halo {rpk}\nUntuk Menghindari Penggunaan Yang Berlebihan Bot Ini Di Khususkan Untuk Yang Sudah Join Di Channel Music !**",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "𝗝𝗼𝗶𝗻 𝗖𝗵𝗮𝗻𝗻𝗲𝗹 💌",
                                url=f"https://t.me/{update_channel}",
                            )
                        ]
                    ]
                ),
                parse_mode="markdown",
            )
            return
    await message.delete()
    if message.chat.id not in db_mem:
        db_mem[message.chat.id] = {}
    if message.sender_chat:
        return await message.reply_text(
            "You're an __Anonymous Admin__ in this Chat Group!\nRevert back to User Account From Admin Rights."
        )
    audio = (
        (message.reply_to_message.audio or message.reply_to_message.voice)
        if message.reply_to_message
        else None
    )
    video = (
        (message.reply_to_message.video or message.reply_to_message.document)
        if message.reply_to_message
        else None
    )
    url = get_url(message)
    if audio:
        mystic = await message.reply_text(
            "Processing Audio... Please Wait!"
        )
        if audio.file_size > 1073741824:
            return await mystic.edit_text(
                "Audio File Size Should Be Less Than 150 mb"
            )
        duration_min = seconds_to_min(audio.duration)
        duration_sec = audio.duration
        if (audio.duration) > DURATION_LIMIT:
            return await mystic.edit_text(
                f"**Duration Limit Exceeded**\n\n**Allowed Duration: **{DURATION_LIMIT_MIN} minute(s)\n**Received Duration:** {duration_min} minute(s)"
            )
        file_name = (
            audio.file_unique_id
            + "."
            + (
                (audio.file_name.split(".")[-1])
                if (not isinstance(audio, Voice))
                else "ogg"
            )
        )
        file_name = path.join(path.realpath("downloads"), file_name)
        file = await convert(
            (await message.reply_to_message.download(file_name))
            if (not path.isfile(file_name))
            else file_name,
        )
        return await start_stream_audio(
            message,
            file,
            "smex1",
            "Given Audio Via Telegram",
            duration_min,
            duration_sec,
            mystic,
        )
    elif video:
        limit = await get_video_limit(141414)
        if not limit:
            return await message.reply_text(
                "**No Limit Defined for Video Calls**\n\nSet a Limit for Number of Maximum Video Calls allowed on Bot by /set_video_limit [Sudo Users Only]"
            )
        count = len(await get_active_video_chats())
        if int(count) == int(limit):
            if await is_active_video_chat(message.chat.id):
                pass
            else:
                return await message.reply_text(
                    "Sorry! Bot only allows limited number of video calls due to CPU overload issues. Many other chats are using video call right now. Try switching to audio or try again later"
                )
        mystic = await message.reply_text(
            "Processing Video... Please Wait!"
        )
        file = await telegram_download(message, mystic)
        return await start_stream_video(
            message,
            file,
            "Given Video Via Telegram",
            mystic,
        )
    elif url:
        if "spotify.com" in url:
            return await message.reply_text("Use /spotify for spotify links")
        
        if "resso.com" in url:            
            return await message.reply_text("Use /resso for resso links")
        
        mystic = await message.reply_text("Processing URL... Please Wait!")
        if not message.reply_to_message:
            query = message.text.split(None, 1)[1]
        else:
            query = message.reply_to_message.text
        (
            title,
            duration_min,
            duration_sec,
            thumb,
            videoid,
            views, 
            channel
        ) = get_yt_info_query(query)
        await mystic.delete()
        buttons = url_markup2(videoid, duration_min, message.from_user.id)
        return await message.reply_photo(
            photo=thumb,
            caption=f"📌 **Name:**{title}\n**⏱️ Duration**: {duration_min} Mins\n\n📑 [Get  Information](https://t.me/{BOT_USERNAME}?start=info_{videoid})",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    else:
        if len(message.command) < 2:
            buttons = playlist_markup(
                message.from_user.first_name, message.from_user.id, "abcd"
            )
            await message.reply_text(
                    "**Usage:** /play [Music Name or Youtube Link or Reply to Audio]\n\nIf you want to play Playlists! Select the one from Below.",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            return
        mystic = await message.reply_text("🔍 **Searching**...")
        query = message.text.split(None, 1)[1]
        (
            title,
            duration_min,
            duration_sec,
            thumb,
            videoid,
            views, 
            channel
        ) = get_yt_info_query(query)
        await mystic.delete()
        buttons = url_markup(
            videoid, duration_min, message.from_user.id, query, 0
        )
        return await message.reply_photo(
            photo=thumb,
            caption=f"📌 **Name:**{title}\n**⏱️ Duration**: {duration_min} Mins\n\n📑 [Get  Information](https://t.me/{BOT_USERNAME}?start=info_{videoid})",
            reply_markup=InlineKeyboardMarkup(buttons),
        )


@app.on_callback_query(filters.regex(pattern=r"MusicStream"))
async def Music_Stream(_, CallbackQuery):
    if CallbackQuery.message.chat.id not in db_mem:
        db_mem[CallbackQuery.message.chat.id] = {}
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    chat_id = CallbackQuery.message.chat.id
    chat_title = CallbackQuery.message.chat.title
    videoid, duration, user_id = callback_request.split("|")
    if str(duration) == "None":
        buttons = livestream_markup("720", videoid, duration, user_id)
        return await CallbackQuery.edit_message_text(
            "**Live Stream Detected**\n\nWant to play live stream? This will stop the current playing musics(if any) and will start streaming live video.",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    if CallbackQuery.from_user.id != int(user_id):
        return await CallbackQuery.answer(
            "This is not for you! Search You Own Song.", show_alert=True
        )
    try:
        with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
            x = ytdl.extract_info(url, download=False)
            
    await CallbackQuery.message.delete()
    if duration_sec > DURATION_LIMIT:
        return await CallbackQuery.message.reply_text(
            f"**Duration Limit Exceeded**\n\n**Allowed Duration: **{DURATION_LIMIT_MIN} minute(s)\n**Received Duration:** {duration_min} minute(s)"
        )
    await CallbackQuery.answer(f"Processing:- {title[:20]}", show_alert=True)
    mystic = await CallbackQuery.message.reply_text(
        f"**{MUSIC_BOT_NAME} Downloader**\n\n**Title:** {title[:50]}\n\n0% ▓▓▓▓▓▓▓▓▓▓▓▓ 100%"
    )
    url = f"https://www.youtube.com/watch?v={id}"
    videoid = id
    def download_bokep():
        ydl_optssx = {
            "format": "bestaudio/best",
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "geo_bypass": True,
            "nocheckcertificate": True,
            "quiet": True,
            "no_warnings": True,
        }
        x = yt_dlp.YoutubeDL(ydl_optssx)
        info = x.extract_info(url, False)
        xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
        if os.path.exists(xyz):
            return xyz
        x.download([url])
        return xyz
        
    downloaded_file = await loop.run_in_executor(None, download_bokep)
    raw_path = await convert(downloaded_file)
    theme = await check_theme(chat_id)
    chat_title = await specialfont_to_normal(chat_title)
    thumb = await gen_thumb(
                        thumbnail, title, CallbackQuery.from_user.id, "NOW PLAYING", views, duration_min, channel
                    )
    if chat_id not in db_mem:
        db_mem[chat_id] = {}
    await start_stream(
        CallbackQuery,
        raw_path,
        videoid,
        thumb,
        title,
        duration_min,
        duration_sec,
        mystic,
    )


@app.on_callback_query(filters.regex(pattern=r"Search"))
async def search_query_more(_, CallbackQuery):
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    query, user_id = callback_request.split("|")
    if CallbackQuery.from_user.id != int(user_id):
        return await CallbackQuery.answer(
            "Search Your Own Music. You're not allowed to use this button.",
            show_alert=True,
        )
    await CallbackQuery.answer("Searching More Results")
    results = YoutubeSearch(query, max_results=5).to_dict()
    med = f"𝟏 <b>{results[0]['title']}</b>\n  ┗➣  📑 <u>[Get Information](https://t.me/{BOT_USERNAME}?start=info_{results[0]['id']})</u>\n\n𝟐 <b>{results[1]['title']}</b>\n  ┗➣  📑 <u>[Get Information](https://t.me/{BOT_USERNAME}?start=info_{results[1]['id']})</u>\n\n𝟑 <b>{results[2]['title']}</b>\n  ┗➣  📑 <u>[Get Information](https://t.me/{BOT_USERNAME}?start=info_{results[2]['id']})</u>\n\n𝟒 <b>{results[3]['title']}</b>\n  ┗➣  📑 <u>[Get Information](https://t.me/{BOT_USERNAME}?start=info_{results[3]['id']})</u>\n\n𝟓 <b>{results[4]['title']}</b>\n  ┗➣  📑 <u>[Get Information](https://t.me/{BOT_USERNAME}?start=info_{results[4]['id']})</u>"

    buttons = search_markup(
        results[0]["id"],
        results[1]["id"],
        results[2]["id"],
        results[3]["id"],
        results[4]["id"],
        results[0]["duration"],
        results[1]["duration"],
        results[2]["duration"],
        results[3]["duration"],
        results[4]["duration"],
        user_id,
        query,
    )
    return await CallbackQuery.edit_message_text(med, reply_markup=InlineKeyboardMarkup(buttons)
    )


@app.on_callback_query(filters.regex(pattern=r"popat"))
async def popat(_, CallbackQuery):
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    userid = CallbackQuery.from_user.id
    i, query, user_id = callback_request.split("|")
    if CallbackQuery.from_user.id != int(user_id):
        return await CallbackQuery.answer(
            "This is not for you! Search You Own Song", show_alert=True
        )
    results = YoutubeSearch(query, max_results=10).to_dict()
    if int(i) == 1:
        buttons = search_markup2(
            results[5]["id"],
            results[6]["id"],
            results[7]["id"],
            results[8]["id"],
            results[9]["id"],
            results[5]["duration"],
            results[6]["duration"],
            results[7]["duration"],
            results[8]["duration"],
            results[9]["duration"],
            user_id,
            query,
        )
        await CallbackQuery.edit_message_text(
            f"𝟔 <b>{results[5]['title']}</b>\n  ┗➣  📑 <u>[Get Information](https://t.me/{BOT_USERNAME}?start=info_{results[5]['id']})</u>\n\n𝟕 <b>{results[6]['title']}</b>\n  ┗➣  📑 <u>[Get Information](https://t.me/{BOT_USERNAME}?start=info_{results[6]['id']})</u>\n\n𝟖 <b>{results[7]['title']}</b>\n  ┗➣  📑 <u>[Get Information](https://t.me/{BOT_USERNAME}?start=info_{results[7]['id']})</u>\n\n𝟗 <b>{results[8]['title']}</b>\n  ┗➣  📑 <u>[Get Additional Information](https://t.me/{BOT_USERNAME}?start=info_{results[8]['id']})</u>\n\n𝟏𝟎 <b>{results[9]['title']}</b>\n  ┗➣  📑 <u>[Get Information](https://t.me/{BOT_USERNAME}?start=info_{results[9]['id']})</u>",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        disable_web_page_preview = True
        return
    if int(i) == 2:
        buttons = search_markup(
            results[0]["id"],
            results[1]["id"],
            results[2]["id"],
            results[3]["id"],
            results[4]["id"],
            results[0]["duration"],
            results[1]["duration"],
            results[2]["duration"],
            results[3]["duration"],
            results[4]["duration"],
            user_id,
            query,
        )
        await CallbackQuery.edit_message_text(
            f"𝟏 <b>{results[0]['title']}</b>\n  ┗➣  📑 <u>[Get Information](https://t.me/{BOT_USERNAME}?start=info_{results[0]['id']})</u>\n\n𝟐 <b>{results[1]['title']}</b>\n  ┗➣  📑 <u>[Get Information](https://t.me/{BOT_USERNAME}?start=info_{results[1]['id']})</u>\n\n𝟑 <b>{results[2]['title']}</b>\n  ┗➣  📑 <u>[Get Information](https://t.me/{BOT_USERNAME}?start=info_{results[2]['id']})</u>\n\n𝟒 <b>{results[3]['title']}</b>\n  ┗➣  📑 <u>[Get Information](https://t.me/{BOT_USERNAME}?start=info_{results[3]['id']})</u>\n\n𝟓 <b>{results[4]['title']}</b>\n  ┗➣  📑 <u>[Get Information](https://t.me/{BOT_USERNAME}?start=info_{results[4]['id']})</u>",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        disable_web_page_preview = True
        return


@app.on_callback_query(filters.regex(pattern=r"slider"))
async def slider_query_results(_, CallbackQuery):
    mention = f"[{CallbackQuery.from_user.first_name}](tg://user?id={CallbackQuery.from_user.id})"
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    what, type, query, user_id = callback_request.split("|")
    if CallbackQuery.from_user.id != int(user_id):
        return await CallbackQuery.answer(
            "Search Your Own Music. You're not allowed to use this button.",
            show_alert=True,
        )
    what = str(what)
    type = int(type)
    if what == "F":
        if type == 9:
            query_type = 0
        else:
            query_type = int(type + 1)
        await CallbackQuery.answer("Getting Next Result", show_alert=True)
        (
            title,
            duration_min,
            duration_sec,
            thumb,
            videoid,
        ) = get_yt_info_query_slider(query, query_type)
        buttons = url_markup(
            videoid, duration_min, user_id, query, query_type
        )
        med = InputMediaPhoto(
            media=thumb,
            caption=f"📌 **Name:**{title}\n**⏱️ Duration**: {duration_min} Mins\n\n📑 [Get  Information](https://t.me/{BOT_USERNAME}?start=info_{videoid})",
        )
        return await CallbackQuery.edit_message_media(
            media=med, reply_markup=InlineKeyboardMarkup(buttons)
        )
    if what == "B":
        if type == 0:
            query_type = 9
        else:
            query_type = int(type - 1)
        await CallbackQuery.answer("Getting Previous Result", show_alert=True)
        (
            title,
            duration_min,
            duration_sec,
            thumb,
            videoid,
        ) = get_yt_info_query_slider(query, query_type)
        buttons = url_markup(
            videoid, duration_min, user_id, query, query_type
        )
        med = InputMediaPhoto(
            media=thumb,
            caption=f"📌 **Name:**{title}\n**⏱️ Duration**: {duration_min} Mins\n\n📑 [Get  Information](https://t.me/{BOT_USERNAME}?start=info_{videoid})",
        )
        return await CallbackQuery.edit_message_media(
            media=med, reply_markup=InlineKeyboardMarkup(buttons)
        )
