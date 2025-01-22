
import unittest
import asyncio
import os
from vaults import Vault, set_root_path

class TestVault(unittest.TestCase):

    def setUp(self):
        """Set up test environment."""
        self.vault_name = 'test_vault'
        self.vault = Vault(self.vault_name)
    
    def tearDown(self):
        """Clean up after tests."""
        self.vault.delete_vault()

    def test_put_and_get(self):
        """Test storing and retrieving a value."""
        self.vault.put('key1', 'value1')
        result = self.vault.get('key1')
        self.assertEqual(result, 'value1')

    def test_pop(self):
        """Test retrieving and removing a value."""
        self.vault.put('key2', 'value2')
        popped_value = self.vault.pop('key2')
        self.assertEqual(popped_value, 'value2')
        self.assertIsNone(self.vault.get('key2'))

    def test_delete_vault(self):
        """Test deleting the vault."""
        db_path = self.vault.db_path
        self.assertTrue(os.path.exists(db_path))
        self.vault.delete_vault()
        self.assertFalse(os.path.exists(db_path))

    def test_non_existent_key(self):
        """Test behavior with non-existent keys."""
        result = self.vault.get('nonexistent_key')
        self.assertIsNone(result)
        popped = self.vault.pop('nonexistent_key')
        self.assertIsNone(popped)
        
    def test_list_keys(self):
        """Test listing all keys."""
        keys_to_add = {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}
        for key, value in keys_to_add.items():
            self.vault.put(key, value)

        keys = self.vault.list_keys()
        self.assertCountEqual(keys, keys_to_add.keys())  # Ensure all keys are present

        # Verify empty vault
        for key in keys_to_add:
            self.vault.pop(key)
        keys_after_pop = self.vault.list_keys()
        self.assertEqual(keys_after_pop, [])
        
class TestAsyncVault(unittest.TestCase):
    def setUp(self):
        self.vault_name = 'async_test_vault'
        self.vault = Vault(self.vault_name)
        
    def tearDown(self):
        self.vault.delete_vault()

    def test_async_put_and_get(self):
        async def run_test():
            await self.vault.__put__('key1', 'value1')
            result = await self.vault.__get__('key1')
            return result
            
        result = asyncio.run(run_test())
        self.assertEqual(result, 'value1')

    def test_async_pop(self):
        async def run_test():
            await self.vault.__put__('key2', 'value2')
            popped = await self.vault.__pop__('key2')
            remaining = await self.vault.__get__('key2')
            return popped, remaining
            
        popped, remaining = asyncio.run(run_test())
        self.assertEqual(popped, 'value2')
        self.assertIsNone(remaining)

    def test_async_list_keys(self):
        async def run_test():
            test_data = {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}
            for key, value in test_data.items():
                await self.vault.__put__(key, value)
            
            keys = await self.vault.__list_keys__()
            return keys, test_data.keys()
            
        keys, expected_keys = asyncio.run(run_test())
        self.assertCountEqual(keys, expected_keys)

    def test_async_delete_vault(self):
        async def run_test():
            await self.vault.__put__('test_key', 'test_value')
            db_path = self.vault.db_path
            await self.vault.__delete_vault__()
            return db_path
            
        db_path = asyncio.run(run_test())
        self.assertFalse(os.path.exists(db_path))

    def test_async_non_existent_key(self):
        async def run_test():
            result = await self.vault.__get__('nonexistent')
            return result
            
        result = asyncio.run(run_test())
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
