import os, pickle, logging
from logging.handlers import RotatingFileHandler
from sqlalchemy import Column, LargeBinary, BINARY, select, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler = RotatingFileHandler("vaults.log", maxBytes=10 * 1024 * 1024)
handler.setFormatter(log_formatter)
log = logging.getLogger("Fus3")
log.setLevel(logging.DEBUG)
log.addHandler(handler)

root_path = os.path.dirname(os.path.abspath(__file__))
vaults_folder = os.path.join(root_path, "vaults")
Base = declarative_base()


def set_root_path(path: str):
    global root_path, vaults_folder
    root_path = path
    vaults_folder = os.path.join(root_path, "vaults")
    os.makedirs(vaults_folder, exist_ok=True)
    log.info(f"Root path set to: {root_path}, vaults folder: {vaults_folder}")


class DictEntry(Base):
    __tablename__ = "dict"
    key = Column(BINARY, primary_key=True, nullable=False)
    value = Column(LargeBinary)


class Vault:
    __slots__ = {"vault_name", "db_path", "__engine__", "__session__"}

    def __init__(self, vault_name: str, to_create: bool = True):
        os.makedirs(vaults_folder, exist_ok=True)
        self.vault_name = vault_name
        self.db_path = os.path.join(vaults_folder, f"{vault_name}.db")
        path_exists = os.path.exists(self.db_path)
        if path_exists or to_create:
            db_url = f"sqlite:///{self.db_path}"
            self.__engine__ = create_engine(db_url, echo=False, future=True)
            self.__session__ = sessionmaker(bind=self.__engine__, class_=Session, expire_on_commit=False)
        if to_create and not path_exists:
            log.info(f"Creating vault '{vault_name}'!")
            self.__create_table__()
        elif not path_exists and not to_create:
            log.error(f"No such vault: '{vault_name}'!")

    def __create_table__(self):
        log.debug("Creating table in the database.")
        with self.__engine__.begin() as conn:
            Base.metadata.create_all(conn)

    def __put__(self, key, value):
        log.debug(f"Putting key: {key} into vault.")
        with self.__session__() as session:
            with session.begin():
                pickled_key = pickle.dumps(key)
                existing_data = session.get(DictEntry, pickled_key)
                if existing_data:
                    existing_data.value = pickle.dumps(value)
                    log.debug(f"Updated value for key: {key}.")
                else:
                    new_data = DictEntry(key=pickled_key, value=pickle.dumps(value))
                    session.add(new_data)
                    log.debug(f"Inserted new key: {key}.")

    def put(self, key, value):
        self.__put__(key, value)
        log.info(f"Key '{key}' stored in vault.")

    def __get__(self, key):
        log.debug(f"Retrieving key: {key} from vault.")
        with self.__session__() as session:
            result = session.execute(select(DictEntry).where(DictEntry.key == pickle.dumps(key)))
            data = result.scalar_one_or_none()
            return pickle.loads(data.value) if data else None

    def get(self, key):
        value = self.__get__(key)
        if value is not None:
            log.info(f"Retrieved key '{key}' from vault.")
        else:
            log.warning(f"Key '{key}' not found in vault.")
        return value

    def get_all_items(self):
        # Bulk fetch all rows using scalars() for reliability.
        with self.__session__() as session:
            entries = session.scalars(select(DictEntry)).all()
            log.info("Fetched %d entries from vault '%s'", len(entries), self.vault_name)
            return [pickle.loads(entry.value) for entry in entries]

    def __delete_vault__(self):
        self.__engine__.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            log.info(f"Vault '{self.vault_name}' deleted successfully.")
        else:
            log.warning(f"Vault '{self.vault_name}' does not exist.")

    def delete_vault(self):
        self.__delete_vault__()
        log.info(f"Vault '{self.vault_name}' deleted successfully.")

    def __pop__(self, key):
        log.debug(f"Popping key: {key} from vault.")
        with self.__session__() as session:
            with session.begin():
                result = session.execute(select(DictEntry).where(DictEntry.key == pickle.dumps(key)))
                data = result.scalar_one_or_none()
                if data:
                    session.delete(data)
                    log.info(f"Key '{key}' removed from vault.")
                    return pickle.loads(data.value)
                log.warning(f"Key '{key}' not found for pop operation.")
                return None

    def pop(self, key):
        value = self.__pop__(key)
        log.info(f"Key '{key}' popped from vault.")
        return value

    def __list_keys__(self):
        log.debug(f"Listing all keys in vault '{self.vault_name}'.")
        with self.__session__() as session:
            result = session.execute(select(DictEntry.key))
            keys = [pickle.loads(row[0]) for row in result.fetchall()]
            return keys

    def list_keys(self):
        keys = self.__list_keys__()
        log.info(f"Listed {len(keys)} keys from vault '{self.vault_name}'.")
        return keys
