
import unittest
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

if __name__ == '__main__':
    unittest.main()
