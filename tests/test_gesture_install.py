from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
class GesturePackagingTests(unittest.TestCase):
    def test_installer_copies_engine_and_overlay(self):
        for script in ('INSTALL_GODS_EYE_WINDOWS.ps1','FIX_GESTURES_WINDOWS.ps1'):
            text=(ROOT/script).read_text(encoding='utf8')
            self.assertIn('jarvis_gesture_engine.js',text)
            self.assertIn('jarvis_gesture_overlay.js',text)
            tag_line = next(line for line in text.splitlines() if line.strip().startswith("$tag"))
            self.assertLess(tag_line.index("jarvis_gesture_engine.js"),tag_line.index("jarvis_gesture_overlay.js"))
    def test_gesture_ui_has_matching_instructions(self):
        code=(ROOT/'integrations/gods_eye_gestures.js').read_text(encoding='utf8')
        self.assertIn('Pinch + move up/down/left/right',code)
        self.assertIn('Two hands: zoom in/out',code)
        self.assertIn('gestureEngine.step(hands)',code)
        self.assertIn('getUserMedia',code)
        self.assertNotIn('jsdelivr',code.lower())
if __name__=='__main__':unittest.main()
