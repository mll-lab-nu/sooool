"""Long-lived shared recording, registration and assessment contracts owned by runtime.evaluation."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from runtime import cli
from runtime.evaluation import append_record, assess, recording


class Records(unittest.TestCase):
    def test_game_results_keep_their_provider_clock_and_completion_status(self):
        cases = [
            ('asterix', 'simulate', 'subscription', 'virtual', {'episodes': [{'status': 'interrupted', 'error': {'message': 'timeout'}}]}, 'interrupted'),
            ('touhou', 'eval', 'api', 'wall', {'complete': True, 'won': False}, 'completed'),
            ('rhythm', 'eval', 'api', 'wall', {'complete': False, 'passed': False}, 'incomplete'),
            ('racing', 'simulate', 'subscription', 'virtual', {'status': 'complete', 'won': False}, 'completed'),
            ('badminton', 'eval', 'api', 'wall', {'complete': False, 'status': 'incomplete'}, 'incomplete'),
            ('tabletennis', 'eval', 'rules', 'wall', {'status': 'complete', 'won': False}, 'completed'),
            ('pcba', 'eval', 'subscription', 'wall', {'metrics': {'success': False}}, 'completed'),
        ]
        for game, command, provider, clock, summary, status in cases:
            with self.subTest(game=game), tempfile.TemporaryDirectory() as directory:
                out = Path(directory) / 'run'
                with recording(out, game=game, command=command, provider=provider, clock=clock):
                    out.mkdir()
                    (out/'manifest.json').write_text(json.dumps({'game': game, 'mode': command, 'recipe': {}}))
                    (out/'summary.json').write_text(json.dumps(summary))
                record = json.loads((out/'evaluation-record.json').read_text())
                self.assertEqual((record['game'], record['command'], record['provider'], record['clock'], record['status']),
                                 (game, command, provider, clock, status))
                self.assertEqual(record['summary'], summary)

    def test_initialization_failure_is_recorded_and_existing_runs_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)/'run'
            with self.assertRaisesRegex(RuntimeError, 'initialization failed'):
                with recording(out, game='pcba', command='eval', provider='subscription', clock='wall', result_file='report.json'):
                    out.mkdir()
                    raise RuntimeError('initialization failed')
            record = json.loads((out/'evaluation-record.json').read_text())
            self.assertEqual(record['status'], 'interrupted')
            self.assertIsNone(record['summary'])
            before = (out/'evaluation-record.json').read_bytes()
            with self.assertRaises(FileExistsError):
                with recording(out, game='pcba', command='eval', provider='subscription', clock='wall'):
                    self.fail('Existing output must not enter a new run')
            self.assertEqual((out/'evaluation-record.json').read_bytes(), before)
            assess(out, 'diagnostic', 'Initialization failed before model calls.')
            assess(out, 'reject', 'Retain this attempt.')
            rows = [json.loads(line) for line in (out/'assessments.jsonl').read_text().splitlines()]
            self.assertEqual([row['decision'] for row in rows], ['diagnostic', 'reject'])

    def test_registration_is_idempotent_and_decisions_append_for_every_game(self):
        providers = {'asterix': 'subscription', 'touhou': 'api', 'rhythm': 'api', 'racing': 'api',
                     'badminton': 'api', 'tabletennis': 'rules', 'pcba': 'subscription', 'tetris': 'claude'}
        for game, provider in providers.items():
            with self.subTest(game=game), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                out = base/game
                destination = base/'records.jsonl'
                with recording(out, game=game, command='eval', provider=provider, clock='wall'):
                    out.mkdir()
                    (out/'summary.json').write_text('{"won": false}')
                argv = ['sol', 'record', str(out), '--registry', str(destination), '--decision', 'diagnostic', '--note', 'Fixture, no model calls.']
                with patch.object(sys, 'argv', argv):
                    cli.main()
                    cli.main()
                self.assertEqual(len(destination.read_text().splitlines()), 1)
                self.assertEqual(len((out/'assessments.jsonl').read_text().splitlines()), 2)
                record_path = out/'evaluation-record.json'
                record = json.loads(record_path.read_text())
                record['summary']['won'] = True
                record_path.write_text(json.dumps(record))
                with self.assertRaisesRegex(ValueError, 'different evidence'):
                    append_record(out, destination)
                self.assertEqual(len(destination.read_text().splitlines()), 1)

    def test_registration_rejects_mismatched_game_and_run_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'run'
            registry=Path(directory)/'records.jsonl'
            with recording(output,game='asterix',command='eval',provider='subscription',clock='wall'):
                output.mkdir()
                (output/'summary.json').write_text('{"won":false}')
            path=output/'evaluation-record.json'
            original=json.loads(path.read_text())
            for changed, message in (({'game':'touhou'},'game does not match'),
                                     ({'record_id':'different'},'ID does not match')):
                with self.subTest(changed=changed):
                    path.write_text(json.dumps({**original,**changed}))
                    with self.assertRaisesRegex(ValueError,message):
                        append_record(output,registry)
                    self.assertFalse(registry.exists())


if __name__ == '__main__':
    unittest.main()
