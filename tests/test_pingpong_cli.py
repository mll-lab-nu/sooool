"""Keep PingPong aliases and upstream Badminton commands on their owning runners."""
import sys
import unittest
from unittest.mock import patch

from runtime.cli import ROOT, main


class GameRoutingTests(unittest.TestCase):
    def test_game_routes_preserve_arguments_and_exit_status(self):
        for game, commands, script in (
            ("pingpong", ("simulate", "eval", "report"), "tabletennis.py"),
            ("tabletennis", ("simulate", "eval", "report"), "tabletennis.py"),
            ("badminton", ("simulate", "eval", "preflight", "audit", "report", "diagnose", "profile"), "badminton.py"),
        ):
            for command in commands:
                with self.subTest(game=game, command=command), \
                     patch.object(sys, "argv", ["sol", command, game, "--help"]), \
                     patch("runtime.cli.subprocess.call", return_value=7) as call:
                    with self.assertRaises(SystemExit) as stopped:
                        main()
                    self.assertEqual(stopped.exception.code, 7)
                    call.assert_called_once_with([sys.executable, str(ROOT / "scripts" / script),
                                                  command, "--help"])


if __name__ == "__main__":
    unittest.main()
