"""
Searcharr
Sonarr & Radarr Telegram Bot
Anime Command Handler
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from telegram.error import BadRequest

from bot.utils.conversation import generate_cid, create_conversation
from bot.utils.auth import authenticated
from bot.utils.text import strip_entities, translate
from bot.utils.formatting import prepare_response
import settings


async def anime_command(update, context, bot):
    """Handle the /anime command to search for and add Anime series."""
    logger = bot.logger
    logger.debug(f"Received anime cmd from [{update.message.from_user.username}]")

    # Check authentication
    if not authenticated(update.message.from_user.id):
        await update.message.reply_text(
            translate(
                "auth_required",
                commands=" OR ".join(
                    [
                        f"`/{c} <{translate('password')}>`"
                        for c in settings.searcharr_start_command_aliases
                    ]
                ),
            )
        )
        return

    # Check if sonarr is enabled
    if not settings.sonarr_enabled:
        await update.message.reply_text(translate("anime_disabled"))
        return

    # Extract title from message
    title = strip_entities(update.message)
    if not title:
        x_title = translate("title").title()
        await update.message.reply_text(
            translate(
                "include_anime_title_in_cmd",
                commands=" OR ".join(
                    [
                        f"`/{c} {x_title}`"
                        for c in settings.anime_series_command_aliases
                    ]
                ),
            )
        )
        return

    # Look up series
    results = bot.anime.lookup_series(title)

    # Handle no results before touching the database
    if not results:
        await update.message.reply_text(translate("no_matching_series"))
        return

    cid = generate_cid()
    if not cid:
        await update.message.reply_text(translate("unexpected_error"))
        return

    create_conversation(
        id=cid,
        username=str(update.message.from_user.username),
        kind="anime",
        results=results,
    )

    # Prepare response for first result
    r = results[0]
    reply_message, reply_markup = prepare_response(
        "anime", r, cid, 0, len(results)
    )

    # Send response with photo
    try:
        await context.bot.sendPhoto(
            chat_id=update.message.chat.id,
            photo=r["remotePoster"],
            caption=reply_message,
            reply_markup=reply_markup,
        )
    except BadRequest as e:
        if str(e) in [
            "Wrong type of the web page content",
            "Wrong file identifier/http url specified",
            "Media_empty",
        ]:
            logger.error(
                f"Error sending photo [{r['remotePoster']}]: BadRequest: {e}. Attempting to send with default poster..."
            )
            await context.bot.sendPhoto(
                chat_id=update.message.chat.id,
                photo="https://artworks.thetvdb.com/banners/images/missing/movie.jpg",
                caption=reply_message,
                reply_markup=reply_markup,
            )
        else:
            raise