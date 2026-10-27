"""Offline arithmetic, rollback, approval and FFmpeg integration fixtures; no cloud calls."""
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


preflight, edit, review = [module(n) for n in ('transcription_preflight', 'edit_plan', 'cut_review')]
NOW = datetime(2026, 10, 23, 12, tzinfo=timezone.utc)


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.request = json.loads((ROOT / 'fixtures/transcription-request.json').read_text(encoding='utf-8'))
        self.request['balance'] = {'provider': 'elevenlabs', 'model': 'scribe_v1', 'channel': 'api',
                                   'remaining': 10, 'unit': 'minutes', 'scope': 'test-pool',
                                   'source': 'synthetic test snapshot, not actual account',
                                   'queried_at': '2026-10-23T12:00:00Z', 'reset_at': '2026-11-01T00:00:00Z'}

    def plan(self, **kwargs):
        return preflight.evaluate(self.request, now=NOW, **kwargs)

    def test_known_sufficient_still_requires_approval(self):
        result = self.plan(measurements_verified=True)
        self.assertEqual(result['state'], 'needs_explicit_confirmation')
        self.assertAlmostEqual(result['estimated_free_usage'], 2.2)
        self.assertAlmostEqual(result['estimated_remaining'], 7.8)
        self.assertFalse(result['upload_allowed'])

    def test_unknown_balance_blocks_even_with_approval_boolean(self):
        self.request['balance'] = None
        self.request['approval'] = {'explicit': True, 'reference': 'not bound'}
        result = self.plan()
        self.assertEqual(result['state'], 'blocked_unknown_balance')
        self.assertIsNone(result['estimated_remaining'])

    def test_insufficient_cannot_enable_paid_fallback(self):
        self.request['balance']['remaining'] = 1
        self.request['allow_paid'] = True
        result = self.plan(measurements_verified=True)
        self.assertEqual(result['state'], 'blocked_insufficient')
        self.assertFalse(result['paid_allowed'])

    def test_units(self):
        for unit, remaining, expected in [('seconds', 600, 132), ('minutes', 10, 2.2), ('hours', 1, 132 / 3600)]:
            with self.subTest(unit=unit):
                self.request['balance'].update(unit=unit, remaining=remaining)
                self.assertAlmostEqual(self.plan()['estimated_free_usage'], expected)

    def test_credits_without_conversion_unknown(self):
        self.request['balance']['unit'] = 'credits'
        self.assertEqual(self.plan()['state'], 'blocked_unknown_balance')

    def test_credits_verified_scope_and_options(self):
        self.request['balance'].update(unit='credits', remaining=500)
        self.request['balance']['conversion'] = {
            'provider': 'elevenlabs', 'model': 'scribe_v1', 'channel': 'api',
            'credits_per_second': 2, 'source': 'synthetic conversion for testing only',
            'verified_at': '2026-10-23T12:00:00Z', 'options_digest': preflight.digest(self.request['options'])}
        self.assertAlmostEqual(self.plan()['estimated_free_usage'], 264)
        self.request['options']['diarize'] = False
        self.assertEqual(self.plan()['state'], 'blocked_unknown_balance')

    def test_model_mismatch_balance_unknown(self):
        self.request['balance']['model'] = 'scribe_v2'
        self.assertEqual(self.plan()['state'], 'blocked_unknown_balance')

    def test_web_minutes_cannot_stand_in_for_api(self):
        self.request['balance']['channel'] = 'web'
        self.assertEqual(self.plan()['state'], 'blocked_unknown_balance')

    def test_invalid_duration(self):
        for value in [-1, 0, float('nan'), float('inf'), True, '12', None]:
            with self.subTest(value=value):
                self.request['inputs'][0]['duration_seconds'] = value
                with self.assertRaises(ValueError):
                    self.plan()

    def test_wrong_sha_rejected(self):
        self.request['inputs'][0]['sha256'] = 'unmeasured'
        with self.assertRaises(ValueError):
            self.plan()

    def test_negative_balance_is_unknown(self):
        self.request['balance']['remaining'] = -5
        self.assertEqual(self.plan()['state'], 'blocked_unknown_balance')

    def test_invalid_attempts_never_estimated(self):
        for value in [0, -1, True, 1.5]:
            self.request['attempts'] = value
            with self.assertRaises(ValueError):
                self.plan()

    def test_missing_cache_result_is_not_reused(self):
        self.request['cache'] = [{'key': preflight.cache_key(self.request['inputs'][0], self.request),
                                  'status': 'success', 'result_path': 'does-not-exist.json', 'result_sha256': '0' * 64}]
        self.assertEqual(self.plan()['inputs'][0]['disposition'], 'planned')

    def test_empty_input_rejected(self):
        self.request['inputs'] = []
        with self.assertRaises(ValueError):
            self.plan()

    def test_stale_future_reset_and_missing_provenance(self):
        cases = [('queried_at', '2026-10-22T00:00:00Z'), ('queried_at', '2026-10-24T00:00:00Z'),
                 ('reset_at', '2026-10-23T10:00:00Z'), ('source', ''), ('scope', '')]
        original = copy.deepcopy(self.request['balance'])
        for key, value in cases:
            with self.subTest(key=key, value=value):
                self.request['balance'] = copy.deepcopy(original)
                self.request['balance'][key] = value
                self.assertEqual(self.plan()['state'], 'blocked_unknown_balance')

    def test_duplicate_inputs_count_once(self):
        self.request['inputs'].append(copy.deepcopy(self.request['inputs'][0]))
        result = self.plan()
        self.assertEqual(result['estimated_seconds'], 120)
        self.assertEqual(result['inputs'][1]['disposition'], 'duplicate')

    def test_cache_requires_success_file_hash_and_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'transcript.json'
            path.write_text('{"words": []}', encoding='utf-8')
            entry = {'key': preflight.cache_key(self.request['inputs'][0], self.request),
                     'status': 'success', 'result_path': str(path), 'result_sha256': preflight.file_hash(path)}
            self.request['cache'] = [entry]
            self.assertEqual(self.plan()['state'], 'no_upload_needed')
            self.request['model'] = 'scribe_v2'
            self.assertEqual(self.plan()['inputs'][0]['disposition'], 'planned')
            self.request['model'] = 'scribe_v1'
            path.write_text('corrupted')
            self.assertEqual(self.plan()['inputs'][0]['disposition'], 'planned')
            entry['status'] = 'failed'
            entry['result_sha256'] = preflight.file_hash(path)
            self.assertEqual(self.plan()['inputs'][0]['disposition'], 'planned')

    def test_retry_reserve_and_inflight_accounting(self):
        self.request['attempts'] = 2
        self.request['reservations'] = [{'scope': 'test-pool', 'unit': 'minutes', 'amount': 6,
                                         'status': 'uncertain', 'included_in_snapshot': False}]
        result = self.plan()
        self.assertAlmostEqual(result['available_free'], 4)
        self.assertAlmostEqual(result['estimated_free_usage'], 4.4)
        self.assertEqual(result['state'], 'blocked_insufficient')

    def test_reflected_reservation_not_deducted_twice(self):
        self.request['reservations'] = [{'scope': 'test-pool', 'unit': 'minutes', 'amount': 6,
                                         'status': 'submitted', 'included_in_snapshot': True}]
        self.assertEqual(self.plan()['available_free'], 10)

    def test_reservation_unit_mismatch_blocks(self):
        self.request['reservations'] = [{'scope': 'test-pool', 'unit': 'credits', 'amount': 1,
                                         'status': 'reserved', 'included_in_snapshot': False}]
        self.assertEqual(self.plan()['state'], 'blocked_unknown_balance')

    def test_approval_binds_plan_and_changes_invalidate(self):
        result = self.plan(measurements_verified=True)
        self.request['approval'] = {'explicit': True, 'plan_digest': result['plan_digest'],
                                     'reference': 'synthetic explicit approval evidence'}
        self.assertEqual(self.plan(measurements_verified=True)['state'], 'approved_preflight_only')
        self.assertFalse(self.plan(measurements_verified=True)['upload_allowed'])
        self.request['attempts'] = 2
        self.assertFalse(self.plan(measurements_verified=True)['approval_matches'])

    def test_unverified_fixture_never_ready(self):
        self.assertEqual(self.plan()['state'], 'blocked_unverified_measurement')

    def test_no_permanent_price_default(self):
        self.assertIsNone(self.plan()['gross_reference_usd'])

    def test_scoped_optional_price_reference(self):
        self.request['price_reference'] = {'provider': 'elevenlabs', 'model': 'scribe_v1', 'channel': 'api',
                                          'usd_per_hour': .22, 'source': 'synthetic dated price',
                                          'as_of': '2026-10-23', 'options_digest': preflight.digest(self.request['options'])}
        self.assertAlmostEqual(self.plan()['gross_reference_usd'], 132 / 3600 * .22)
        self.request['price_reference']['model'] = 'scribe_v2'
        self.assertIsNone(self.plan()['gross_reference_usd'])

    def test_options_cache_key_and_billing_rounding(self):
        old = preflight.cache_key(self.request['inputs'][0], self.request)
        self.request['options']['diarize'] = False
        self.assertNotEqual(old, preflight.cache_key(self.request['inputs'][0], self.request))
        self.request['inputs'][0]['duration_seconds'] = 1.1
        self.request['billing'] = {'rounding_seconds': 1, 'minimum_seconds_per_file': 5}
        self.assertEqual(self.plan()['estimated_seconds'], 5)

    def test_unsupported_provider_model_channel(self):
        for key, value in [('provider', 'other'), ('model', 'scribe_v2_realtime'), ('channel', 'web')]:
            original = self.request[key]
            self.request[key] = value
            with self.assertRaises(ValueError):
                self.plan()
            self.request[key] = original


