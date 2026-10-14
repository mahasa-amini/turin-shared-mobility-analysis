"""Small operator cases that protect measurement-specific cleaning decisions."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


class CleaningRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        base = Path(cls.temp.name) / 'src/cleaning'
        base.mkdir(parents=True)
        cls.modules = {}
        for name in ('clean_bird', 'finalize_bird', 'finalize_lime', 'audit_voi', 'finalize_voi'):
            path = base / f'{name}.py'
            shutil.copy2(ROOT / 'src/cleaning' / path.name, path)
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            cls.modules[name] = module

    def test_bird_masks_measurements_retains_trip_and_dst(self):
        audit, final = self.modules['clean_bird'], self.modules['finalize_bird']
        raw = pd.DataFrame({
            'ID_VEICOLO': ['a', 'b'], 'DATAORA_INIZIO': ['2024-03-31 01:55', '2024-07-01 12:00'],
            'DATAORA_FINE': ['2024-03-31 03:05', '2024-07-01 12:01'],
            'LATITUDINE_INIZIO_CORSA': [45., 45.], 'LONGITUTIDE_INIZIO_CORSA': [7.6, 7.6],
            'LATITUDINE_FINE_CORSA': [45., 45.], 'LONGITUTIDE_FINE_CORSA': [7.6, 7.6],
            'DISTANZA_KM': [0., 1.], 'DURATA_MIN': [10., 1.],
        })
        actual = final.add_final_quality_fields(audit.add_audit_flags(audit.add_quality_features(audit.convert_types(raw))))
        self.assertTrue(actual.VALID_TRIP_RECORD.all())
        self.assertTrue(actual.loc[0, 'TEMPORAL_DST_AMBIGUOUS'])
        self.assertTrue(pd.isna(actual.loc[0, 'DISTANCE_KM_CLEAN']))
        self.assertTrue(pd.isna(actual.loc[1, 'SPEED_KMH_CLEAN']))
        self.assertEqual(actual.loc[0, 'END_TIME_RECONSTRUCTED'], pd.Timestamp('2024-03-31 02:05'))
        self.assertTrue(actual.SMALL_DISPLACEMENT_RETAINED.all())

    def test_lime_dst_sentinel_zero_duration_and_spatial_flags(self):
        frame = pd.DataFrame({
            'ID_VEICOLO': list('abcde'), 'START_TIME': pd.to_datetime(['2024-01-01'] * 5),
            'END_TIME_RAW': pd.to_datetime(['2024-01-01 00:10'] * 5),
            'DURATION_DIFFERENCE_MIN': [60., -60., 0., 0., 0.],
            'DURATION_FROM_TIMESTAMPS_MIN': [70., -50., .25, 0., 10.],
            'DURATA_MIN': [10., 10., 0., 0., 10.], 'DISTANZA_KM': [100., 0., 0., 1., 1.],
            'HAVERSINE_KM': [.1] * 5,
            'LATITUDINE_INIZIO_CORSA': [45., 45., 45., 45., 90.],
            'LONGITUTIDE_INIZIO_CORSA': [7.6] * 5, 'LATITUDINE_FINE_CORSA': [45.] * 5,
            'LONGITUTIDE_FINE_CORSA': [7.6] * 5,
            'BATTERIA_INIZIO_CORSA': [100.] * 5, 'BATTERIA_FINE_CORSA': [50.] * 5,
        })
        actual = self.modules['finalize_lime'].add_final_quality_fields(frame)
        self.assertEqual(actual.DURATION_MIN_CLEAN.tolist(), [10., 10., .25, 0., 10.])
        self.assertTrue(pd.isna(actual.loc[0, 'DISTANCE_KM_CLEAN']))
        self.assertFalse(actual.loc[0, 'FLAG_LONG_DISTANCE_30'])
        self.assertEqual(actual.loc[1, 'DISTANCE_KM_CLEAN'], 0.)
        self.assertTrue(actual.loc[2, 'VALID_TRIP_RECORD'])
        self.assertFalse(actual.loc[3, 'VALID_TRIP_RECORD'])
        self.assertTrue(actual.loc[4, 'VALID_TRIP_RECORD'])
        self.assertFalse(actual.loc[4, 'VALID_SPATIAL_PREZONE'])
        frame.loc[0, 'LATITUDINE_INIZIO_CORSA'] = float('nan')
        self.assertFalse(self.modules['finalize_lime'].add_final_quality_fields(frame).loc[0, 'VALID_TRIP_RECORD'])

    def test_voi_dedup_conflicts_preserve_reservation_uncertainty(self):
        module = self.modules['finalize_voi']
        row = {c: 1 for c in module.TRIP_DEFINING_COLUMNS}
        row.update({module.TRIP_ID: 'trip', 'SOURCE_PERIOD': '2024-01', 'SOURCE_ROW': 1, 'Prenotazione': 'si'})
        other = dict(row, SOURCE_ROW=2, Prenotazione='No')
        actual = module.build_canonical_trips(pd.DataFrame([row, other]))
        self.assertEqual(len(actual), 1)
        self.assertEqual(actual.iloc[0].DUPLICATE_ROWS_COLLAPSED, 1)
        self.assertTrue(actual.iloc[0].PRENOTAZIONE_CONFLICT)
        self.assertTrue(pd.isna(actual.iloc[0].PRENOTAZIONE_CLEAN))
        other['KM Tot'] = 2
        with self.assertRaisesRegex(ValueError, 'Trip-defining conflicts'):
            module.build_canonical_trips(pd.DataFrame([row, other]))

    def test_voi_damaged_time_fallback_and_utc_conversion(self):
        audit, final = self.modules['audit_voi'], self.modules['finalize_voi']
        code = audit.normalize_compact_timestamp(pd.Series(['20240100000000', '20240701100000.0']))
        parsed = pd.to_datetime(code, format='%Y%m%d%H%M%S', errors='coerce')
        self.assertTrue(pd.isna(parsed.iloc[0]))
        frame = pd.DataFrame({'START_TIME_RAW': parsed,
                              'END_TIME_RAW': parsed + pd.Timedelta(minutes=5),
                              'Tempo Tot': [7., 6.], 'SOURCE_PERIOD': ['2024-01', '2024-07']})
        actual = final.add_temporal_fields(frame)
        self.assertEqual(actual.DURATION_MIN_CLEAN.tolist(), [7., 5.])
        self.assertTrue(actual.loc[0, 'FLAG_JAN2024_TEMPORAL_DAMAGE'])
        self.assertEqual(actual.loc[0, 'DURATION_SOURCE'], 'provider_tempo_tot')
        self.assertEqual(actual.loc[1, 'START_TIME_LOCAL'], pd.Timestamp('2024-07-01 12:00'))
        self.assertFalse(actual.loc[0, 'HAS_TEMPORAL_DETAIL'])


class ComparisonRules(unittest.TestCase):
    def test_material_changes_fail(self):
        spec = importlib.util.spec_from_file_location('reproduce', ROOT / 'scripts/reproduce_cleaning.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        baseline = pd.DataFrame({'id': ['001', '002'], 'value': [1., float('nan')],
                                 'time': pd.to_datetime(['2024-01-01', '2024-01-02'])})
        self.assertEqual(module.compare_frames(baseline.copy(), baseline)['value']['max_abs_difference'], 0.)
        for column, value in [('id', '1'), ('value', 2.), ('value', float('nan')),
                              ('time', pd.Timestamp('2024-01-01 00:00:01'))]:
            with self.subTest(column=column, value=value):
                changed = baseline.copy()
                changed.loc[0, column] = value
                with self.assertRaisesRegex(ValueError, 'Material discrepancy'):
                    module.compare_frames(changed, baseline)
        with self.assertRaisesRegex(ValueError, 'shape or column order'):
            module.compare_frames(baseline[['value', 'id', 'time']], baseline)


if __name__ == '__main__':
    unittest.main()
