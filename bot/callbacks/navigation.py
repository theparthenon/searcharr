"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
Navigation Callback Handler
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from telegram import InputMediaPhoto
from telegram.error import BadRequest

from bot.utils.formatting import prepare_response, prepare_response_users
from bot.utils.log import set_up_logger

logger = set_up_logger("callbacks.navigation", False, False)


async def handle_navigation(update, context, bot, convo, cid, i, op):
    """Handle navigation callbacks (prev/next).
    
    Args:
        update: The update with the callback query
        context: The callback context
        bot: The SearcharrBot instance
        convo: The conversation data
        cid: The conversation ID
        i: The current index
        op: The operation ("prev" or "next")
    """
    query = update.callback_query
    
    if convo["type"] in ["series", "movie", "book"]:
        # Handle navigation for content
        if op == "prev":
            if i <= 0:
                await query.answer()
                return
            
            # Get previous item
            r = convo["results"][i - 1]
            reply_message, reply_markup = prepare_response(
                convo["type"], r, cid, i - 1, len(convo["results"])
            )
            
            # Update message with new content
            try:
                await query.message.edit_media(
                    media=InputMediaPhoto(r["remotePoster"]),
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
                    await query.message.edit_media(
                        media=InputMediaPhoto(
                            "https://artworks.thetvdb.com/banners/images/missing/movie.jpg"
                        ),
                        reply_markup=reply_markup,
                    )
                else:
                    raise
                    
            await query.bot.edit_message_caption(
                chat_id=query.message.chat_id,
                message_id=query.message.message_id,
                caption=reply_message,
                reply_markup=reply_markup,
            )
            
        elif op == "next":
            if i >= len(convo["results"]) - 1:
                await query.answer()
                return
                
            # Get next item
            r = convo["results"][i + 1]
            reply_message, reply_markup = prepare_response(
                convo["type"], r, cid, i + 1, len(convo["results"])
            )
            
            # Update message with new content
            try:
                await query.message.edit_media(
                    media=InputMediaPhoto(r["remotePoster"]),
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
                    await query.message.edit_media(
                        media=InputMediaPhoto(
                            "https://artworks.thetvdb.com/banners/images/missing/movie.jpg"
                        ),
                        reply_markup=reply_markup,
                    )
                else:
                    raise
                    
            await query.bot.edit_message_caption(
                chat_id=query.message.chat_id,
                message_id=query.message.message_id,
                caption=reply_message,
                reply_markup=reply_markup,
            )
            
    elif convo["type"] == "users":
        # Handle navigation for user management
        page_size = 5  # Number of users per page
        
        if op == "prev":
            if i <= 0:
                i = 0
                
        elif op == "next":
            if i > len(convo["results"]):
                await query.answer()
                return
                
        # Prepare response for users page
        reply_message, reply_markup = prepare_response_users(
            cid,
            convo["results"],
            i,
            page_size,
            len(convo["results"]),
        )
        
        # Update message with new content
        await context.bot.edit_message_text(
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text=reply_message,
            reply_markup=reply_markup,
        )