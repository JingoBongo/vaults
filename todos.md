# Vault Module - Notes & Code Examples

## Overview

The `vaults` module provides a persistent key-value store backed by SQLite. It supports thread-safe operations, multiple serialization formats, and full Python dictionary protocol compatibility.

**Location**: `vaults/vaults.py` (271 lines)
**Tests**: `vaults/tests.py` (370 lines, 100% coverage)

---

## Quick Start

```python
from vaults import Vault, set_root_path

# Set where vault files will be stored
set_root_path('/path/to/data')

# Create a vault (auto-creates if not exists)
users = Vault('users')

# Dictionary-style API
users['alice'] = {'role': 'admin', 'active': True}
users['bob'] = {'role': 'user', 'active': False}

# Retrieve
print(users.get('alice'))           # {'role': 'admin', 'active': True}
print(users.get('charlie', {}))     # {} (default value)

# Check existence
print('alice' in users)             # True

# List all keys
print(users.list_keys())            # ['alice', 'bob']

# Iterate
for key in users:
    print(f"{key}: {users[key]}")

# Delete
del users['bob']
```

---

## Basic Operations

### put() / get()

```python
vault = Vault('settings')

# Store any Python object
vault.put('host', 'localhost')
vault.put('port', 5432)
vault.put('features', ['auth', 'cache', 'logging'])
vault.put('config', {'timeout': 30, 'retries': 3})

# Retrieve
host = vault.get('host')           # 'localhost'
port = vault.get('port')           # 5432
```

### pop() - Remove and Return

```python
vault = Vault('temp')

vault['session'] = 'abc123'
session = vault.pop('session')     # Returns 'abc123', removes key
print(vault.get('session'))        # None
```

### popitem() - Remove Arbitrary Item

```python
vault = Vault('queue')
vault['task1'] = {'data': 'first'}
vault['task2'] = {'data': 'second'}

key, value = vault.popitem()
# Returns random (key, value) pair, removes it from vault
```

### list_keys() / get_all_items()

```python
vault = Vault('data')
vault['a'] = 1
vault['b'] = 2
vault['c'] = 3

# List all keys
keys = vault.list_keys()           # ['a', 'b', 'c']

# Get all key-value pairs
items = vault.get_all_items()      # [('a', 1), ('b', 2), ('c', 3)]
```

### clear() - Empty Vault

```python
vault = Vault('cache')
vault['old'] = 'data'
vault.clear()
print(len(vault))                  # 0
```

### delete_vault() - Delete Entire Vault File

```python
vault = Vault('temporary')
vault['temp'] = 'data'
vault.delete_vault()               # Deletes 'temporary.db' file
```

---

## Dictionary Protocol

Vault implements Python's dict protocol for intuitive use:

```python
vault = Vault('items')

# Item access (raises KeyError if missing)
vault['key'] = 'value'
print(vault['key'])                # 'value'

# Deletion
del vault['key']

# Containment
print('key' in vault)              # False

# Length
print(len(vault))                  # 0

# Iteration (yields keys)
for key in vault:
    print(key)

# Boolean check
if vault:
    print("Vault has data")

# Keys, values, items
keys = vault.keys()                # List of keys
values = vault.values()            # List of values
items = vault.items()              # List of (key, value) tuples

# Update from dict
vault.update({'a': 1, 'b': 2})

# Set default
result = vault.setdefault('new_key', 'default')  # Returns 'default'
```

---

## Context Manager

```python
with Vault('transaction_test') as vault:
    vault['step1'] = 'done'
    vault['step2'] = 'done'
    # Changes auto-commit on exit

# Reopen and verify
vault2 = Vault('transaction_test', to_create=False)
print(vault2['step1'])             # 'done'
```

---

## Thread Safety

```python
# Thread-safe mode uses RLock for concurrent access
vault = Vault('shared_data', thread_safe=True)

import threading

def worker(name, value):
    vault[name] = value

threads = []
for i in range(10):
    t = threading.Thread(target=worker, args=(f'key_{i}', i))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print(len(vault))                  # 10 (all writes succeeded)
```

---

## Serialization Support

