"""Regression tests for precise and conservative computer controls."""
import unittest
from unittest.mock import Mock, patch
from actions import computer_control as cc


class ComputerAccuracyTests(unittest.TestCase):
    def setUp(self):
        self.fake = Mock()
        self.fake.size.return_value = (1920, 1080)
        self.patcher = patch.object(cc, 'pyautogui', self.fake)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_windows_scroll_uses_normal_notches(self):
        with patch.object(cc.sys, 'platform', 'win32'):
            cc._scroll('down', 3)
        self.fake.scroll.assert_called_once_with(-3)

    def test_horizontal_scroll_direction(self):
        cc._scroll('right', 2)
        self.fake.hscroll.assert_called_once_with(2)

    def test_rejects_offscreen_click(self):
        with self.assertRaises(ValueError):
            cc._click(3000, 20)
        self.fake.click.assert_not_called()

    def test_rejects_partial_coords(self):
        with self.assertRaises(ValueError):
            cc._click(20, None)
        self.fake.click.assert_not_called()

    def test_rejects_nan_move(self):
        with self.assertRaises(ValueError):
            cc._move(float('nan'), 50)
        self.fake.moveTo.assert_not_called()

    def test_drag_checks_both_endpoints_before_moving(self):
        with self.assertRaises(ValueError):
            cc._drag(10, 10, -1, 0)
        self.fake.moveTo.assert_not_called()

    def test_unicode_typing_uses_clipboard(self):
        with patch.object(cc, '_require_pyperclip', return_value=True), patch.object(cc, '_clipboard_paste', return_value='Pasted') as paste:
            cc._type('नमस्ते')
            paste.assert_called_once_with('नमस्ते')
        self.fake.write.assert_not_called()

    def test_windows_focus_only_succeeds_if_activated(self):
        with patch.object(cc, '_get_os', return_value='windows'), patch.object(cc.subprocess, 'run', return_value=Mock(returncode=0, stdout='False\n')):
            self.assertIn('failed', cc._focus_window('Not present'))

    def test_unknown_user_data_not_fabricated(self):
        with patch.object(cc, '_user_profile', return_value={}):
            response = cc.computer_control({'action': 'user_data', 'field': 'name'})
        self.assertIn('No saved user data', response)

    def test_does_not_log_user_text(self):
        with patch.object(cc, '_type', return_value='ok'), patch('builtins.print') as p:
            cc.computer_control({'action': 'type', 'text': 'SECRET_PRIVATE_TEXT'})
            output = repr(p.call_args_list)
            self.assertNotIn('SECRET_PRIVATE_TEXT', output)


if __name__ == '__main__':
    unittest.main()
