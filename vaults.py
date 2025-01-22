import asyncio
import os
import pickle
from sqlalchemy import Column, LargeBinary, BINARY, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import logging
from logging.handlers import RotatingFileHandler

# Logger setup
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_file = 'vaults.log'
handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
handler.setFormatter(log_formatter)
log = logging.getLogger('Fus3')
log.setLevel(logging.DEBUG)
log.addHandler(handler)

root_path = os.path.dirname(os.path.abspath(__file__))
vaults_folder = os.path.join(root_path, "vaults")
Base = declarative_base()

def set_root_path(path: str):
    """
    Sets the global root path and creates the vaults folder.
    
    Args:
        path (str): The root directory path.
    """
    global root_path, vaults_folder
    root_path = path
    vaults_folder = os.path.join(root_path, "vaults")
    os.makedirs(vaults_folder, exist_ok=True)
    log.info(f"Root path set to: {root_path}, vaults folder: {vaults_folder}")

class DictEntry(Base):
    """
    SQLAlchemy model representing a key-value pair in the vault.
    """
    __tablename__ = 'dict'
    key = Column(BINARY, primary_key=True, nullable=False)
    value = Column(LargeBinary)

class Vault:
    """
    A class for managing a persistent vault using an SQLite database.
    
    Attributes:
        vault_name (str): Name of the vault.
        db_path (str): Path to the SQLite database file.
        __engine__: SQLAlchemy async engine for the database.
        __session__: SQLAlchemy async session factory.
    """
    __slots__ = {"vault_name", "db_path", "__engine__", "__session__", "__metadata__"}

    def __init__(self, vault_name: str, to_create: bool = True):
        """
        Initialize the Vault instance.
        
        Args:
            vault_name (str): Name of the vault.
            to_create (bool): Whether to create the database if it doesn't exist.
        """
        os.makedirs(vaults_folder, exist_ok=True)
        
        self.vault_name = vault_name
        self.db_path = os.path.join(root_path, vaults_folder, f"{vault_name}.db")
        path_exists = os.path.exists(self.db_path)

        if path_exists or to_create:
            db_url = f"sqlite+aiosqlite:///{self.db_path}"
            self.__engine__ = create_async_engine(db_url)
            self.__session__ = sessionmaker(self.__engine__, class_=AsyncSession, expire_on_commit=False)

        if to_create and not path_exists:
            log.info(f"Creating vault '{vault_name}'!")
            asyncio.run(self.__create_table__())
        elif not path_exists and not to_create:
            log.error(f"No such vault: '{vault_name}'!")

    async def __create_table__(self):
        """
        Create the database table if it doesn't exist.
        """
        log.debug("Creating table in the database.")
        async with self.__engine__.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def __put__(self, key, value):
        """
        Asynchronous helper to insert or update a key-value pair in the database.
        """
        log.debug(f"Putting key: {key} into vault.")
        async with self.__session__() as session:
            async with session.begin():
                existing_data = await session.get(DictEntry, pickle.dumps(key))
                if existing_data:
                    existing_data.value = pickle.dumps(value)
                    log.debug(f"Updated value for key: {key}.")
                else:
                    new_data = DictEntry(key=pickle.dumps(key), value=pickle.dumps(value))
                    session.add(new_data)
                    log.debug(f"Inserted new key: {key}.")

    def put(self, key, value):
        """
        Insert or update a key-value pair in the database.
        
        Args:
            key: The key for the data.
            value: The value to associate with the key.
        """
        asyncio.run(self.__put__(key, value))
        log.info(f"Key '{key}' stored in vault.")

    async def __get__(self, key):
        """
        Asynchronous helper to retrieve a value by its key.
        """
        log.debug(f"Retrieving key: {key} from vault.")
        async with self.__session__() as session:
            result = await session.execute(select(DictEntry).where(DictEntry.key == pickle.dumps(key)))
            data = result.scalar_one_or_none()
            return pickle.loads(data.value) if data else None

    def get(self, key):
        """
        Retrieve a value by its key.
        
        Args:
            key: The key to retrieve.
        
        Returns:
            The associated value, or None if the key doesn't exist.
        """
        value = asyncio.run(self.__get__(key))
        if value is not None:
            log.info(f"Retrieved key '{key}' from vault.")
        else:
            log.warning(f"Key '{key}' not found in vault.")
        return value
    
    async def __delete_vault__(self):
        """
        Asynchronous helper to delete the database and close connections.
        """
        await self.__engine__.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            log.info(f"Vault '{self.vault_name}' deleted successfully.")
        else:
            log.warning(f"Vault '{self.vault_name}' does not exist.")

    def delete_vault(self):
        """
        Delete the vault database file and close connections.
        """
        asyncio.run(self.__delete_vault__())

    async def __pop__(self, key):
        """
        Asynchronous helper to retrieve and remove a key-value pair from the database.
        """
        log.debug(f"Popping key: {key} from vault.")
        async with self.__session__() as session:
            async with session.begin():
                result = await session.execute(select(DictEntry).where(DictEntry.key == pickle.dumps(key)))
                data = result.scalar_one_or_none()
                if data:
                    await session.delete(data)
                    log.info(f"Key '{key}' removed from vault.")
                    return pickle.loads(data.value)
                log.warning(f"Key '{key}' not found for pop operation.")
                return None

    def pop(self, key):
        """
        Retrieve and remove a key-value pair from the database.
        
        Args:
            key: The key to pop.
        
        Returns:
            The associated value, or None if the key doesn't exist.
        """
        return asyncio.run(self.__pop__(key))


    async def __list_keys__(self):
        """
        Asynchronous helper to list all keys stored in the vault.
        
        Returns:
            A list of all keys in the vault.
        """
        log.debug(f"Listing all keys in vault '{self.vault_name}'.")
        async with self.__session__() as session:
            result = await session.execute(select(DictEntry.key))
            keys = [pickle.loads(row[0]) for row in result.fetchall()]
            return keys

    def list_keys(self):
        """
        Retrieve a list of all keys in the vault.
        
        Returns:
            A list of all keys.
        """
        keys = asyncio.run(self.__list_keys__())
        log.info(f"Listed {len(keys)} keys from vault '{self.vault_name}'.")
        return keys