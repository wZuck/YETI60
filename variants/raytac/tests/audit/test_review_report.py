#!/usr/bin/env python3
"""Reject mixed-board counts and malformed bilingual review publications."""
import copy
import csv
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import report_raytac_review as review


def current_summary():
    candidate = ROOT / 'hardware/usb-short-route'
    with (candidate / 'mainboard-purchase.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    return review.candidate_summary(
        review.read(candidate / 'audit/native-check.json'),
        review.read(candidate / 'audit/fabrication-check.json'),
        review.read(candidate / 'audit/assembly-package.json'), rows)


class ReviewPublication(unittest.TestCase):
    def setUp(self):
        self.summary = current_summary()
        self.report = dict(self.summary,
                           current_candidate_summary=copy.deepcopy(self.summary),
                           physical_verification=False, production_approved=False,
                           manufacturing_order_released=False)
        self.documents = {
            zh: '\n'.join(f"| {'线束' if zh and tag == 'Harness' else tag} | {cn if zh else en} |"
                          for tag, en, cn in review.summary_rows(self.summary))
            for zh in (False, True)}

    def verify(self):
        review.verify_publication(self.report, self.documents, self.summary)

    def test_current_candidate_counts(self):
        self.verify()
        # Distinguish this board from the retained reference's 267 pairs/816 vias.
        self.assertEqual(self.summary['physical_signal_pairs'], 411)
        self.assertEqual(self.summary['through_vias'], 813)
        self.assertEqual(self.summary['mainboard_parts'], 75)
        self.assertEqual(self.summary['assembly_conductors'], 9)

    def test_fit_dictionary_cannot_be_a_part_count(self):
        self.report['mainboard_parts'] = {'status': 'bounded-fit-passed'}
        with self.assertRaisesRegex(AssertionError, 'candidate count'):
            self.verify()

    def test_summary_rejects_non_scalar_counts(self):
        self.summary['mainboard_parts'] = {'status': 'bounded-fit-passed'}
        with self.assertRaisesRegex(AssertionError, 'Non-scalar'):
            review.summary_rows(self.summary)

    def test_reference_board_counts_cannot_replace_current_counts(self):
        for key, wrong in [('physical_signal_pairs', 267), ('through_vias', 816)]:
            with self.subTest(key=key):
                report = copy.deepcopy(self.report)
                report[key] = wrong
                with self.assertRaisesRegex(AssertionError, 'candidate count'):
                    review.verify_publication(report, self.documents, self.summary)

    def test_both_language_tables_reject_wrong_BOM(self):
        for zh in (False, True):
            with self.subTest(zh=zh):
                documents = dict(self.documents)
                documents[zh] = documents[zh].replace('75', "{'status': 'bounded-fit-passed'}")
                with self.assertRaisesRegex(AssertionError, 'review table'):
                    review.verify_publication(self.report, documents, self.summary)

    def test_both_language_tables_reject_reference_harness(self):
        for zh in (False, True):
            with self.subTest(zh=zh):
                documents = dict(self.documents)
                documents[zh] = documents[zh].replace('9 conductors', '7 conductors').replace('9 根', '7 根')
                with self.assertRaisesRegex(AssertionError, 'Harness'):
                    review.verify_publication(self.report, documents, self.summary)

    def test_missing_warning_disclosure_rejected(self):
        for zh in (False, True):
            with self.subTest(zh=zh):
                documents = dict(self.documents)
                documents[zh] = '\n'.join(line for line in documents[zh].splitlines()
                                          if not line.startswith('| DRC |'))
                with self.assertRaisesRegex(AssertionError, 'DRC'):
                    review.verify_publication(self.report, documents, self.summary)

    def test_physical_approval_is_not_inferred(self):
        for key in ['physical_verification', 'production_approved', 'manufacturing_order_released']:
            with self.subTest(key=key):
                report = copy.deepcopy(self.report)
                report[key] = True
                with self.assertRaises(AssertionError):
                    review.verify_publication(report, self.documents, self.summary)


if __name__ == '__main__':
    if '--published' in sys.argv:
        sys.argv.remove('--published')
        audit = ROOT / 'docs/audit'
        report = json.loads((audit / 'raytac-review.json').read_text())
        documents = {zh: (audit / ('raytac-review' + ('.zh-CN' if zh else '') + '.md')).read_text()
                     for zh in (False, True)}
        review.verify_publication(report, documents, current_summary())
        print('Published JSON and both Markdown reports match current candidate evidence.', flush=True)
    unittest.main()
