import os
import pickle
import sqlite3
import threading
import logging
from logging.handlers import RotatingFileHandler
from typing import Any, Iterator, List, Tuple, Optional, Dict

try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False

log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler = RotatingFileHandler("vaults.log", maxBytes=10 * 1024 * 1024)
handler.setFormatter(log_formatter)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(handler)

_custom_logger = None

root_path = os.path.dirname(os.path.abspath(__file__))
vaults_folder = os.path.join(root_path, "vaults")


def set_root_path(path: str) -> None:
    """Set the root directory for vault storage.

    Creates the vaults subdirectory if it doesn't exist.

    Args:
        path: Directory path where vault files will be stored.

    Example:
        >>> set_root_path('/data/vaults')
    """
    global root_path, vaults_folder
    root_path = path
    vaults_folder = os.path.join(root_path, "vaults")
    os.makedirs(vaults_folder, exist_ok=True)
    log.info(f"Root path set to: {root_path}, vaults folder: {vaults_folder}")


def set_logger(logger: logging.Logger) -> None:
    """Configure a custom logger for the vaults module.

    By default, vaults uses its own logger. Call this function to redirect
    logs to your application's logger.

    Args:
        logger: Logger instance to use for vault operations.

    Example:
        >>> import logging
        >>> my_logger = logging.getLogger('vaults')
        >>> set_logger(my_logger)
    """
    global log, _custom_logger
    _custom_logger = logger
    log = logger
    log.info("Custom logger configured for vaults module.")


def _try_msgpack_serialize(obj: Any) -> Optional[bytes]:
    if not MSGPACK_AVAILABLE:
        return None
    try:
        return msgpack.packb(obj, use_bin_type=True)
    except (TypeError, ValueError):
        return None


def _serialize(obj: Any) -> bytes:
    packed = _try_msgpack_serialize(obj)
    if packed is not None:
        return b'M' + packed
    return b'P' + pickle.dumps(obj)


def _deserialize(data: bytes) -> Any:
    if not data:
        return None
    marker = data[0:1]
    if marker == b'M':
        if not MSGPACK_AVAILABLE:
            raise RuntimeError("msgpack not available but data is msgpack format")
        result = msgpack.unpackb(data[1:], raw=False)
    elif marker == b'P':
        result = pickle.loads(data[1:])
    else:
        raise ValueError(f"Unknown serialization format marker: {marker}")

    if isinstance(result, tuple):
        return list(result)
    return result


class VaultError(Exception):
    pass


