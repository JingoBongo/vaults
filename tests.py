
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
        


if __name__ == '__main__':
    unittest.main()
