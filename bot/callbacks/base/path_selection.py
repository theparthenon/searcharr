"""
Searcharr
Sonarr & Radarr Telegram Bot
Path Selection Utility
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from bot.callbacks.base.media_message import update_media_message
from bot.utils.conversation import get_add_data, update_add_data, delete_conversation
from bot.utils.formatting import prepare_response
from bot.utils.text import translate
from bot.utils.log import set_up_logger

logger = set_up_logger("callbacks.base.path_selection")


async def check_path_selection(update, context, service, kind, convo, cid, i):
    """Check and handle root folder selection.
    
    Args:
        update: The update with the callback query
        context: The callback context
        service: The service client (Sonarr, Radarr)
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
    
    if not additional_data.get("p"):
        paths = service._root_folders
        if len(paths) > 1:
            # Need to prompt user to select a path
            reply_message, reply_markup = prepare_response(
                kind,
                r,
                cid,
                i,
                len(convo["results"]),
                add=True,
                paths=paths,
            )
            
            await update_media_message(
                query.message,
                r["remotePoster"],
                caption=reply_message,
                reply_markup=reply_markup
            )
            await query.answer()
            return False
        
        elif len(paths) == 1:
            # Only one path, use it automatically
            logger.debug(
                f"Only one root folder enabled. Adding/Updating additional data for cid=[{cid}], key=[p], value=[{paths[0]['path']}]..."
            )
            update_add_data(cid, "p", paths[0]["path"])

        else:
            # No paths available, show error and cancel
            delete_conversation(cid)
            service_name = "Sonarr" if kind == "series" else "Radarr"
            await query.message.reply_text(
                translate(
                    "no_root_folders",
                    kind=translate(kind),
                    app=service_name
                )
            )
            await query.message.delete()
            await query.answer()
            return False
    else:
        # Path is already selected, but might be an ID that needs to be translated to a path
        try:
            int(additional_data.get("p"))
        except ValueError:
            # Value is already the full path
            pass
        else:
            # Translate id to actual path
            paths = service._root_folders
            path = next(
                (
                    p["path"]
                    for p in paths
                    if p["id"] == int(additional_data["p"])
                ),
                None,
            )
            logger.debug(
                f"Path id [{additional_data['p']}] lookup result: [{path}]"
            )
            if path:
                update_add_data(cid, "p", path)
    
    return True