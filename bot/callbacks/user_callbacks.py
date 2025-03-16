"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
User Management Callback Handlers
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from bot.utils.auth import remove_user, update_admin_access, get_users, authenticated
from bot.utils.conversation import create_conversation
from bot.utils.formatting import prepare_response_users
from bot.utils.text import translate
from bot.utils.log import set_up_logger
from bot.callbacks.base import handle_cancel
from config import settings

logger = set_up_logger("callbacks.user_management", False, False)


async def handle_user_callback(update, context, bot, convo, cid, i, op, op_flags):
    """Handle callbacks related to user management.
    
    Args:
        update: The update with the callback query
        context: The callback context
        bot: The SearcharrBot instance
        convo: The conversation data
        cid: The conversation ID
        i: The current index (user ID in this case)
        op: The operation
        op_flags: Additional operation flags
    """
    query = update.callback_query
    
    # Handle common operations
    if op in ["cancel", "done"]:
        await handle_cancel(update, context, convo, cid, i, op)
        return
    
    # For user management, i is actually the user_id
    user_id = i
    
    # Check if user has admin privileges
    auth_level = await check_admin_auth(update, context)
    if auth_level != 2:
        return
    
    # Handle different operations
    try:
        if op == "remove_user":
            await handle_remove_user(update, context, convo, cid, user_id)
        elif op == "make_admin":
            await handle_make_admin(update, context, convo, cid, user_id)
        elif op == "remove_admin":
            await handle_remove_admin(update, context, convo, cid, user_id)
        elif op == "prev" or op == "next":
            await handle_user_navigation(update, context, convo, cid, i, op)
        else:
            # For unknown operations, just answer the callback query
            await query.answer()
    except Exception as e:
        logger.error(f"Error in user management callback: {e}")
        await query.message.reply_text(translate("unexpected_error"))
        await query.answer()


async def check_admin_auth(update, context):
    """Check if the user has admin privileges.
    
    Args:
        update: The update with the callback query
        context: The callback context
        
    Returns:
        int: The authentication level (2 for admin)
    """
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
        
        await query.answer()
    except Exception as e:
        logger.error(f"Error removing all access for user id [{user_id}]: {e}")
        await query.message.reply_text(
            translate("unknown_error_removing_user", user=user_id)
        )
        await query.answer()


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
        
        await query.answer()
    except Exception as e:
        logger.error(f"Error adding admin access for user id [{user_id}]: {e}")
        await query.message.reply_text(
            translate("unknown_error_adding_admin", user=user_id)
        )
        await query.answer()


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
        
        await query.answer()
    except Exception as e:
        logger.error(f"Error removing admin access for user id [{user_id}]: {e}")
        await query.message.reply_text(
            translate("unknown_error_removing_admin", user=user_id)
        )
        await query.answer()


async def handle_user_navigation(update, context, convo, cid, offset, op):
    """Handle navigation for user management (prev/next pages).
    
    Args:
        update: The update with the callback query
        context: The callback context
        convo: The conversation data
        cid: The conversation ID
        offset: The current offset (page)
        op: The operation ("prev" or "next")
    """
    query = update.callback_query
    page_size = 5  # Number of users per page
    
    # Calculate new offset
    if op == "prev":
        new_offset = max(0, offset - page_size)
    elif op == "next":
        new_offset = min(len(convo["results"]) - 1, offset + page_size)
    else:
        new_offset = offset
    
    # Prepare response for users page
    reply_message, reply_markup = prepare_response_users(
        cid,
        convo["results"],
        new_offset,
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
    
    await query.answer()