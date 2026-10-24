"""Long-lived registered command routing contracts owned by the root CLI."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from runtime.cli import main


class GameRoutingTests(unittest.TestCase):
    def test_game_routes_preserve_arguments_and_exit_status(self):
        for game, commands, canonical in (
            ("asterix", ("simulate", "eval"), "asterix"),
            ("tetris", ("simulate", "eval", "replay"), "tetris"),
            ("touhou", ("simulate", "eval", "profile"), "touhou"),
            ("rhythm", ("simulate", "eval", "profile"), "rhythm"),
            ("pcba", ("simulate", "eval", "report", "demo", "realtime-smoke", "view", "latency", "pipeline", "loop-demo", "export", "showcase", "figures", "clock-preflight"), "pcba"),
            ("pingpong", ("simulate", "eval", "report"), "tabletennis"),
            ("tabletennis", ("simulate", "eval", "report"), "tabletennis"),
            ("badminton", ("simulate", "eval", "preflight", "audit", "report", "diagnose", "profile"), "badminton"),
            ("racing", ("simulate", "eval", "profile", "preflight", "budget"), "racing"),
        ):
            for command in commands:
                with self.subTest(game=game, command=command), \
                     patch.object(sys, "argv", ["sol", command, game, "--help"]), \
                     patch("runtime.cli.envs.launch", side_effect=SystemExit(7)) as call:
                    with self.assertRaises(SystemExit) as stopped:
                        main()
                    self.assertEqual(stopped.exception.code, 7)
                    self.assertEqual(call.call_args.args[1:], (canonical, [command, "--help"]))

    def test_registry_and_setup_only_errors_need_no_site_packages(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, '-S', '-m', 'runtime.cli', 'env', 'list'],
                                cwd=root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual({json.loads(line)['game'] for line in result.stdout.splitlines()},
                         {'asterix', 'tetris', 'touhou', 'rhythm', 'pcba', 'racing', 'badminton', 'tabletennis', 'pvz', 'vera20k'})
        for game in ('pvz', 'vera20k'):
            result = subprocess.run([sys.executable, '-S', '-m', 'runtime.cli', 'simulate', game],
                                    cwd=root, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(f'Environment {game} does not support simulate', result.stderr)

    def test_command_help_lists_only_supported_games(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, '-S', '-m', 'runtime.cli', 'profile', '--help'],
                                cwd=root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('{touhou,rhythm,racing,badminton}', result.stdout)
        self.assertNotIn('asterix', result.stdout)
        self.assertNotIn('pvz', result.stdout)


if __name__ == "__main__":
    unittest.main()
