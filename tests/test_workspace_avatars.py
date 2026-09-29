from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PIL import Image
from rag.personas import get_persona
from ui.workspace import persona_avatar


class WorkspaceAvatarTests(unittest.TestCase):
    def test_future_persona_photo_replaces_placeholder(self):
        with TemporaryDirectory() as folder:
            Image.new('RGB', (180, 100), '#ff0000').save(Path(folder) / 'nui.png')
            with patch('ui.workspace.AVATAR_DIR', Path(folder), create=True):
                avatar = persona_avatar(get_persona('nui'))
            image = Image.open(BytesIO(avatar)).convert('RGB')
            self.assertEqual(image.size, (96, 96))
            self.assertEqual(image.getpixel((48, 48)), (255, 0, 0))

    def test_corrupt_future_photo_keeps_workspace_available(self):
        with TemporaryDirectory() as folder:
            (Path(folder) / 'nui.png').write_bytes(b'not an image')
            with patch('ui.workspace.AVATAR_DIR', Path(folder), create=True):
                avatar = persona_avatar(get_persona('nui'))
            self.assertTrue(avatar.startswith(b'\x89PNG'))
