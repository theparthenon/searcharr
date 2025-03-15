"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
User Management Callback Handler
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from bot.utils.auth import remove_user, update_admin_access, get_users
from bot.utils.conversation import create_conversation
from bot.utils.formatting import prepare_response_users
from bot.utils.text import translate
from bot.utils.log import set_up_logger
from config import settings

logger = set_up_logger("callbacks.user_management", False, False)


async def handle_user_management(update, context, bot, convo, cid, i, op):
    """Handle user management callbacks.
    
    Args:
        update: The update with the callback query
        context: The callback context
        bot: The SearcharrBot instance
        convo: The conversation data
        cid: The conversation ID
        i: The current index (user ID in this case)
        op: The operation ("remove_user", "make_admin", or "remove_admin")
    """
    query = update.callback_query
    user_id = i  # The i parameter is the user ID in user management callbacks
    
    # Check if user has admin privileges
    auth_level = await check_admin_auth(update, context)
    if auth_level != 2:
        return
    
    # Handle the different operations
    try:
        if op == "remove_user":
            await handle_remove_user(update, context, convo, cid, user_id)
        elif op == "make_admin":
            await handle_make_admin(update, context, convo, cid, user_id)
        elif op == "remove_admin":
            await handle_remove_admin(update, context, convo, cid, user_id)
    except Exception as e:
        logger.error(f"Error in user management callback: {e}")
        await query.message.reply_text(translate("unexpected_error"))


async def check_admin_auth(update, context):
    """Check if the user has admin privileges.
    
    Args:
        update: The update with the callback query
        context: The callback context
        
    Returns:
        int: The authentication level (2 for admin)
    """
    from bot.utils.auth import authenticated
    
    query = update.callback_query
    auth_level = authenticated(query.from_user.id)
    
    if auth_level != 2:
        await query.message.reply_text(
            translate(
                "admin_auth_required",
                commands=" OR ".join(
                    [
                        f"`/{c} <{translate('admin_password')}>`"
                        for c in settings.searcharr_start_command_aliases
                    ]
                ),
            )
        )
        await query.message.delete()
        await query.answer()
    
    return auth_level


async def handle_remove_user(update, context, convo, cid, user_id):
    """Handle the remove_user operation.
    
    Args:
        update: The update with the callback query
        context: The callback context
        convo: The conversation data
        cid: The conversation ID
        user_id: The user ID to remove
    """
    query = update.callback_query
    
    try:
        # Remove the user
        remove_user(user_id)
        
        # Update the conversation with fresh user data
        updated_users = get_users()
        create_conversation(
            id=cid,
            username=str(query.from_user.username),
            kind="users",
            results=updated_users,
        )
        
        # Prepare updated user list response
        reply_message, reply_markup = prepare_response_users(
            cid,
            updated_users,
            0,
            5,
            len(updated_users),
        )
        
        # Update the message
        await context.bot.edit_message_text(
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text=f"{translate('removed_user', user=user_id)} {reply_message}",
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.error(f"Error removing all access for user id [{user_id}]: {e}")
        await query.message.reply_text(
            translate("unknown_error_removing_user", user=user_id)
        )


async def handle_make_admin(update, context, convo, cid, user_id):
    """Handle the make_admin operation.
    
    Args:
        update: The update with the callback query
        context: The callback context
        convo: The conversation data
        cid: The conversation ID
        user_id: The user ID to make admin
    """
    query = update.callback_query
    
    try:
        # Make the user an admin
        update_admin_access(user_id, 1)
        
        # Update the conversation with fresh user data
        updated_users = get_users()
        create_conversation(
            id=cid,
            username=str(query.from_user.username),
            kind="users",
            results=updated_users,
        )
        
        # Prepare updated user list response
        reply_message, reply_markup = prepare_response_users(
            cid,
            updated_users,
            0,
            5,
            len(updated_users),
        )
        
        # Update the message
        await context.bot.edit_message_text(
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text=f"{translate('added_admin_access', user=user_id)} {reply_message}",
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.error(f"Error adding admin access for user id [{user_id}]: {e}")
        await query.message.reply_text(
            translate("unknown_error_adding_admin", user=user_id)
        )


async def handle_remove_admin(update, context, convo, cid, user_id):
    """Handle the remove_admin operation.
    
    Args:
        update: The update with the callback query
        context: The callback context
        convo: The conversation data
        cid: The conversation ID
        user_id: The user ID to remove admin privileges from
    """
    query = update.callback_query
    
    try:
        # Remove admin privileges
        update_admin_access(user_id, "")
        
        # Update the conversation with fresh user data
        updated_users = get_users()
        create_conversation(
            id=cid,
            username=str(query.from_user.username),
            kind="users",
            results=updated_users,
        )
        
        # Prepare updated user list response
        reply_message, reply_markup = prepare_response_users(
            cid,
            updated_users,
            0,
            5,
            len(updated_users),
        )
        
        # Update the message
        await context.bot.edit_message_text(
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text=f"{translate('removed_admin_access', user=user_id)} {reply_message}",
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.error(f"Error removing admin access for user id [{user_id}]: {e}")
        await query.message.reply_text(
            translate("unknown_error_removing_admin", user=user_id)
        )