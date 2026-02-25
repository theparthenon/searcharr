"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
Start Command Handler
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from bot.utils.auth import add_user, authenticated
from bot.utils.text import strip_entities, translate
from bot.utils.log import set_up_logger
import settings

logger = set_up_logger("commands.start")


async def start_command(update, context, bot):
    """Handle the /start command for authentication.
    
    Args:
        update: The update with the message
        context: The callback context
        bot: The SearcharrBot instance
    """
    logger.debug(f"Received start cmd from [{update.message.from_user.username}]")
    
    # Extract password from message
    password = strip_entities(update.message)
    
    # Check if it's an admin authentication
    if password and password == settings.searcharr_admin_password:
        # Add user as admin
        add_user(
            id=update.message.from_user.id,
            username=str(update.message.from_user.username),
            admin=1,
        )
        
        await update.message.reply_text(
            translate(
                "admin_auth_success",
                commands=" OR ".join(
                    [f"`/{c}`" for c in settings.searcharr_help_command_aliases]
                ),
            )
        )
    # Check if already authenticated
    elif authenticated(update.message.from_user.id):
        await update.message.reply_text(
            translate(
                "already_authenticated",
                commands=" OR ".join(
                    [f"`/{c}`" for c in settings.searcharr_help_command_aliases]
                ),
            )
        )
    # Check if it's a regular user authentication
    elif password == settings.searcharr_password:
        # Add user
        add_user(
            id=update.message.from_user.id,
            username=str(update.message.from_user.username),
        )
        
        await update.message.reply_text(
            translate(
                "auth_successful",
                commands=" OR ".join(
                    [f"`/{c}`" for c in settings.searcharr_help_command_aliases]
                ),
            )
        )
    # Invalid password
    else:
        await update.message.reply_text(translate("incorrect_pw"))