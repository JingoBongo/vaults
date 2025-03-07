# Vaults

Vaults is a Python library providing a persistent key-value store using SQLite. It supports asynchronous operations and is ideal for small-scale storage needs.

## Features

- Persistent key-value store using SQLite.
- Asynchronous operations with `SQLAlchemy` and `aiosqlite`.
- Simple interface for CRUD operations.
- Logging for all major events and errors.

## Installation

*the async library needs python 3.9 or above*

pip install git+https://github.com/JingoBongo/vaults#egg=vaults
or
pip install git+http://192.168.0.2:9999/mscebec/vaults#egg=vaults

*using -e flag with pip install will install library in local folder for further modifications*

## Usage
import vaults

*setting path for where folder with vaults will be located. Not necessary, but preferred.*

vaults.set_root_path('placeholder')

*making an object also creates the vault file in vaults folder*

v1 = vaults.Vault('testvault')

*most basic dictionary features. There is also pop() and delete_vault() to get rid of the vault file*

v1.put("tkey", 'tvalue')

print(v1.get('tkey'))

*all method calls from above are sync that call the async methods, you can call async methods directly using \_\_pop\_\_('key') etc*
