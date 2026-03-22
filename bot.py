import os
import re
import asyncio
import aiohttp
import logging
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ─── CONFIG (Railway environment variables se aayega) ────────────────────────
API_ID          = int(os.environ.get("21954054", "0"))
API_HASH        = os.environ.get("5c8ad310b11454cbb5cbb3bc3df75c54", "")
BOT_TOKEN       = os.environ.get("8761145131:AAHl2uUeiKPNipRY0zKwuVek-L1ejBZahd0", "")
OMDB_KEY        = os.environ.get("http://www.omdbapi.com/?i=tt3896198&apikey=ab97208c", "")
MOVIE_CHANNEL   = os.environ.get("-1002793410950", "")   # Channel 1 - jahan movies hain
UPDATE_CHANNEL  = os.environ.get("-1001713509408", "")  # Channel 2 - jahan update jaega
MOVIE_CH_LINK   = os.environ.get("https://t.me/rksearchinggroup", "")   # e.g. https://t.me/YourMovieChannel

# ─── INIT CLIENT ─────────────────────────────────────────────────────────────
client = TelegramClient('bot_session', 21954054, 5c8ad310b11454cbb5cbb3bc3df75c54).start(bot_token=8761145131:AAHl2uUeiKPNipRY0zKwuVek-L1ejBZahd0)

# ─── MOVIE NAME CLEANER ───────────────────────────────────────────────────────
def clean_movie_name(text: str) -> str:
    """Caption ya file name se clean movie naam nikalo"""
    if not text:
        return ""
    # Remove emojis
    text = re.sub(r'[^\x00-\x7F\u0900-\u097F\s]', ' ', text)
    # Remove common patterns
    patterns = [
        r'\b(480p|720p|1080p|4k|2160p|bluray|webrip|hdcam|dvdrip|hdrip|web-dl)\b',
        r'\b(hindi|english|dubbed|multi|audio|mkv|mp4|avi|x264|x265|hevc)\b',
        r'\[.*?\]', r'\(.*?\)', r'\{.*?\}',
        r'[-_\.]{2,}', r'\s{2,}',
    ]
    for p in patterns:
        text = re.sub(p, ' ', text, flags=re.IGNORECASE)
    # Take first line only
    text = text.split('\n')[0].strip()
    # Remove year at end if present (keep for search)
    year_match = re.search(r'\b(19|20)\d{2}\b', text)
    year = year_match.group() if year_match else None
    clean = re.sub(r'\b(19|20)\d{2}\b', '', text).strip()
    clean = re.sub(r'\s+', ' ', clean).strip(' -_.')
    return clean, year

# ─── OMDB FETCH ───────────────────────────────────────────────────────────────
async def fetch_movie_info(movie_name: str, year: str = None) -> dict:
    """OMDB se movie details fetch karo"""
    try:
        params = {
            "t": movie_name,
            "apikey": OMDB_KEY,
            "plot": "short",
            "type": "movie"
        }
        if year:
            params["y"] = year

        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.omdbapi.com/", params=params) as r:
                data = await r.json()

        if data.get("Response") == "True":
            return data

        # Year match nahi hua toh bina year try karo
        if year:
            params.pop("y")
            async with aiohttp.ClientSession() as session:
                async with session.get("https://www.omdbapi.com/", params=params) as r:
                    data = await r.json()
            if data.get("Response") == "True":
                return data

        # Partial search fallback
        search_params = {"s": movie_name, "apikey": OMDB_KEY, "type": "movie"}
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.omdbapi.com/", params=search_params) as r:
                sdata = await r.json()

        if sdata.get("Response") == "True" and sdata.get("Search"):
            top = sdata["Search"][0]
            detail_params = {"i": top["imdbID"], "apikey": OMDB_KEY, "plot": "short"}
            async with aiohttp.ClientSession() as session:
                async with session.get("https://www.omdbapi.com/", params=detail_params) as r:
                    return await r.json()

    except Exception as e:
        logger.error(f"OMDB error: {e}")
    return None

