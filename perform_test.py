import unittest

from maya import standalone, cmds
from unittest import TestCase


class TestCases(TestCase):
    # Plugin unload test
    def test_unload_plugin(self):
        cmds.unloadPlugin("objExport")
        self.assertFalse(cmds.pluginInfo("objExport", query=True, loaded=True))

    # Plugin Load test
    def test_load_plugin(self):
        cmds.loadPlugin("objExport")
        self.assertTrue(cmds.pluginInfo("objExport", query=True, loaded=True))


if __name__ == "__main__":
    # Open Maya
    standalone.initialize()

    unittest.main()
