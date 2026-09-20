import json
import os
from pathlib import Path
import string
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import i18n

class TranslationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.env=patch.dict(os.environ,{'XDG_DATA_HOME':self.temp.name,'LANG':'lt_LT.UTF-8'})
  self.env.start(); i18n.load_language()
 def tearDown(self):
  self.env.stop();self.temp.cleanup();i18n.load_language()
 def test_default_english_even_on_lithuanian_system(self):
  self.assertEqual(i18n.language(),'en')
  self.assertEqual(i18n.tr('Programos'),'Applications')
 def test_exact_requested_language_choices(self):
  self.assertEqual([x[0] for x in i18n.LANGUAGES],['en','ru','lt','zh','it'])
 def test_all_catalogs_have_matching_placeholders(self):
  for source,row in i18n._catalog.items():
   slots={n for _,n,_,_ in string.Formatter().parse(source) if n}
   for lang in ['en','ru','zh','it']:
    self.assertTrue(row[lang])
    self.assertEqual(slots,{n for _,n,_,_ in string.Formatter().parse(row[lang]) if n})
 def test_each_language_persists_after_reload(self):
  for lang,_ in i18n.LANGUAGES:
   i18n.set_language(lang)
   i18n.set_language('en',persist=False)
   self.assertEqual(i18n.load_language(),lang)
 def test_lithuanian_uses_original(self):
  i18n.set_language('lt',persist=False)
  self.assertEqual(i18n.tr('Įdiegtos programos'),'Įdiegtos programos')
 def test_dynamic_messages(self):
  for lang,_ in i18n.LANGUAGES:
   i18n.set_language(lang,persist=False)
   text=i18n.tr('Pašalinta paketų: {count}.\nŽurnalas: {log}',count=3,log='/tmp/log.json')
   self.assertIn('3',text);self.assertIn('/tmp/log.json',text);self.assertNotIn('{',text)
 def test_corrupt_preferences_fall_back_to_english(self):
  p=i18n.preferences_path();p.parent.mkdir(parents=True)
  for bad in ['broken','[]','{"language":"xx"}']:
   p.write_text(bad);self.assertEqual(i18n.load_language(),'en')
 def test_other_preferences_preserved(self):
  p=i18n.preferences_path();p.parent.mkdir(parents=True);p.write_text('{"other":42}')
  i18n.set_language('it')
  self.assertEqual(json.loads(p.read_text())['other'],42)
 def test_unknown_language_rejected_without_changing_language(self):
  with self.assertRaises(ValueError):i18n.set_language('bad')
  self.assertEqual(i18n.language(),'en')
 def test_backend_error_and_detail_translation(self):
  self.assertEqual(i18n.translate_error('Netinkamas atkūrimo taškas.'),'Invalid restore point.')
  self.assertEqual(i18n.translate_error('dpkg turi neužbaigtų operacijų:\napt'),'dpkg has unfinished operations:\napt')
 def test_unknown_external_metadata_unchanged(self):
  self.assertEqual(i18n.tr('Firefox ESR'),'Firefox ESR')

if __name__=='__main__':unittest.main()
