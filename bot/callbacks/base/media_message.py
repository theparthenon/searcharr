"""
Searcharr
Sonarr & Radarr Telegram Bot
Photo Media Utilities
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from telegram import InputMediaPhoto
from telegram.error import BadRequest
from bot.utils.log import set_up_logger

logger = set_up_logger("callbacks.base.media_message")

async def update_media_message(message, media_url, caption=None, reply_markup=None, fallback_url="https://artworks.thetvdb.com/banners/images/missing/movie.jpg"):
    """Sends or edits a message with photo media, falling back to a default image if the original fails.
    
    Args:
        message: The telegram message object to edit
        media_url: The URL of the image to use
        caption: Optional caption for the photo
        reply_markup: Optional reply markup for the message
        fallback_url: URL to use if the primary image fails to load
        
    Returns:
        The result of the message edit operation
    """
    try:
        return await message.edit_media(
            media=InputMediaPhoto(
                media_url,
                caption=caption
            ),
            reply_markup=reply_markup,
        )
    except BadRequest as e:
        if str(e) in [
            "Wrong type of the web page content",
            "Wrong file identifier/http url specified",
            "Media_empty",
        ]:
            logger.error(
                f"Error sending photo [{media_url}]: BadRequest: {e}. Attempting to send with default poster..."
            )
            return await message.edit_media(
                media=InputMediaPhoto(
                    fallback_url,
                    caption=caption
                ),
                reply_markup=reply_markup,
            )
        else:
            raise