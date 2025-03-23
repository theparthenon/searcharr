"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
Quality Profile Selection Utility
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from bot.callbacks.base.media_message import update_media_message
from bot.utils.conversation import get_add_data, update_add_data, delete_conversation
from bot.utils.formatting import prepare_response
from bot.utils.text import translate
from bot.utils.log import set_up_logger

logger = set_up_logger("callbacks.base.quality_selection", False, False)


async def check_quality_selection(update, context, service, kind, convo, cid, i):
    """Check and handle quality profile selection.
    
    Args:
        update: The update with the callback query
        context: The callback context
        service: The service client (Sonarr, Radarr, Readarr)
        kind: The content kind (series, movie, book)
        convo: The conversation data
        cid: The conversation ID
        i: The current index
        
    Returns:
        bool: True if we should continue to next step, False if we're waiting for user input
    """
    query = update.callback_query
    r = convo["results"][i]
    additional_data = get_add_data(cid)
    
    if not additional_data.get("q"):
        quality_profiles = service._quality_profiles
        if len(quality_profiles) > 1:
            # Need to prompt user to select a quality profile
            reply_message, reply_markup = prepare_response(
                kind,
                r,
                cid,
                i,
                len(convo["results"]),
                add=True,
                quality_profiles=quality_profiles,
            )

            await update_media_message(
                query.message,
                r["remotePoster"],
                caption=reply_message,
                reply_markup=reply_markup
            )
            await query.answer()
            return False
        elif len(quality_profiles) == 1:
            # Only one quality profile, use it automatically
            logger.debug(
                f"Only one quality profile enabled. Adding/Updating additional data for cid=[{cid}], key=[q], value=[{quality_profiles[0]['id']}]..."
            )
            update_add_data(cid, "q", quality_profiles[0]["id"])
        else:
            # No quality profiles available, show error and cancel
            delete_conversation(cid)
            service_name = "Sonarr" if kind == "series" else "Radarr" if kind == "movie" else "Readarr"
            await query.message.reply_text(
                translate(
                    "no_quality_profiles",
                    kind=translate(kind),
                    app=service_name
                )
            )
            await query.message.delete()
            await query.answer()
            return False
    
    return True