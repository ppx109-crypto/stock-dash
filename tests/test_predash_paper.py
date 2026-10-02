import unittest
from predash.paper import new_account,replay,execute,export_account,restore_account,PaperError

class PaperLedgerTests(unittest.TestCase):
    def trade(self,account,side,quantity,price,identifier=None):
        return execute(account,'005930','연습 종목',side,quantity,price,'2026-09-29',
                       '2026-09-30T15:00:00+09:00','매매 이유',identifier)
    def test_cash_cost_and_realized_on_partial_then_full_sale(self):
        account=self.trade(new_account(10000),'buy',3,1000)
        account=self.trade(account,'buy',1,2000)
        account=self.trade(account,'sell',2,1500)
        ledger=replay(account)
        self.assertEqual((ledger['cash'],ledger['realized'],ledger['positions'][0]['cost']),(8000,500,2500))
        account=self.trade(account,'sell',2,1000)
        self.assertEqual(replay(account),{'cash':10000,'realized':0,'positions':[]})
    def test_rejects_insufficient_cash_oversell_and_duplicate(self):
        account=new_account(1000)
        with self.assertRaises(PaperError):self.trade(account,'buy',2,1000)
        account=self.trade(account,'buy',1,1000,'same')
        with self.assertRaises(PaperError):self.trade(account,'sell',2,1000)
        with self.assertRaises(PaperError):self.trade(account,'sell',1,1000,'same')
        self.assertEqual(len(account['trades']),1)
    def test_rejects_old_quotes_and_fractional_quantity(self):
        with self.assertRaises(PaperError):execute(new_account(),'005930','연습','buy',1,1000,
            '2026-09-20','2026-09-30T15:00:00+09:00')
        with self.assertRaises(PaperError):self.trade(new_account(),'buy',1.5,1000)
    def test_backup_replayed_and_forged_trades_rejected(self):
        account=self.trade(new_account(),'buy',10,1000)
        restored=restore_account(export_account(account))
        self.assertEqual(replay(restored),replay(account))
        restored['trades'][0]['side']='sell'
        import json
        with self.assertRaises(PaperError):restore_account(json.dumps(restored))

if __name__=='__main__':unittest.main()

