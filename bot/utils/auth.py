"""
Searcharr
Sonarr, Radarr & Readarr Telegram Bot
Authentication Utilities
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
from bot.utils.database import execute_query, execute_insert, get_connection
from bot.utils.log import set_up_logger

logger = set_up_logger("auth")


def add_user(id, username, admin=""):
    """Add or update a user in the database.
    
    Args:
        id (int): The user ID
        username (str): The username
        admin (str, optional): Admin status. Defaults to "".
        
    Returns:
        bool: True on success, False on failure
    """
    q = "INSERT OR REPLACE INTO users (id, username, admin) VALUES (?, ?, ?);"
    qa = (id, username, admin)
    
    result = execute_insert(q, qa)
    return result


def remove_user(id):
    """Remove a user from the database.
    
    Args:
        id (int): The user ID
        
    Returns:
        bool: True on success, False on failure
    """
    q = "DELETE FROM users where id=?;"
    qa = (id,)
    
    result = execute_insert(q, qa)
    return result


def get_users(admin=False):
    """Get all users or admin users from the database.
    
    Args:
        admin (bool, optional): Only get admin users. Defaults to False.
        
    Returns:
        list: List of user dictionaries
    """
    admin_clause = " where IFNULL(admin, '') != ''" if admin else ""
    q = f"SELECT * FROM users{admin_clause};"
    
    try:
        con, cur = get_connection()
        r = cur.execute(q)
        records = r.fetchall()
        con.close()
        return records
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return []


def update_admin_access(user_id, admin=""):
    """Update a user's admin access.
    
    Args:
        user_id (int): The user ID
        admin (str, optional): Admin status. Defaults to "".
        
    Returns:
        bool: True on success, False on failure
    """
    q = "UPDATE users set admin=? where id=?;"
    qa = (str(admin), user_id)
    
    result = execute_insert(q, qa)
    return result


def authenticated(user_id):
    """Check if a user is authenticated.
    
    Args:
        user_id (int): The user ID
        
    Returns:
        int: 2 if admin, 1 if regular user, 0 if not authenticated
    """
    q = "SELECT * FROM users WHERE id=?;"
    qa = (user_id,)
    
    try:
        con, cur = get_connection()
        r = cur.execute(q, qa)
        record = r.fetchone()
        
        logger.debug(f"Query result for user lookup: {record}")
        con.close()
        
        if record and record["id"] == user_id:
            return 2 if record["admin"] else 1
    except Exception as e:
        logger.error(f"Error checking authentication: {e}")
    
    logger.debug(f"Did not find user [{user_id}] in the database.")
    return 0