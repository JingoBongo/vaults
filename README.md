# Vaults

A persistent key-value store using SQLite with a dict-like interface. Fast, simple, and Pythonic.

## Features

- **Persistent storage** - Data survives process restarts via SQLite
- **Dict-like interface** - Use `vault['key'] = value` syntax
- **Fast serialization** - Uses msgpack for most types, falls back to pickle
- **No external dependencies** - Only msgpack (optional performance boost)
- **Thread-safe option** - Enable with `thread_safe=True`
- **Bulk operations** - Efficient `put_many()`, `get_many()`, `pop_many()`, `has_keys()`
- **Custom logging** - Integrate with your application's logger via `set_logger()`
- **Full dict protocol** - Supports `len()`, `in`, iteration, `keys()`, `values()`, `items()`, and more

## Installation

```bash
pip install vaults
```

Or for development with editable install:

```bash
pip install -e .
```

## Quick Start

```python
import vaults

# Set where vault files will be stored
vaults.set_root_path('/path/to/data')

# Create a vault (creates file if not exists)
v = vaults.Vault('my_data')

# Dict-style operations
v['name'] = 'Alice'
v['age'] = 30
v['settings'] = {'theme': 'dark', 'notifications': True}

# Read values
print(v['name'])           # Alice
print(v.get('age', 0))     # 30
print('theme' in v)        # True

# Get all data
print(v.keys())            # ['name', 'age', 'settings']
print(v.values())          # ['Alice', 30, {'theme': 'dark', ...}]
print(v.items())           # [('name', 'Alice'), ('age', 30), ...]

# Remove data
del v['age']
value = v.pop('name')      # Returns 'Alice'

# Cleanup
v.delete_vault()  # Deletes the vault file
```

## API Reference

### Creating a Vault

```python
Vault(name, to_create=True, thread_safe=False)
```

- `name` - Name of the vault (creates `name.db` file)
- `to_create` - If False, raises error if vault doesn't exist
- `thread_safe` - If True, uses RLock for concurrent access

### Dictionary Operations

| Method | Syntax | Description |
|--------|--------|-------------|
| `put(key, value)` | `vault['key'] = value` | Store a value |
| `get(key, default=None)` | `vault.get('key', default)` | Retrieve or return default |
| `pop(key)` | `value = vault.pop('key')` | Remove and return value |
| `popitem()` | `key, value = vault.popitem()` | Remove and return arbitrary item |
| `delete_vault()` | `vault.delete_vault()` | Delete the vault file |
| `clear()` | `vault.clear()` | Remove all entries |

### Bulk Operations

| Method | Syntax | Description |
|--------|--------|-------------|
| `put_many(data)` | `vault.put_many({'k': 'v'})` | Bulk insert/update, returns count |
| `get_many(keys)` | `vault.get_many(['a', 'b'])` | Bulk fetch, returns dict |
| `pop_many(keys)` | `vault.pop_many(['a', 'b'])` | Bulk remove, returns dict |
| `has_keys(keys)` | `vault.has_keys(['a', 'b'])` | Check if all keys exist (bool) |

### Dictionary Protocol

| Method | Syntax | Description |
|--------|--------|-------------|
| `__getitem__` | `vault['key']` | Get value (raises KeyError if missing) |
| `__setitem__` | `vault['key'] = value` | Set value |
| `__delitem__` | `del vault['key']` | Delete key (raises KeyError if missing) |
| `__contains__` | `'key' in vault` | Check if key exists |
| `__len__` | `len(vault)` | Number of items |
| `__iter__` | `for key in vault:` | Iterate over keys |
| `__bool__` | `if vault:` | True if not empty |
| `keys()` | `vault.keys()` | List of all keys |
| `values()` | `vault.values()` | List of all values |
| `items()` | `vault.items()` | List of (key, value) pairs |
| `update(other)` | `vault.update({'k': 'v'})` | Bulk insert |
| `setdefault(key, default)` | `vault.setdefault('k', 'default')` | Get or set default |

### Context Manager

```python
with Vault('data') as v:
    v['key'] = 'value'
# Auto-commits on exit
```

### Custom Logging

Vaults has its own logger by default. To integrate with your application's logger:

```python
import logging
from vaults import set_logger

my_logger = logging.getLogger('vaults')
set_logger(my_logger)
```

Now all vault operations will log through your configured logger.

## Serialization

Vaults uses **msgpack** for maximum performance on supported types:

- `None`, `bool`, `int`, `float`, `str`
- `bytes`, `bytearray`
- `list`, `dict`, `set`, `frozenset`

**Note:** Tuples are stored but returned as lists when retrieved.

For unsupported types (custom classes, etc.), it **falls back to pickle** automatically.

This gives you the speed of msgpack with pickle's flexibility.

## Performance

Compared to the previous SQLAlchemy version:

- **3-10x faster** operations (no ORM overhead)
- **Lower memory usage** (no SQLAlchemy overhead)
- **Smaller dependency footprint** (msgpack only vs full SQLAlchemy)

## Thread Safety

Enable thread-safe mode for concurrent access:

```python
v = Vault('shared', thread_safe=True)

# Multiple threads can safely access
import threading
def worker():
    v[f'thread_{threading.current_thread().name}'] = 'data'

threads = [threading.Thread(target=worker) for _ in range(10)]
for t in threads: t.start()
for t in threads: t.join()
```

## File Structure

Vaults create SQLite database files in the `vaults/` subdirectory of `set_root_path()`:

```
/path/to/data/
└── vaults/
    ├── my_data.db
    └── other_vault.db
```

## Error Handling

All database errors are wrapped in `VaultError`:

```python
from vaults import Vault, VaultError

try:
    v = Vault('nonexistent', to_create=False)
except VaultError as e:
    print(f"Vault error: {e}")
```

## Testing

```bash
pip install pytest
pytest tests.py -v
```

## Requirements

- Python 3.8+
- msgpack >= 1.0.0, < 1.1.0

## License

MIT
