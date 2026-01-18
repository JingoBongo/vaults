import unittest
import os
import tempfile
import shutil
import threading
import time
import importlib.util
spec = importlib.util.spec_from_file_location("vaults_module", "vaults.py")
vaults = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vaults)
Vault = vaults.Vault
set_root_path = vaults.set_root_path
VaultError = vaults.VaultError

class TestVaultCore(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        set_root_path(self.test_dir)
        self.vault_name = 'test_vault'
        self.vault = Vault(self.vault_name)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_put_and_get(self):
        self.vault.put('key1', 'value1')
        result = self.vault.get('key1')
        self.assertEqual(result, 'value1')

    def test_pop(self):
        self.vault.put('key2', 'value2')
        popped_value = self.vault.pop('key2')
        self.assertEqual(popped_value, 'value2')
        self.assertIsNone(self.vault.get('key2'))

    def test_delete_vault(self):
        db_path = self.vault.db_path
        self.assertTrue(os.path.exists(db_path))
        self.vault.delete_vault()
        self.assertFalse(os.path.exists(db_path))

    def test_non_existent_key(self):
        result = self.vault.get('nonexistent_key')
        self.assertIsNone(result)
        result = self.vault.get('nonexistent_key', 'default')
        self.assertEqual(result, 'default')
        popped = self.vault.pop('nonexistent_key')
        self.assertIsNone(popped)

    def test_list_keys(self):
        keys_to_add = {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}
        for key, value in keys_to_add.items():
            self.vault.put(key, value)

        keys = self.vault.list_keys()
        self.assertCountEqual(keys, keys_to_add.keys())

        for key in keys_to_add:
            self.vault.pop(key)
        keys_after_pop = self.vault.list_keys()
        self.assertEqual(keys_after_pop, [])

    def test_get_all_items(self):
        data = {'a': 1, 'b': 2, 'c': 3}
        for k, v in data.items():
            self.vault.put(k, v)

        items = self.vault.get_all_items()
        items_dict = dict(items)
        self.assertEqual(items_dict, data)

    def test_clear(self):
        self.vault.put('key1', 'value1')
        self.vault.put('key2', 'value2')
        self.assertEqual(len(self.vault), 2)
        self.vault.clear()
        self.assertEqual(len(self.vault), 0)

    def test_popitem(self):
        self.vault.put('a', 1)
        self.vault.put('b', 2)
        self.assertEqual(len(self.vault), 2)
        key, value = self.vault.popitem()
        self.assertEqual(len(self.vault), 1)
        self.assertIn(key, ['a', 'b'])
        if key == 'a':
            self.assertEqual(value, 1)
        else:
            self.assertEqual(value, 2)

    def test_popitem_empty(self):
        with self.assertRaises(VaultError):
            self.vault.popitem()


class TestVaultDictProtocol(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        set_root_path(self.test_dir)
        self.vault = Vault('dict_test')

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_getitem(self):
        self.vault.put('key', 'value')
        self.assertEqual(self.vault['key'], 'value')

    def test_getitem_missing(self):
        with self.assertRaises(KeyError):
            _ = self.vault['missing']

    def test_setitem(self):
        self.vault['key'] = 'value'
        self.assertEqual(self.vault.get('key'), 'value')

    def test_setitem_overwrite(self):
        self.vault['key'] = 'value1'
        self.vault['key'] = 'value2'
        self.assertEqual(self.vault['key'], 'value2')

    def test_delitem(self):
        self.vault['key'] = 'value'
        del self.vault['key']
        self.assertIsNone(self.vault.get('key'))

    def test_delitem_missing(self):
        with self.assertRaises(KeyError):
            del self.vault['missing']

    def test_contains(self):
        self.vault['key'] = 'value'
        self.assertIn('key', self.vault)
        self.assertNotIn('missing', self.vault)

    def test_len(self):
        self.assertEqual(len(self.vault), 0)
        self.vault['a'] = 1
        self.vault['b'] = 2
        self.assertEqual(len(self.vault), 2)

    def test_iter(self):
        self.vault['a'] = 1
        self.vault['b'] = 2
        self.vault['c'] = 3
        keys = list(self.vault)
        self.assertCountEqual(keys, ['a', 'b', 'c'])

    def test_bool(self):
        self.assertFalse(bool(self.vault))
        self.vault['key'] = 'value'
        self.assertTrue(bool(self.vault))

    def test_repr(self):
        self.vault['a'] = 1
        r = repr(self.vault)
        self.assertIn('dict_test', r)
        self.assertIn('1 items', r)

    def test_keys(self):
        self.vault['a'] = 1
        self.vault['b'] = 2
        keys = self.vault.keys()
        self.assertCountEqual(keys, ['a', 'b'])

    def test_values(self):
        self.vault['a'] = 1
        self.vault['b'] = 2
        values = self.vault.values()
        self.assertCountEqual(values, [1, 2])

    def test_items(self):
        self.vault['a'] = 1
        self.vault['b'] = 2
        items = self.vault.items()
        items_dict = dict(items)
        self.assertEqual(items_dict, {'a': 1, 'b': 2})

    def test_update(self):
        self.vault.update({'a': 1, 'b': 2})
        self.assertEqual(self.vault['a'], 1)
        self.assertEqual(self.vault['b'], 2)

    def test_setdefault(self):
        self.vault['existing'] = 'value'
        result1 = self.vault.setdefault('existing', 'default')
        self.assertEqual(result1, 'value')
        result2 = self.vault.setdefault('new', 'default')
        self.assertEqual(result2, 'default')
        self.assertEqual(self.vault['new'], 'default')


class TestVaultSerialization(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        set_root_path(self.test_dir)
        self.vault = Vault('serialization_test')

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_string_types(self):
        self.vault.put('str_key', 'string_value')
        self.assertEqual(self.vault.get('str_key'), 'string_value')

    def test_int_types(self):
        self.vault.put('int_key', 42)
        self.assertEqual(self.vault.get('int_key'), 42)

    def test_float_types(self):
        self.vault.put('float_key', 3.14159)
        self.assertAlmostEqual(self.vault.get('float_key'), 3.14159)

    def test_list_types(self):
        self.vault.put('list_key', [1, 2, 3])
        self.assertEqual(self.vault.get('list_key'), [1, 2, 3])

    def test_dict_types(self):
        self.vault.put('dict_key', {'nested': 'value'})
        self.assertEqual(self.vault.get('dict_key'), {'nested': 'value'})

    def test_tuple_types(self):
        self.vault.put('tuple_key', (1, 2, 3))
        result = self.vault.get('tuple_key')
        self.assertEqual(result, [1, 2, 3])

    def test_none_value(self):
        self.vault.put('none_key', None)
        self.assertIsNone(self.vault.get('none_key'))

    def test_bool_types(self):
        self.vault.put('true_key', True)
        self.vault.put('false_key', False)
        self.assertTrue(self.vault.get('true_key'))
        self.assertFalse(self.vault.get('false_key'))

    def test_unicode_keys(self):
        self.vault.put('ключ', 'value')
        self.assertEqual(self.vault.get('ключ'), 'value')

    def test_unicode_values(self):
        self.vault.put('key', 'значение')
        self.assertEqual(self.vault.get('key'), 'значение')

    def test_large_value(self):
        large_value = 'x' * 100000
        self.vault.put('large', large_value)
        self.assertEqual(self.vault.get('large'), large_value)

    def test_special_characters(self):
        special = '!@#$%^&*()_+-=[]{}|;\':",./<>?'
        self.vault.put('special', special)
        self.assertEqual(self.vault.get('special'), special)


class TestVaultContextManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        set_root_path(self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_context_manager(self):
        with Vault('context_test') as v:
            v['key'] = 'value'
        v2 = Vault('context_test', to_create=False)
        self.assertEqual(v2['key'], 'value')
        v2.delete_vault()


class TestVaultThreadSafety(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        set_root_path(self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_thread_safe_creation(self):
        v = Vault('thread_test', thread_safe=True)
        self.assertTrue(v._thread_safe)
        v.delete_vault()

    def test_non_thread_safe_creation(self):
        v = Vault('thread_test', thread_safe=False)
        self.assertFalse(v._thread_safe)
        v.delete_vault()

    def test_concurrent_access(self):
        v = Vault('concurrent_test', thread_safe=True)
        errors = []

        def worker(start, end):
            try:
                for i in range(start, end):
                    v[f'key_{i}'] = f'value_{i}'
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(4):
            t = threading.Thread(target=worker, args=(i * 25, (i + 1) * 25))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(v), 100)
        v.delete_vault()


class TestVaultErrorHandling(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        set_root_path(self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_nonexistent_vault(self):
        with self.assertRaises(VaultError):
            Vault('does_not_exist', to_create=False)


class TestVaultEdgeCases(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        set_root_path(self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_empty_vault_operations(self):
        v = Vault('empty')
        self.assertEqual(len(v), 0)
        self.assertFalse(bool(v))
        self.assertEqual(list(v), [])
        self.assertEqual(v.keys(), [])
        self.assertEqual(v.values(), [])
        self.assertEqual(v.items(), [])

    def test_overwrite_key(self):
        v = Vault('overwrite')
        v['key'] = 'first'
        v['key'] = 'second'
        self.assertEqual(v['key'], 'second')
        self.assertEqual(len(v), 1)

    def test_case_sensitivity(self):
        v = Vault('case')
        v['Key'] = 'upper'
        v['key'] = 'lower'
        self.assertEqual(v['Key'], 'upper')
        self.assertEqual(v['key'], 'lower')
        self.assertEqual(len(v), 2)


class TestVaultBulkOperations(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        set_root_path(self.test_dir)
        self.vault = Vault('bulk_test')

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_put_many_basic(self):
        data = {'a': 1, 'b': 2, 'c': 3}
        count = self.vault.put_many(data)
        self.assertEqual(count, 3)
        self.assertEqual(self.vault['a'], 1)
        self.assertEqual(self.vault['b'], 2)
        self.assertEqual(self.vault['c'], 3)

    def test_put_many_empty(self):
        count = self.vault.put_many({})
        self.assertEqual(count, 0)
        self.assertEqual(len(self.vault), 0)

    def test_put_many_overwrite(self):
        self.vault['a'] = 'original'
        data = {'a': 'updated', 'b': 'new'}
        count = self.vault.put_many(data)
        self.assertEqual(count, 2)
        self.assertEqual(self.vault['a'], 'updated')
        self.assertEqual(self.vault['b'], 'new')
        self.assertEqual(len(self.vault), 2)

    def test_put_many_large_batch(self):
        data = {f'key_{i}': f'value_{i}' for i in range(100)}
        count = self.vault.put_many(data)
        self.assertEqual(count, 100)
        self.assertEqual(len(self.vault), 100)

    def test_put_many_with_various_types(self):
        data = {
            'int': 42,
            'float': 3.14,
            'str': 'hello',
            'list': [1, 2, 3],
            'dict': {'nested': 'value'},
            'none': None,
            'bool': True
        }
        count = self.vault.put_many(data)
        self.assertEqual(count, 7)
        self.assertEqual(self.vault['int'], 42)
        self.assertEqual(self.vault['float'], 3.14)
        self.assertEqual(self.vault['str'], 'hello')
        self.assertEqual(self.vault['list'], [1, 2, 3])
        self.assertEqual(self.vault['dict'], {'nested': 'value'})
        self.assertIsNone(self.vault.get('none'))
        self.assertTrue(self.vault['bool'])

    def test_get_many_basic(self):
        self.vault['a'] = 1
        self.vault['b'] = 2
        self.vault['c'] = 3
        result = self.vault.get_many(['a', 'b', 'c'])
        self.assertEqual(result, {'a': 1, 'b': 2, 'c': 3})

    def test_get_many_empty(self):
        result = self.vault.get_many([])
        self.assertEqual(result, {})

    def test_get_many_partial_existing(self):
        self.vault['a'] = 1
        self.vault['b'] = 2
        result = self.vault.get_many(['a', 'b', 'c', 'd'])
        self.assertEqual(result, {'a': 1, 'b': 2})

    def test_get_many_none_existing(self):
        self.vault['a'] = 1
        result = self.vault.get_many(['x', 'y', 'z'])
        self.assertEqual(result, {})

    def test_get_many_single_key(self):
        self.vault['only'] = 'value'
        result = self.vault.get_many(['only'])
        self.assertEqual(result, {'only': 'value'})

    def test_pop_many_basic(self):
        self.vault['a'] = 1
        self.vault['b'] = 2
        self.vault['c'] = 3
        result = self.vault.pop_many(['a', 'b'])
        self.assertEqual(result, {'a': 1, 'b': 2})
        self.assertEqual(len(self.vault), 1)
        self.assertIsNone(self.vault.get('a'))
        self.assertEqual(self.vault['c'], 3)

    def test_pop_many_empty(self):
        result = self.vault.pop_many([])
        self.assertEqual(result, {})
        self.assertEqual(len(self.vault), 0)

    def test_pop_many_partial_existing(self):
        self.vault['a'] = 1
        self.vault['b'] = 2
        result = self.vault.pop_many(['a', 'x', 'y'])
        self.assertEqual(result, {'a': 1})
        self.assertEqual(len(self.vault), 1)
        self.assertEqual(self.vault['b'], 2)

    def test_pop_many_none_existing(self):
        self.vault['a'] = 1
        result = self.vault.pop_many(['x', 'y', 'z'])
        self.assertEqual(result, {})
        self.assertEqual(len(self.vault), 1)

    def test_pop_many_all_items(self):
        self.vault['a'] = 1
        self.vault['b'] = 2
        result = self.vault.pop_many(['a', 'b'])
        self.assertEqual(result, {'a': 1, 'b': 2})
        self.assertEqual(len(self.vault), 0)

    def test_has_keys_all_present(self):
        self.vault['a'] = 1
        self.vault['b'] = 2
        self.vault['c'] = 3
        result = self.vault.has_keys(['a', 'b', 'c'])
        self.assertTrue(result)

    def test_has_keys_empty_list(self):
        result = self.vault.has_keys([])
        self.assertTrue(result)

    def test_has_keys_partial_missing(self):
        self.vault['a'] = 1
        self.vault['b'] = 2
        result = self.vault.has_keys(['a', 'b', 'c'])
        self.assertFalse(result)

    def test_has_keys_none_present(self):
        self.vault['a'] = 1
        result = self.vault.has_keys(['x', 'y', 'z'])
        self.assertFalse(result)

    def test_has_keys_single_key_present(self):
        self.vault['only'] = 'value'
        result = self.vault.has_keys(['only'])
        self.assertTrue(result)

    def test_has_keys_single_key_missing(self):
        self.vault['a'] = 'value'
        result = self.vault.has_keys(['missing'])
        self.assertFalse(result)

    def test_bulk_operations_thread_safe(self):
        v = Vault('bulk_thread_test', thread_safe=True)
        errors = []

        def worker_put(start, end):
            try:
                data = {f'key_{i}': f'value_{i}' for i in range(start, end)}
                v.put_many(data)
            except Exception as e:
                errors.append(e)

        def worker_get(keys):
            try:
                v.get_many(keys)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(4):
            t = threading.Thread(target=worker_put, args=(i * 25, (i + 1) * 25))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(v), 100)
        v.delete_vault()

    def test_bulk_mixed_operations(self):
        self.vault.put_many({'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(len(self.vault), 3)

        result = self.vault.get_many(['a', 'b'])
        self.assertEqual(result, {'a': 1, 'b': 2})

        self.assertTrue(self.vault.has_keys(['a', 'b', 'c']))

        removed = self.vault.pop_many(['a', 'b'])
        self.assertEqual(removed, {'a': 1, 'b': 2})

        self.assertEqual(len(self.vault), 1)
        self.assertFalse(self.vault.has_keys(['a', 'b']))
        self.assertTrue(self.vault.has_keys(['c']))


if __name__ == '__main__':
    unittest.main()
