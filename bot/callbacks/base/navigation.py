"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
Navigation Utilities
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from bot.callbacks.base.media_message import update_media_message
from bot.utils.formatting import prepare_response
from bot.utils.log import set_up_logger

logger = set_up_logger("callbacks.base.navigation")


async def handle_navigation(update, context, kind, convo, cid, i, op):
    """Handle navigation callbacks (prev/next) for content browsing.
    
    Args:
        update: The update with the callback query
        context: The callback context
        kind: The content kind (series, movie, book)
        convo: The conversation data
        cid: The conversation ID
        i: The current index
        op: The operation ("prev" or "next")
        
    Returns:
        bool: True if handled, False if not applicable
    """
    query = update.callback_query
    
    if op == "prev":
        if i <= 0:
            await query.answer()
            return True
        
        # Get previous item
        r = convo["results"][i - 1]
        reply_message, reply_markup = prepare_response(
            kind, r, cid, i - 1, len(convo["results"])
        )
        
        await update_media_message(
            query.message,
            r["remotePoster"],
            caption=reply_message,
            reply_markup=reply_markup
        )
        
    elif op == "next":
        if i >= len(convo["results"]) - 1:
            await query.answer()
            return True
            
        # Get next item
        r = convo["results"][i + 1]
        reply_message, reply_markup = prepare_response(
            kind, r, cid, i + 1, len(convo["results"])
        )

        await update_media_message(
            query.message,
            r["remotePoster"],
            caption=reply_message,
            reply_markup=reply_markup
        )

    await query.answer()
    return True