# ─── BUILD CAPTION ────────────────────────────────────────────────────────────
def build_caption(info: dict, msg_link: str, raw_name: str) -> str:
    title   = info.get("Title", raw_name)
    year    = info.get("Year", "")
    rating  = info.get("imdbRating", "N/A")
    genre   = info.get("Genre", "")
    runtime = info.get("Runtime", "")
    lang    = info.get("Language", "")
    plot    = info.get("Plot", "")
    director= info.get("Director", "")

    lines = [f"🎬 *{title}*" + (f" ({year})" if year else "")]
    lines.append("")
    if rating and rating != "N/A":
        lines.append(f"⭐ Rating: {rating}/10")
    if genre and genre != "N/A":
        lines.append(f"🎭 Genre: {genre}")
    if runtime and runtime != "N/A":
        lines.append(f"⏱ Runtime: {runtime}")
    if lang and lang != "N/A":
        lines.append(f"🌐 Language: {lang}")
    if director and director != "N/A":
        lines.append(f"🎬 Director: {director}")
    if plot and plot != "N/A":
        lines.append(f"\n📖 {plot}")
    lines.append("\n━━━━━━━━━━━━━━━")
    lines.append("📥 *Movie Download Karein:*")
    lines.append(f"👉 [Yahan Click Karein]({msg_link})")
    lines.append("━━━━━━━━━━━━━━━")
    lines.append("🔔 *Nai Movies ke liye Follow Karein!*")
    return "\n".join(lines)

def build_caption_fallback(raw_name: str, msg_link: str) -> str:
    return (
        f"🎬 *{raw_name}*\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📥 *Movie Download Karein:*\n"
        f"👉 [Yahan Click Karein]({msg_link})\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔔 *Nai Movies ke liye Follow Karein!*"
    )

# ─── SEND TO UPDATE CHANNEL ───────────────────────────────────────────────────
async def post_to_update_channel(info: dict, msg_link: str, raw_name: str):
    caption = build_caption(info, msg_link, raw_name) if info else build_caption_fallback(raw_name, msg_link)
    poster_url = info.get("Poster") if info else None

    try:
        if poster_url and poster_url != "N/A":
            # Download poster
            async with aiohttp.ClientSession() as session:
                async with session.get(poster_url) as r:
                    if r.status == 200:
                        img_bytes = await r.read()
                        await client.send_file(
                            UPDATE_CHANNEL,
                            file=img_bytes,
                            caption=caption,
                            parse_mode='md',
                            attributes=[],
                            force_document=False
                        )
                        logger.info(f"✅ Posted with poster: {raw_name}")
                        return
        # No poster fallback
        await client.send_message(UPDATE_CHANNEL, caption, parse_mode='md', link_preview=True)
        logger.info(f"✅ Posted (no poster): {raw_name}")
    except Exception as e:
        logger.error(f"Post error: {e}")
        try:
            await client.send_message(UPDATE_CHANNEL, caption, parse_mode='md')
        except Exception as e2:
            logger.error(f"Fallback post error: {e2}")

# ─── MESSAGE LINK BUILDER ────────────────────────────────────────────────────
def make_msg_link(channel_username: str, msg_id: int) -> str:
    username = channel_username.lstrip("@").lstrip("https://t.me/")
    return f"https://t.me/{username}/{msg_id}"

# ─── EVENT HANDLER ────────────────────────────────────────────────────────────
@client.on(events.NewMessage(chats=MOVIE_CHANNEL))
async def on_new_movie(event):
    msg = event.message
    logger.info(f"New message in movie channel: id={msg.id}")

    # Only process if it has media (movie file)
    if not msg.media:
        return

    # Get movie name from caption or document filename
    raw_caption = msg.message or ""
    filename = ""

    if isinstance(msg.media, MessageMediaDocument):
        doc = msg.media.document
        for attr in doc.attributes:
            if hasattr(attr, 'file_name') and attr.file_name:
                filename = attr.file_name
                break

    raw_name = raw_caption.strip() or filename

    if not raw_name:
        logger.info("No name found, skipping")
        return

    # Clean name
    result = clean_movie_name(raw_name)
    if isinstance(result, tuple):
        clean_name, year = result
    else:
        clean_name, year = result, None

    if not clean_name:
        logger.info("Could not extract movie name")
        return

    logger.info(f"Movie detected: '{clean_name}' ({year})")

    # Build message link
    msg_link = make_msg_link(MOVIE_CH_LINK, msg.id)

    # Fetch from OMDB
    info = await fetch_movie_info(clean_name, year)
    if info:
        logger.info(f"OMDB found: {info.get('Title')}")
    else:
        logger.warning(f"OMDB not found for: {clean_name}")

    # Post to update channel
    await asyncio.sleep(2)  # Small delay to avoid flood
    await post_to_update_channel(info, msg_link, clean_name)

# ─── START ────────────────────────────────────────────────────────────────────
async def main():
    logger.info("🤖 CineBot started! Monitoring movie channel...")
    logger.info(f"Movie Channel: {MOVIE_CHANNEL}")
    logger.info(f"Update Channel: {UPDATE_CHANNEL}")
    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
