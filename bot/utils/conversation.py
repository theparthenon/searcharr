"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
Conversation Management Utilities
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
import json
import uuid

from bot.utils.database import execute_query, execute_insert, get_connection
from bot.utils.log import set_up_logger

logger = set_up_logger("conversation")


def generate_cid():
    """Generate a unique conversation ID.
    
    Returns:
        str: A unique conversation ID
    """
    q = "SELECT * FROM conversations WHERE id=?"
    con, cur = get_connection()
    while True:
        u = uuid.uuid4().hex[:8]
        try:
            r = cur.execute(q, (u,))
        except Exception as e:
            r = None
            logger.error(
                f"Error executing database query to check conversation id uniqueness [{q}]: {e}"
            )

        if not r:
            return None
        elif not len(r.fetchall()):
            con.close()
            return u
        else:
            logger.warning("Detected conversation id collision. Interesting.")


def create_conversation(id, username, kind, results):
    """Create or update a conversation in the database.
    
    Args:
        id (str): The conversation ID
        username (str): The username of the user
        kind (str): The type of conversation
        results (list): The results of the search
        
    Returns:
        bool: True on success, False on failure
    """
    q = "INSERT OR REPLACE INTO conversations (id, username, type, results) VALUES (?, ?, ?, ?)"
    qa = (id, username, kind, json.dumps(results))
    
    result = execute_insert(q, qa)
    return result


def get_conversation(id):
    """Get a conversation by ID.
    
    Args:
        id (str): The conversation ID
        
    Returns:
        dict: The conversation or None if not found
    """
    q = "SELECT * FROM conversations WHERE id=?;"
    qa = (id,)
    
    try:
        con, cur = get_connection()
        r = cur.execute(q, qa)
        record = r.fetchone()
        
        if record:
            logger.debug(f"Found conversation {record['id']} in the database")
            record.update({"results": json.loads(record["results"])})
        con.close()
        return record
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        return None


def delete_conversation(id):
    """Delete a conversation by ID.
    
    Args:
        id (str): The conversation ID
        
    Returns:
        bool: True on success, False on failure
    """
    # First clear associated additional data
    clear_add_data(id)
    
    # Then delete the conversation
    q = "DELETE FROM conversations WHERE id=?;"
    qa = (id,)
    
    result = execute_insert(q, qa)
    return result


def get_add_data(cid):
    """Get additional data for a conversation.
    
    Args:
        cid (str): The conversation ID
        
    Returns:
        dict: The additional data
    """
    q = "SELECT * FROM add_data WHERE cid=?;"
    qa = (cid,)
    
    try:
        con, cur = get_connection()
        r = cur.execute(q, qa)
        records = r.fetchall()
        con.close()
        
        logger.debug(f"Add data query response: {records}")
        return {x["key"]: x["value"] for x in records}
    except Exception as e:
        logger.error(f"Error getting add data: {e}")
        return {}


def update_add_data(cid, key, value):
    """Update additional data for a conversation.
    
    Args:
        cid (str): The conversation ID
        key (str): The data key
        value (str): The data value
        
    Returns:
        bool: True on success, False on failure
    """
    q = "INSERT OR REPLACE INTO add_data (cid, key, value) VALUES (?, ?, ?)"
    qa = (cid, key, value)
    
    result = execute_insert(q, qa)
    return result


def clear_add_data(cid):
    """Clear all additional data for a conversation.
    
    Args:
        cid (str): The conversation ID
        
    Returns:
        bool: True on success, False on failure
    """
    q = "DELETE FROM add_data WHERE cid=?;"
    qa = (cid,)
    
    result = execute_insert(q, qa)
    return result