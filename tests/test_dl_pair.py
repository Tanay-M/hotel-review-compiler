"""DL model contracts; synthetic predictions here are not research evidence."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from hotel_compiler.dl_pair import QUERIES, eligible_text
from hotel_compiler.routed_data import HEADS
from hotel_compiler.routed_model import load_routed_predictor


class PairContracts(unittest.TestCase):
    def test_every_category_is_conditioned_on_original_text(self):
        calls = []
        def tokenizer(text, query, truncation):
            calls.append((text, query, truncation))
            return {'input_ids': [1]*10}
        original = 'Room was AMAZING!!!'
        self.assertTrue(eligible_text(tokenizer, original, 160))
        self.assertEqual(len(calls), len(HEADS))
        self.assertTrue(all(t == original and not trunc for t, q, trunc in calls))
        self.assertEqual({q for t,q,trunc in calls}, set(QUERIES.values()))

    def test_rejects_overlength_pair_without_silent_truncation(self):
        def tokenizer(text, query, truncation):
            return {'input_ids': [0]*(161 if query == QUERIES['Food'] else 100)}
        self.assertFalse(eligible_text(tokenizer, 'review', 160))

    def test_dispatch_uses_manifest_not_folder_name(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            manifest = folder/'routed_manifest.json'
            manifest.write_text(json.dumps({'model_type':'dl_category_pair'}))
            with patch('hotel_compiler.dl_pair.LocalDLModel') as dl:
                load_routed_predictor(folder, device='cpu')
                dl.assert_called_once_with(folder, device='cpu')
            manifest.write_text(json.dumps({'model_type':'frozen'}))
            with patch('hotel_compiler.routed_model.LocalRoutedModel') as ml:
                load_routed_predictor(folder, device='cpu')
                ml.assert_called_once_with(folder, device='cpu')


if __name__ == '__main__': unittest.main()
