"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
Cancel/Done Callback Handler
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from bot.utils.conversation import delete_conversation
from bot.utils.text import translate
from bot.utils.log import set_up_logger

logger = set_up_logger("callbacks.cancel", False, False)


async def handle_cancel(update, context, bot, convo, cid, i, op):
    """Handle cancel and done callbacks.
    
    Args:
        update: The update with the callback query
        context: The callback context
        bot: The SearcharrBot instance
        convo: The conversation data
        cid: The conversation ID
        i: The current index
        op: The operation ("cancel" or "done")
    """
    query = update.callback_query
    
    # Delete the conversation from the database
    delete_conversation(cid)
    
    if op == "cancel":
        # Send cancellation message
        await query.message.reply_text(translate("search_canceled"))
    
    # Delete the message
    await query.message.delete()