class Vault:
    """Persistent key-value store backed by SQLite.

    Provides a dict-like interface with thread-safe operations and automatic
    serialization using msgpack (with pickle fallback).

    Args:
        vault_name: Name of the vault (creates `name.db` file).
        to_create: If False, raises VaultError if vault doesn't exist.
        thread_safe: If True, uses RLock for concurrent access.

    Example:
        >>> from vaults import Vault, set_root_path
        >>> set_root_path('/data')
        >>> v = Vault('my_data')
        >>> v['key'] = 'value'
        >>> v.get('key')
        'value'
    """
    __slots__ = {"vault_name", "db_path", "_connection", "_thread_safe", "_lock"}

    def __init__(self, vault_name: str, to_create: bool = True, thread_safe: bool = False) -> None:
        """Initialize a Vault instance.

        Args:
            vault_name: Name of the vault (creates `name.db` file).
            to_create: If False, raises VaultError if vault doesn't exist.
            thread_safe: If True, uses RLock for concurrent access.

        Raises:
            VaultError: If vault doesn't exist and to_create is False.
        """
        os.makedirs(vaults_folder, exist_ok=True)
        self.vault_name = vault_name
        self.db_path = os.path.join(vaults_folder, f"{vault_name}.db")
        self._thread_safe = thread_safe
        self._lock = threading.RLock() if thread_safe else None

        path_exists = os.path.exists(self.db_path)
        if path_exists or to_create:
            self._connection = sqlite3.connect(self.db_path, check_same_thread=not thread_safe)
            self._connection.isolation_level = None
        else:
            log.error(f"No such vault: '{vault_name}'!")
            raise VaultError(f"Vault '{vault_name}' does not exist")

        if to_create and not path_exists:
            log.info(f"Creating vault '{vault_name}'!")
            self._create_table()
        elif not path_exists and not to_create:
            log.error(f"No such vault: '{vault_name}'!")
            raise VaultError(f"Vault '{vault_name}' does not exist")

    def _create_table(self) -> None:
        log.debug("Creating table in the database.")
        try:
            self._execute("CREATE TABLE IF NOT EXISTS dict (key BLOB PRIMARY KEY, value BLOB)")
        except sqlite3.Error as e:
            log.error(f"Failed to create table: {e}")
            raise VaultError(f"Failed to create table: {e}")

    def _execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        try:
            cursor = self._connection.cursor()
            cursor.execute(query, params)
            return cursor
        except sqlite3.Error as e:
            log.error(f"Database error: {e}")
            raise VaultError(f"Database error: {e}")

    def _execute_with_lock(self, query: str, params: tuple = (())[0:0]) -> sqlite3.Cursor:
        if self._lock:
            with self._lock:
                return self._execute(query, params)
        return self._execute(query, params)

    def _put(self, key: Any, value: Any) -> None:
        log.debug(f"Putting key: {key} into vault.")
        serialized_key = _serialize(key)
        serialized_value = _serialize(value)
        try:
            self._execute_with_lock(
                "INSERT OR REPLACE INTO dict (key, value) VALUES (?, ?)",
                (serialized_key, serialized_value)
            )
        except VaultError:
            raise

    def put(self, key: Any, value: Any) -> None:
        self._put(key, value)
        log.info(f"Key stored in vault.")

    def _get(self, key: Any) -> Optional[Any]:
        log.debug(f"Retrieving key: {key} from vault.")
        serialized_key = _serialize(key)
        cursor = self._execute("SELECT value FROM dict WHERE key = ?", (serialized_key,))
        row = cursor.fetchone()
        return _deserialize(row[0]) if row else None

    def get(self, key: Any, default: Any = None) -> Any:
        value = self._get(key)
        if value is not None:
            log.info(f"Retrieved key from vault.")
        else:
            log.warning(f"Key not found in vault, returning default.")
            value = default
        return value

    def _pop(self, key: Any) -> Optional[Any]:
        log.debug(f"Popping key: {key} from vault.")
        serialized_key = _serialize(key)
        cursor = self._execute("SELECT value FROM dict WHERE key = ?", (serialized_key,))
        row = cursor.fetchone()
        if row:
            value = _deserialize(row[0])
            self._execute("DELETE FROM dict WHERE key = ?", (serialized_key,))
            log.info(f"Key removed from vault.")
            return value
        log.warning(f"Key not found for pop operation.")
        return None

    def pop(self, key: Any) -> Optional[Any]:
        value = self._pop(key)
        return value

    def put_many(self, data: Dict[Any, Any]) -> int:
        """Bulk insert or update multiple key-value pairs.

        Uses a single transaction for atomicity and efficiency.

        Args:
            data: Dictionary of key-value pairs to store.

        Returns:
            Number of items inserted/updated.

        Example:
            >>> v.put_many({'a': 1, 'b': 2, 'c': 3})
            3
        """
        log.debug(f"put_many: Bulk inserting {len(data)} items into vault '{self.vault_name}'.")
        if not data:
            log.info("put_many: No data to insert.")
            return 0

        serialized_items = [(_serialize(k), _serialize(v)) for k, v in data.items()]

        if self._lock:
            with self._lock:
                cursor = self._connection.cursor()
                cursor.executemany(
                    "INSERT OR REPLACE INTO dict (key, value) VALUES (?, ?)",
                    serialized_items
                )
        else:
            cursor = self._connection.cursor()
            cursor.executemany(
                "INSERT OR REPLACE INTO dict (key, value) VALUES (?, ?)",
                serialized_items
            )

        log.info(f"put_many: Inserted {len(serialized_items)} items into vault '{self.vault_name}'.")
        return len(serialized_items)

    def get_many(self, keys: List[Any]) -> Dict[Any, Any]:
        """Bulk fetch multiple values by keys.

        Returns only keys that exist in the vault.

        Args:
            keys: List of keys to retrieve.

        Returns:
            Dictionary containing only existing key-value pairs.

        Example:
            >>> v.put_many({'a': 1, 'b': 2, 'c': 3})
            >>> v.get_many(['a', 'b', 'missing'])
            {'a': 1, 'b': 2}
        """
        log.debug(f"get_many: Fetching {len(keys)} keys from vault '{self.vault_name}'.")
        if not keys:
            log.info("get_many: No keys to fetch.")
            return {}

        serialized_keys = [_serialize(k) for k in keys]
        placeholders = ','.join('?' * len(serialized_keys))

        cursor = self._execute(
            f"SELECT key, value FROM dict WHERE key IN ({placeholders})",
            tuple(serialized_keys)
        )

        result = {(_deserialize(row[0])): _deserialize(row[1]) for row in cursor.fetchall()}
        log.info(f"get_many: Retrieved {len(result)} items from vault '{self.vault_name}'.")
        return result

    def pop_many(self, keys: List[Any]) -> Dict[Any, Any]:
        """Bulk remove and return multiple key-value pairs.

        Logs a warning for keys that don't exist.

        Args:
            keys: List of keys to remove.

        Returns:
            Dictionary of removed key-value pairs.

        Example:
            >>> v.put_many({'a': 1, 'b': 2})
            >>> v.pop_many(['a'])
            {'a': 1}
        """
        log.debug(f"pop_many: Bulk removing {len(keys)} keys from vault '{self.vault_name}'.")
        if not keys:
            log.info("pop_many: No keys to remove.")
            return {}

        found = self.get_many(keys)
        if not found:
            log.warning("pop_many: No keys found to remove.")
            return {}

        serialized_keys = [_serialize(k) for k in found.keys()]
        placeholders = ','.join('?' * len(serialized_keys))

        self._execute(
            f"DELETE FROM dict WHERE key IN ({placeholders})",
            tuple(serialized_keys)
        )

        log.info(f"pop_many: Removed {len(found)} items from vault '{self.vault_name}'.")
        return found

    def has_keys(self, keys: List[Any]) -> bool:
        """Check if all specified keys exist in the vault.

        Args:
            keys: List of keys to check.

        Returns:
            True if all keys exist, False otherwise. Empty list returns True.

        Example:
            >>> v.put_many({'a': 1, 'b': 2})
            >>> v.has_keys(['a', 'b'])
            True
            >>> v.has_keys(['a', 'c'])
            False
        """
        log.debug(f"has_keys: Checking {len(keys)} keys in vault '{self.vault_name}'.")
        if not keys:
            log.info("has_keys: No keys to check.")
            return True

        serialized_keys = [_serialize(k) for k in keys]
        placeholders = ','.join('?' * len(serialized_keys))

        cursor = self._execute(
            f"SELECT COUNT(*) FROM dict WHERE key IN ({placeholders})",
            tuple(serialized_keys)
        )

        count = cursor.fetchone()[0]
        all_present = count == len(keys)
        log.info(f"has_keys: Checked {len(keys)} keys in vault '{self.vault_name}'. All present: {all_present}.")
        return all_present

    def popitem(self) -> Tuple[Any, Any]:
        log.debug(f"Popping arbitrary item from vault.")
        cursor = self._execute("SELECT key, value FROM dict LIMIT 1")
        row = cursor.fetchone()
        if row:
            key = _deserialize(row[0])
            value = _deserialize(row[1])
            self._execute("DELETE FROM dict WHERE key = ?", (row[0],))
            log.info(f"Popped item from vault.")
            return (key, value)
        raise VaultError("popitem(): dictionary is empty")

    def delete_vault(self) -> None:
        log.info(f"Deleting vault '{self.vault_name}'.")
        if self._connection:
            self._connection.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            log.info(f"Vault '{self.vault_name}' deleted successfully.")
        else:
            log.warning(f"Vault '{self.vault_name}' does not exist.")

    def clear(self) -> None:
        log.debug(f"Clearing all entries from vault '{self.vault_name}'.")
        self._execute("DELETE FROM dict")

    def _list_keys(self) -> List[Any]:
        log.debug(f"Listing all keys in vault '{self.vault_name}'.")
        cursor = self._execute("SELECT key FROM dict")
        return [_deserialize(row[0]) for row in cursor.fetchall()]

    def list_keys(self) -> List[Any]:
        keys = self._list_keys()
        log.info(f"Listed {len(keys)} keys from vault '{self.vault_name}'.")
        return keys

    def get_all_items(self) -> List[Tuple[Any, Any]]:
        log.debug(f"Fetching all items from vault '{self.vault_name}'.")
        cursor = self._execute("SELECT key, value FROM dict")
        return [(_deserialize(row[0]), _deserialize(row[1])) for row in cursor.fetchall()]

    def __getitem__(self, key: Any) -> Any:
        value = self._get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key: Any, value: Any) -> None:
        self._put(key, value)

    def __delitem__(self, key: Any) -> None:
        serialized_key = _serialize(key)
        cursor = self._execute("SELECT 1 FROM dict WHERE key = ?", (serialized_key,))
        if not cursor.fetchone():
            raise KeyError(key)
        self._execute("DELETE FROM dict WHERE key = ?", (serialized_key,))
        log.info(f"Key deleted from vault.")

    def __contains__(self, key: Any) -> bool:
        serialized_key = _serialize(key)
        cursor = self._execute("SELECT 1 FROM dict WHERE key = ? LIMIT 1", (serialized_key,))
        return cursor.fetchone() is not None

    def __len__(self) -> int:
        cursor = self._execute("SELECT COUNT(*) FROM dict")
        return cursor.fetchone()[0]

    def __iter__(self) -> Iterator[Any]:
        return iter(self._list_keys())

    def __bool__(self) -> bool:
        cursor = self._execute("SELECT 1 FROM dict LIMIT 1")
        return cursor.fetchone() is not None

    def __repr__(self) -> str:
        items = list(self.get_all_items())
        return f"Vault('{self.vault_name}', {len(items)} items)"

    def keys(self) -> List[Any]:
        return self._list_keys()

    def values(self) -> List[Any]:
        log.debug(f"Fetching all values from vault '{self.vault_name}'.")
        cursor = self._execute("SELECT value FROM dict")
        return [_deserialize(row[0]) for row in cursor.fetchall()]

    def items(self) -> List[Tuple[Any, Any]]:
        return self.get_all_items()

    def update(self, other: Dict[Any, Any]) -> None:
        for key, value in other.items():
            self._put(key, value)

    def setdefault(self, key: Any, default: Any = None) -> Any:
        serialized_key = _serialize(key)
        cursor = self._execute("SELECT value FROM dict WHERE key = ?", (serialized_key,))
        row = cursor.fetchone()
        if row:
            return _deserialize(row[0])
        self._put(key, default)
        return default

    def __enter__(self) -> "Vault":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._connection.commit()
