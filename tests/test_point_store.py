import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import point_store

class DeletionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'XDG_DATA_HOME':self.tmp.name});self.env.start()
        point_store.folder().mkdir(parents=True)
    def tearDown(self):
        self.env.stop();self.tmp.cleanup()
    def test_only_selected_point_removed(self):
        a=point_store.folder()/('a'*32+'.json');b=point_store.folder()/('b'*32+'.json')
        a.write_text('{}');b.write_text('{}')
        point_store.delete('a'*32)
        self.assertFalse(a.exists());self.assertTrue(b.exists())
    def test_paths_rejected(self):
        for value in ['../../etc/passwd','../initial-point','bad','/tmp/file']:
            with self.assertRaises(ValueError):point_store.delete(value)
    def test_initial_point_stays_hidden(self):
        self.assertFalse(point_store.initial_deleted())
        point_store.delete('initial-point')
        self.assertTrue(point_store.initial_deleted())
    def test_symlink_target_not_deleted(self):
        target=Path(self.tmp.name)/'keep';target.write_text('keep')
        (point_store.folder()/('a'*32+'.json')).symlink_to(target)
        point_store.delete('a'*32)
        self.assertEqual(target.read_text(),'keep')