Vault automatically handles various Python types:

```python
vault = Vault('types')

# Primitives
vault['string'] = 'hello'
vault['int'] = 42
vault['float'] = 3.14159
vault['bool'] = True
vault['none'] = None

# Collections
vault['list'] = [1, 2, 3]
vault['tuple'] = (1, 2, 3)         # Returns as list on retrieval
vault['dict'] = {'nested': 'value'}

# Unicode
vault['russian'] = 'привет'
vault['emoji'] = '👋'

# Large data
vault['large'] = 'x' * 100000      # 100KB string

# Special characters
vault['special'] = '!@#$%^&*()_+-=[]{}|;\':",./<>?'
```

---

## Error Handling

```python
from vaults import Vault, VaultError

# Accessing non-existent vault (to_create=False)
try:
    vault = Vault('missing', to_create=False)
except VaultError as e:
    print(f"Vault doesn't exist: {e}")

# KeyError on missing item
vault = Vault('test')
vault['key'] = 'value'
del vault['key']

try:
    _ = vault['missing']
except KeyError:
    print("Key not found")

# popitem() on empty vault
try:
    vault.popitem()
except VaultError as e:
    print("Vault is empty")
```

---

## Common Patterns

### Configuration Store

```python
config = Vault('app_config')

# Load defaults
config.setdefault('debug', False)
config.setdefault('max_connections', 100)
config.setdefault('api_url', 'https://api.example.com')

# Runtime updates
if config['debug']:
    print("Debug mode enabled")
```

### Cache with TTL Concept (Manual)

```python
cache = Vault('cache')

def get_cached(key):
    entry = cache.get(key)
    if entry:
        value, timestamp = entry
        if time.time() - timestamp < 3600:  # 1 hour
            return value
        else:
            del cache[key]  # Expired
    return None

def set_cached(key, value):
    cache[key] = (value, time.time())
```

### Session Store

```python
sessions = Vault('sessions')

def create_session(user_id):
    import uuid
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        'user_id': user_id,
        'created': time.time(),
        'last_activity': time.time()
    }
    return session_id

def validate_session(session_id):
    data = sessions.get(session_id)
    if data:
        data['last_activity'] = time.time()
        sessions[session_id] = data
        return data
    return None
```

### Counter

```python
counter = Vault('counter')

def increment(name):
    current = counter.get(name, 0)
    counter[name] = current + 1
    return counter[name]

def decrement(name):
    current = counter.get(name, 0)
    counter[name] = current - 1
    return counter[name]
```

---

## Fuse Integration Examples

In Fuse, vaults are used for different purposes:

```python
# Virtual environment paths
venvs_vault = Vault('virtual_environments')
venvs_vault.put('default_venv', '/path/to/fuse_core/venvs/default_venv')

# Repository configurations
remote_repos_vault = Vault('remote_runnables_repositories')
remote_repos_vault.put('myrepo', {
    'url': 'https://github.com/user/repo',
    'name': 'myrepo',
    'instructions': ['{default_venv} main.py'],
    'PID': None,
    'status': 'stopped'
})

# Shared state
commons_vault = Vault('commons')
commons_vault.put('streamlit_enabled', 'True')
commons_vault.put('node_name', 'home-server')

# Notes
notes_vault = Vault('notes')
notes_vault.put('note', 'Remember to backup weekly')
```

---

## File Structure

```
vaults/
├── vaults.py      # Core implementation (271 lines)
├── tests.py       # Test suite (370 lines)
└── __init__.py    # Package init (empty)
```

---

## Performance Considerations

| Operation | Complexity |
|-----------|------------|
| put() / get() | O(1) |
| pop() | O(1) |
| list_keys() | O(n) |
| get_all_items() | O(n) |
| clear() | O(n) |

---

## TODOs & Improvements

### Clarifications (Updated 2024)

#### TTL/Expiration - How It Works

Two approaches exist:

**Lazy Expiration** (recommended for Fuse):
- Check expiration only on `get()`
- Expired data remains until accessed
- Requires periodic cleanup job

