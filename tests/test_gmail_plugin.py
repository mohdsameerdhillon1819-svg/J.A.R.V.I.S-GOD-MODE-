"""Offline tests; no Google account or network required."""
import base64
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from plugins import gmail_control as gm


class TestGmailControl(unittest.TestCase):
    def setUp(self):
        with gm._lock: gm._pending.clear()

    def test_plugin_declared(self):
        self.assertEqual(gm.PLUGIN['name'], 'gmail_control')
        self.assertIn('prepare_send', gm.PLUGIN['parameters']['properties']['action']['enum'])

    def test_validate_mail(self):
        self.assertEqual(gm._validate_addresses('hello@example.com'), 'hello@example.com')
        for value in ('', 'not-an-address', 'x@example.com\nBcc:bad@example.com'):
            with self.assertRaises(ValueError): gm._validate_addresses(value)

    def test_raw_draft_mime(self):
        raw = gm._make_message('a@example.com', 'Hi', 'Hello')['raw']
        msg = base64.urlsafe_b64decode(raw)
        self.assertIn(b'To: a@example.com', msg)
        self.assertIn(b'Subject: Hi', msg)
        self.assertIn(b'Hello', msg)

    def test_body_parsing(self):
        body = base64.urlsafe_b64encode('Hello!'.encode()).decode()
        self.assertEqual(gm._body_text({'parts':[{'mimeType':'text/plain','body':{'data':body}}]}), 'Hello!')
        self.assertEqual(gm._body_text({'mimeType':'text/html','body':{'data':body}}), '')

    @patch.object(gm, '_service')
    def test_create_draft_does_not_send(self, get_service):
        service = MagicMock()
        get_service.return_value = service
        service.users().drafts().create().execute.return_value={'id':'draft12345'}
        result = gm.run({'action':'draft','to':'a@example.com','subject':'Hello','body':'Test'})
        self.assertIn('draft12345', result)
        service.users().drafts().send.assert_not_called()

    @patch.object(gm, '_service')
    def test_send_without_confirmation_rejected(self, get_service):
        service=MagicMock(); get_service.return_value=service
        self.assertIn('Not sent', gm.run({'action':'send','draft_id':'draft12345','confirmation_code':'000000'}))
        service.users().drafts().send.assert_not_called()

    @patch.object(gm, '_service')
    def test_prepare_and_send_once(self, get_service):
        service=MagicMock();get_service.return_value=service
        service.users().drafts().get().execute.return_value={
            'message':{'payload':{'headers':[{'name':'To','value':'a@example.com'},
                                               {'name':'Subject','value':'Test'}]}}}
        service.users().drafts().send.return_value.execute.return_value={'id':'sent12345'}
        text=gm.run({'action':'prepare_send','draft_id':'draft12345'})
        self.assertIn('REVIEW BEFORE SENDING', text)
        self.assertIn('Nothing has been sent', text)
        with gm._lock: code=gm._pending['code']
        self.assertIn('Not sent', gm.run({'action':'send','draft_id':'draft12345','confirmation_code':'wrong'}))
        self.assertIn('sent12345', gm.run({'action':'send','draft_id':'draft12345','confirmation_code':code}))
        self.assertIn('Not sent', gm.run({'action':'send','draft_id':'draft12345','confirmation_code':code}))
        self.assertEqual(service.users().drafts().send.call_count, 1)

    @patch.object(gm, '_service')
    def test_search_metadata(self, get_service):
        service=MagicMock();get_service.return_value=service
        service.users().messages().list().execute.return_value={'messages':[{'id':'msg12345'}]}
        service.users().messages().get().execute.return_value={
            'payload':{'headers':[{'name':'From','value':'someone@example.com'},
                                   {'name':'Subject','value':'Homework'}]}}
        self.assertIn('Homework', gm.run({'action':'search','query':'in:inbox','limit':1}))


if __name__=='__main__': unittest.main()
