"""External FFmpeg processes must not inherit bundled shared libraries."""
import os
import unittest
from unittest.mock import patch

from process_env import system_program_env


class ProcessEnvironmentTest(unittest.TestCase):
    @patch('sys.platform', 'linux')
    @patch('sys.frozen', True, create=True)
    def test_frozen_restores_original_library_path(self):
        with patch.dict(os.environ, {'LD_LIBRARY_PATH': '/bundle',
                                     'LD_LIBRARY_PATH_ORIG': '/user/libs'}, clear=True):
            self.assertEqual(system_program_env(), {'LD_LIBRARY_PATH': '/user/libs'})
            self.assertEqual(os.environ['LD_LIBRARY_PATH'], '/bundle')

    @patch('sys.platform', 'linux')
    @patch('sys.frozen', True, create=True)
    def test_frozen_removes_library_path_without_original(self):
        with patch.dict(os.environ, {'LD_LIBRARY_PATH': '/bundle'}, clear=True):
            self.assertEqual(system_program_env(), {})

    @patch('sys.frozen', False, create=True)
    def test_source_preserves_environment(self):
        with patch.dict(os.environ, {'LD_LIBRARY_PATH': '/user/libs'}, clear=True):
            self.assertEqual(system_program_env(), dict(os.environ))