```python
def cleanup_expired(self) -> int:
    """Remove all expired TTL entries. Returns count deleted."""
    import time
    now = time.time()
    cursor = self._execute("SELECT key, value FROM dict")
    expired_keys = []
    for row in cursor.fetchall():
        value = _deserialize(row[1])
        if isinstance(value, dict) and 'expires_at' in value:
            if now > value['expires_at']:
                expired_keys.append(_deserialize(row[0]))
    for key in expired_keys:
        self._pop(key)
    return len(expired_keys)
```

**Active Expiration** (background thread):
- Adds daemon thread that periodically cleans up
- More complete but more complex
- Not recommended for Fuse's use case

**Use in Fuse**: Lazy approach with periodic cleanup is sufficient.

---

#### Encryption at Rest

**Library**: Fernet from `cryptography` package
- AES-128-CBC encryption
- HMAC-SHA256 authentication
- Random IV each time
- **Not built-in**, requires: `pip install cryptography`

**Performance**: Negligible (microseconds for KB-sized data)

**Implementation**: Use separate class, NOT a boolean flag:

```python
class EncryptedVault:
    """Wrapper that encrypts all data before storing in Vault."""

    def __init__(self, vault_name: str, key: bytes = None):
        self._inner = Vault(vault_name)
        self._key = key or Fernet.generate_key()
        self._cipher = Fernet(self._key)

    def put(self, key: Any, value: Any) -> None:
        encrypted = self._cipher.encrypt(pickle.dumps(value))
        self._inner.put(key, encrypted)

    def get(self, key: Any, default: Any = None) -> Any:
        raw = self._inner.get(key)
        if raw is None:
            return default
        return pickle.loads(self._cipher.decrypt(raw))
```

**Why separate class**: Forces explicit opt-in, prevents accidental decryption failure.

---

#### Connection Pooling - REMOVED FROM TODOs

**Reason**: Vaults are designed as standalone, offline dictionaries. Connection pooling is NOT a vaults concern.

If needed, implement at Fuse level:

```python
class VaultManager:
    """Singleton vault manager at Fuse level."""
    _vaults = {}

    @classmethod
    def get_vault(cls, name: str) -> Vault:
        if name not in cls._vaults:
            cls._vaults[name] = Vault(name)
        return cls._vaults[name]
```

**Conclusion**: Remove connection pooling from vaults TODOs.

---

#### Export/Import - Clarification

**Fact**: Copying `.db` files works perfectly and IS the export.

```python
import shutil
shutil.copy('vaults/virtual_environments.db', 'backup.db')  # Export
shutil.copy('backup.db', 'vaults/virtual_environments.db')  # Import
```

**When JSON export is useful**:
- Human-readable inspection
- Migration between Python versions (pickle compatibility)
- Sharing configurations between Fuse instances
- Version control of configurations

**Binary data problem**: Vaults store pickled data (binary). JSON export requires base64 encoding:

```python
def export_base64(self) -> Dict[str, str]:
    """Export as base64-encoded JSON (not human-readable)."""
    items = self.get_all_items()
    return {
        'format': 'vaults-base64-v1',
        'data': {
            base64.b64encode(self._serialize(k)).decode(): 
            base64.b64encode(self._serialize(v)).decode()
            for k, v in items
        }
    }
```

**Recommendation for Fuse**: Copying `.db` files is sufficient. JSON export is optional low priority.

---

## Best Practices

1. **Use thread_safe=True** when multiple threads access the same vault
2. **Use context manager** (`with Vault(...) as v:`) for atomic batch operations
3. **Don't store extremely large objects** - SQLite has size limits
4. **Back up vault files** (just `.db` files) for data recovery
5. **Use meaningful vault names** - they become filenames
6. **Close vaults properly** - rely on context manager or explicit close

---

## Migration Guide

### From v1 to v2 (if bulk ops are added)

```python
# Old way
for key, value in data.items():
    vault.put(key, value)

# New way
vault.put_many(data)
```

---

## References

- SQLite3 Python documentation: https://docs.python.org/3/library/sqlite3.html
- Pickle protocol: https://docs.python.org/3/library/pickle.html
- msgpack-python: https://msgpack-python.readthedocs.io/
