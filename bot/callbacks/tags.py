"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
Tag Selection Callback Handler
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from telegram import InputMediaPhoto
from telegram.error import BadRequest

from bot.utils.conversation import get_add_data, update_add_data
from bot.utils.formatting import prepare_response
from bot.utils.log import set_up_logger
from config import settings

logger = set_up_logger("callbacks.tags", False, False)


async def handle_tags(update, context, bot, convo, cid, i, op, op_flags):
    """Handle tag selection callbacks.
    
    Args:
        update: The update with the callback query
        context: The callback context
        bot: The SearcharrBot instance
        convo: The conversation data
        cid: The conversation ID
        i: The current index
        op: The operation
        op_flags: Additional operation flags
    """
    query = update.callback_query
    
    # Get the content result
    r = convo["results"][i]
    
    # Return if no tag-related flags
    if not op_flags.get("tt") and not op_flags.get("td"):
        await query.answer()
        return
    
    # Get current additional data
    additional_data = get_add_data(cid)
    
    # Process a new tag selection
    if op_flags.get("tt"):
        tag_id = op_flags.get("tt")
        
        # Get current tags
        tag_ids = (
            additional_data.get("t", "").split(",")
            if len(additional_data.get("t", ""))
            else []
        )
        
        # Add new tag
        if tag_id not in tag_ids:
            tag_ids.append(tag_id)
            logger.debug(f"Adding tag [{tag_id}]")
            update_add_data(cid, "t", ",".join(tag_ids))
        
        # Determine which service to use for tag info
        if convo["type"] == "series":
            service = bot.sonarr
            user_selectable_tags = settings.sonarr_user_selectable_tags
            forced_tags = settings.sonarr_forced_tags
        elif convo["type"] == "movie":
            service = bot.radarr
            user_selectable_tags = settings.radarr_user_selectable_tags
            forced_tags = settings.radarr_forced_tags
        elif convo["type"] == "book":
            service = bot.readarr
            user_selectable_tags = settings.readarr_user_selectable_tags
            forced_tags = settings.readarr_forced_tags
        
        # Get all available tags
        all_tags = service.get_filtered_tags(
            user_selectable_tags,
            forced_tags,
        )
        
        # Prepare response with updated tag selection
        reply_message, reply_markup = prepare_response(
            convo["type"],
            r,
            cid,
            i,
            len(convo["results"]),
            add=True,
            tags=all_tags,
        )
        
        # Update the message
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
    
    # Process tag selection completion
    elif op_flags.get("td"):
        # Mark tag selection as done
        update_add_data(cid, "td", "1")
        
        # Return to add_content to proceed with next step
        from bot.callbacks.add_content import handle_add_content
        await handle_add_content(update, context, bot, convo, cid, i, op, {})
    
    await query.answer()