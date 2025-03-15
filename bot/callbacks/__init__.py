"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
Callback Handlers
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from urllib.parse import parse_qsl

from bot.utils.conversation import get_conversation
from bot.utils.auth import authenticated
from bot.utils.text import translate
from bot.callbacks.navigation import handle_navigation
from bot.callbacks.add_content import handle_add_content
from bot.callbacks.user_management import handle_user_management
from bot.callbacks.tags import handle_tags
from config import settings


def main_callback_handler(bot):
    """Create a callback handler function for the bot.
    
    Args:
        bot: The SearcharrBot instance
        
    Returns:
        function: The callback handler function
    """
    
    async def callback_handler(update, context):
        """Handle all callback queries.
        
        Args:
            update: The update with the callback query
            context: The callback context
        """
        query = update.callback_query
        logger = bot.logger
        logger.debug(
            f"Received callback from [{query.from_user.username}]: [{query.data}]"
        )
        
        # Check authentication
        auth_level = authenticated(query.from_user.id)
        if not auth_level:
            await query.message.reply_text(
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
            await query.message.delete()
            await query.answer()
            return

        # Validate callback data
        if not query.data or not query.data.strip():
            await query.answer()
            return

        # Parse the callback data
        parts = query.data.split("^^^")
        if len(parts) != 3:
            await query.answer()
            return
            
        cid, i, op = parts
        i = int(i)
        
        # Parse additional operation flags if present
        op_flags = {}
        if "^^" in op:
            op, op_flags_str = op.split("^^")
            op_flags = dict(parse_qsl(op_flags_str))
        
        # Get the conversation
        convo = get_conversation(cid)
        if not convo:
            await query.message.reply_text(translate("convo_not_found"))
            await query.message.delete()
            await query.answer()
            return
            
        # Route to appropriate handler
        if op == "noop":
            # No operation, just acknowledge
            pass
            
        elif op == "cancel" or op == "done":
            # Cancel search or finish operation
            from bot.callbacks.cancel import handle_cancel
            await handle_cancel(update, context, bot, convo, cid, i, op)
            
        elif op == "prev" or op == "next":
            # Handle navigation
            await handle_navigation(update, context, bot, convo, cid, i, op)
            
        elif op == "add":
            # Handle adding content
            await handle_add_content(update, context, bot, convo, cid, i, op, op_flags)
            
        elif op in ["remove_user", "make_admin", "remove_admin"]:
            # Handle user management
            await handle_user_management(update, context, bot, convo, cid, i, op)
            
        # Always answer the callback query to clear the loading indicator
        await query.answer()
        
    return callback_handler