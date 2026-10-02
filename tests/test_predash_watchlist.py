import unittest
from predash.watchlist import MAX_WATCH,clean_codes,export_backup,restore_backup,backup_names

class WatchlistTests(unittest.TestCase):
    def test_public_codes_bounded_deduplicated_and_portable(self):
        raw=['005930','000660','005930','abc123','12345678']+[f'{i:06d}' for i in range(10)]
        codes=clean_codes(raw)
        self.assertEqual(codes[:2],['005930','000660'])
        self.assertEqual(len(codes),MAX_WATCH)
        self.assertEqual(restore_backup(export_backup(codes)),codes)
    def test_invalid_backup_rejected(self):
        with self.assertRaises(ValueError):restore_backup('{"version":2,"codes":[]}')
    def test_named_backup_preserves_names_and_legacy_codes(self):
        payload=export_backup(['005930'],{'005930':'삼성전자'})
        self.assertEqual(restore_backup(payload),['005930'])
        self.assertEqual(backup_names(payload),{'005930':'삼성전자'})
        self.assertEqual(backup_names('{"version":1,"codes":["005930"]}'),{})
    def test_backup_names_exclude_unlisted_and_invalid_labels(self):
        payload=export_backup(['005930','000660','035420'],
            {'005930':' 삼성전자 ','000660':123,'035420':'035420','123456':'다른 종목'})
        self.assertEqual(backup_names(payload),{'005930':'삼성전자'})

if __name__=='__main__':unittest.main()