class EditTests(unittest.TestCase):
    def setUp(self):
        self.project = json.loads((ROOT / 'fixtures/edit-project.json').read_text(encoding='utf-8'))

    def test_remap_and_reversible_originals(self):
        original = copy.deepcopy(self.project)
        result = edit.build(self.project)
        self.assertEqual(result['duration_seconds'], 5)
        self.assertEqual([w['id'] for w in result['remapped_words']], ['w1', 'w3', 'w4', 'w5'])
        self.assertAlmostEqual(result['remapped_words'][1]['start'], 1.1)
        self.assertEqual(result['original_words'], original['words'])
        self.assertEqual(self.project, original)
        self.assertFalse(result['verification']['ear_listening'])

    def test_unapproved_candidate_preserves_all(self):
        self.project['candidates'][0]['approved'] = False
        result = edit.build(self.project)
        self.assertEqual(result['duration_seconds'], 6)
        self.assertEqual(len(result['remapped_words']), 5)

    def test_string_approval_not_approval(self):
        self.project['candidates'][0]['approved'] = 'true'
        self.assertEqual(edit.build(self.project)['duration_seconds'], 6)

    def test_rollback_by_decision_restores_word_times(self):
        self.project['candidates'][0]['approved'] = False
        result = edit.build(self.project)
        for before, after in zip(self.project['words'], result['remapped_words']):
            self.assertEqual((before['start'], before['end']), (after['start'], after['end']))

    def test_cut_inside_word_rejected(self):
        self.project['candidates'][0]['start'] = 1.2
        with self.assertRaisesRegex(ValueError, 'word boundary'):
            edit.build(self.project)

    def test_overlapping_deletes_rejected(self):
        self.project['candidates'].append({'id': 'd2', 'source': 'screen', 'start': 1, 'end': 2.1,
                                          'reason': 'test', 'approved': True})
        with self.assertRaisesRegex(ValueError, 'overlapping'):
            edit.build(self.project)

    def test_whole_source_deleted_rejected(self):
        self.project['candidates'][0].update(start=0, end=6)
        with self.assertRaises(ValueError):
            edit.build(self.project)

    def test_reason_required(self):
        self.project['candidates'][0]['reason'] = ''
        with self.assertRaises(ValueError):
            edit.build(self.project)

    def test_invalid_word_time(self):
        for value in [-1, float('nan'), True, 8]:
            self.project['words'][0]['start'] = value
            with self.assertRaises(ValueError):
                edit.build(self.project)

    def test_duplicate_ids_rejected(self):
        self.project['words'].append(copy.deepcopy(self.project['words'][0]))
        with self.assertRaises(ValueError):
            edit.build(self.project)

    def test_multiple_sources_timeline_and_cut_windows(self):
        second = copy.deepcopy(self.project['sources'][0])
        second['id'] = 'second'
        self.project['sources'].append(second)
        result = edit.build(self.project)
        self.assertEqual(result['duration_seconds'], 11)
        self.assertEqual([c['time'] for c in result['cut_reviews']], [1, 5])
        self.assertTrue(all(c['checks']['audio_seam'] == 'pending' for c in result['cut_reviews']))


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required for integration')
class MediaIntegrationTests(unittest.TestCase):
    def test_actual_audio_measurement_and_cli_rechecks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'own.wav'
            with wave.open(str(path), 'wb') as stream:
                stream.setnchannels(1)
                stream.setsampwidth(2)
                stream.setframerate(16000)
                stream.writeframes(b'\x00\x00' * 32000)
            measured = preflight.measure(path)
            self.assertAlmostEqual(measured['duration_seconds'], 2)
            self.assertEqual(measured['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
            request = json.loads((ROOT / 'fixtures/transcription-request.json').read_text(encoding='utf-8'))
            request['inputs'] = [measured]
            input_path, output = Path(tmp) / 'request.json', Path(tmp) / 'plan.json'
            input_path.write_text(json.dumps(request), encoding='utf-8')
            import sys
            subprocess.run([sys.executable, str(ROOT / 'transcription_preflight.py'), 'plan',
                            str(input_path), '--output', str(output)], check=True, capture_output=True)
            self.assertTrue(json.loads(output.read_text())['measurements_verified'])
            measured['sha256'] = '1' * 64
            input_path.write_text(json.dumps(request), encoding='utf-8')
            failed = subprocess.run([sys.executable, str(ROOT / 'transcription_preflight.py'), 'plan',
                                     str(input_path), '--output', str(Path(tmp) / 'failed.json')], capture_output=True)
            self.assertNotEqual(failed.returncode, 0)

    def test_every_cut_exports_window_frames_and_decodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / 'original-test.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=160x284:r=25:d=2',
                            '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=16000:duration=2',
                            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', str(media)], check=True)
            project = {'sources': [{'id': 'x', 'path': 'source.mp4', 'sha256': '0' * 64, 'duration_seconds': 3}],
                       'words': [], 'candidates': [{'id': 'd', 'source': 'x', 'start': 1, 'end': 2,
                                                   'reason': 'synthetic test', 'approved': True}]}
            edl = edit.build(project)
            result = review.inspect_cuts(edl, media, Path(tmp) / 'cuts')
            self.assertEqual(result['cut_count'], 1)
            self.assertTrue(result['full_decode_pass'])
            self.assertTrue(result['audio_stream_present'])
            self.assertFalse(result['ear_listening'])
            self.assertEqual(len(list((Path(tmp) / 'cuts').glob('*.png'))), 2)
            self.assertEqual(len(list((Path(tmp) / 'cuts').glob('*.mp4'))), 1)

    def test_duration_mismatch_stops_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / 'short.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=s=32x32:d=1', str(media)], check=True)
            with self.assertRaisesRegex(ValueError, 'duration'):
                review.inspect_cuts({'duration_seconds': 9, 'cut_reviews': []}, media, Path(tmp) / 'never')
            self.assertFalse((Path(tmp) / 'never').exists())


if __name__ == '__main__':
    unittest.main()
