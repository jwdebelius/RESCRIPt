# ----------------------------------------------------------------------------
# Copyright (c) 2019--, QIIME 2 development team.
#
# Distributed under the terms of the Lesser GPL 3.0 licence.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from qiime2.plugin.testing import TestPluginBase
from qiime2.plugins import rescript
import qiime2
import pandas as pd
import pandas.util.testing as pdt

from rescript import cross_validate


import_data = qiime2.Artifact.import_data


class TestPipelines(TestPluginBase):
    package = 'rescript.tests'

    def setUp(self):
        super().setUp()

        # drop feature C1b because it is missing species level
        self.taxa_series = pd.read_csv(
            self.get_data_path('derep-taxa.tsv'), sep='\t', index_col=0,
            squeeze=True).drop('C1b')
        self.taxa = import_data('FeatureData[Taxonomy]', self.taxa_series)
        seqs = import_data(
            'FeatureData[Sequence]', self.get_data_path('derep-test.fasta'))
        self.seqs = import_data(
            'FeatureData[Sequence]', seqs.view(pd.Series).drop('C1b'))

    def test_cross_validate_k3(self):
        exp, obs = rescript.actions.cross_validate(self.seqs, self.taxa, k=3)
        # exp_exp (expected ground truth taxonomies) we will just evaluate
        # at genus level for now, since that is consistently correct.
        # TODO: evaluate at species level once random_state is implemented.
        exp_exp = self.taxa_series.copy().sort_index().apply(
            lambda x: ';'.join(x.split(';')[:6]))
        # exp_obs (expected observations), for now should equal exp_exp when
        # evaluating at genus level.
        # TODO: evaluate at species level once random_state is implemented.
        exp_obs = exp_exp
        # TODO: evaluate at species level once random_state is implemented.
        pdt.assert_series_equal(
            exp_exp, exp.view(pd.Series).sort_index().apply(
                lambda x: ';'.join(x.split(';')[:6])))
        pdt.assert_series_equal(
            exp_obs, obs.view(pd.Series).sort_index().apply(
                lambda x: ';'.join(x.split(';')[:6])))

    def test_cross_validate_perfect_classifier(self):
        # exp species should equal the input taxonomy when k='disable'
        exp, obs = rescript.actions.cross_validate(
            self.seqs, self.taxa, k='disable')
        pdt.assert_series_equal(
            exp.view(pd.Series).sort_index(), self.taxa_series.sort_index())
        # obs species will equal best possible predictive accuracy.
        # Evaluate at genus level right now, which will always be consistent.
        # TODO: evaluate at species level once random_state is implemented.
        pdt.assert_series_equal(
            obs.view(pd.Series).sort_index().apply(
                lambda x: ';'.join(x.split(';')[:6])),
            self.taxa_series.sort_index().apply(
                lambda x: ';'.join(x.split(';')[:6])))

    def test_evaluate_classifications(self):
        # simulate predicted classifications at genus level
        taxa = self.taxa_series.copy().apply(
            lambda x: ';'.join(x.split(';')[:6]))
        taxa = qiime2.Artifact.import_data('FeatureData[Taxonomy]', taxa)
        vol, = rescript.actions.evaluate_classifications([self.taxa], [taxa])
        # now the same but input multiple times to test lists of inputs
        vol, = rescript.actions.evaluate_classifications(
            [self.taxa, taxa], [taxa, taxa])

    def test_evaluate_classifications_mismatch_input_count(self):
        with self.assertRaisesRegex(
                ValueError, "Input must contain an equal number"):
            rescript.actions.evaluate_classifications(
                [self.taxa], [self.taxa, self.taxa])

    def test_evaluate_classifications_mismatch_features(self):
        taxa = qiime2.Artifact.import_data(
            'FeatureData[Taxonomy]', self.taxa.view(pd.Series).drop('A1'))
        with self.assertRaisesRegex(
                ValueError, "Indices of pair 1 do not match"):
            rescript.actions.evaluate_classifications(
                [self.taxa], [taxa])


class TestTaxaUtilities(TestPluginBase):
    package = 'rescript.tests'

    def setUp(self):
        super().setUp()

        taxa = import_data(
            'FeatureData[Taxonomy]', self.get_data_path('derep-taxa.tsv'))
        self.taxa = taxa.view(pd.Series)
        seqs = import_data(
            'FeatureData[Sequence]', self.get_data_path('derep-test.fasta'))
        self.seqs = seqs.view(pd.Series)

    def test_stratify_taxa_k2(self):
        exp = [('k__Bacteria; p__Firmicutes; c__Bacilli; o__Bacillales; '
                'f__Paenibacillaceae; g__Paenibacillus; s__chondroitinus',
                {'A1', 'A2'}),
               ('k__Bacteria; p__Firmicutes; c__Bacilli; o__Bacillales; '
                'f__Paenibacillaceae; g__Paenibacillus; s__alvei',
                {'A3', 'A4', 'A5'}),
               ('k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; '
                'f__Lactobacillaceae; g__Lactobacillus',
                {'B1', 'B1a', 'B1b'}),
               ('k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; '
                'f__Lactobacillaceae; g__Lactobacillus; s__casei',
                {'B2', 'B3'}),
               ('k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; '
                'f__Lactobacillaceae; g__Pediococcus; s__damnosus',
                {'C1', 'C2'}),
               ('k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; '
                'f__Lactobacillaceae; g__Pediococcus; s__acidilacti',
                {'C1a', 'C1c', 'C1d'})]
        obs = cross_validate._stratify_taxa(self.taxa, self.seqs, 2)
        self.assertEquals(exp, obs)

    def test_stratify_taxa_k3(self):
        exp = [('k__Bacteria; p__Firmicutes; c__Bacilli; o__Bacillales; '
                'f__Paenibacillaceae; g__Paenibacillus; s__alvei',
                {'A1', 'A2', 'A3', 'A4', 'A5'}),
               ('k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; '
                'f__Lactobacillaceae; g__Lactobacillus',
                {'B1', 'B1a', 'B1b', 'B2', 'B3'}),
               ('k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; '
                'f__Lactobacillaceae; g__Pediococcus; s__acidilacti',
                {'C1', 'C1a', 'C1c', 'C1d', 'C2'})]
        obs = cross_validate._stratify_taxa(self.taxa, self.seqs, 3)
        self.assertEquals(exp, obs)

    def test_stratify_taxa_k5(self):
        exp = [('k__Bacteria; p__Firmicutes; c__Bacilli; o__Bacillales; '
                'f__Paenibacillaceae; g__Paenibacillus',
                {'A1', 'A2', 'A3', 'A4', 'A5'}),
               ('k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; '
                'f__Lactobacillaceae; g__Lactobacillus',
                {'B1', 'B1a', 'B1b', 'B2', 'B3'}),
               ('k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; '
                'f__Lactobacillaceae; g__Pediococcus',
                {'C1', 'C1a', 'C1c', 'C1d', 'C2'})]
        obs = cross_validate._stratify_taxa(self.taxa, self.seqs, 5)
        self.assertEquals(exp, obs)

    def test_stratify_taxa_k10(self):
        exp = [('k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; '
                'f__Lactobacillaceae',
               {'A1', 'A2', 'A3', 'A4', 'A5', 'B1', 'B1a', 'B1b', 'B2', 'B3',
                'C1', 'C1a', 'C1c', 'C1d', 'C2'})]
        obs = cross_validate._stratify_taxa(self.taxa, self.seqs, 10)
        self.assertEquals(exp, obs)

    def test_calculate_per_rank_precision_recall(self):
        # trim the reference taxa at different positions to simulate
        # classification results with underclassification
        warped_taxa = pd.Series([';'.join(t.split(';')[:n]) for n, t in zip(
            [7] * 4 + [5] * 8 + [4] * 4, self.taxa.values)])
        exp = pd.DataFrame(
            {'Level': {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7},
             'Precision': {
                0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0},
             'Recall': {
                0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 0.75, 5: 0.25, 6: 0.25},
             'F-Measure': {
                0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 0.8571428571428571, 5: 0.4,
                6: 0.4}})
        obs = cross_validate._calculate_per_rank_precision_recall(
            self.taxa, warped_taxa)
        pdt.assert_frame_equal(exp, obs)

    def test_validate_even_rank_taxonomy_pass(self):
        taxa = self.taxa.copy().drop('C1b')
        cross_validate._validate_even_rank_taxonomy(taxa)

    def test_validate_even_rank_taxonomy_fail(self):
        with self.assertRaisesRegex(ValueError, "too short: C1b"):
            cross_validate._validate_even_rank_taxonomy(self.taxa)

    def test_validate_indices_match_pass(self):
        cross_validate._validate_indices_match(self.taxa, self.seqs)

    def test_validate_indices_match_fail(self):
        taxa = self.taxa.copy().drop(['A1', 'B1'])
        with self.assertRaisesRegex(ValueError, "one input: A1, B1"):
            cross_validate._validate_indices_match(taxa, self.seqs)


class TestRelabelStratifiedTaxonomy(TestPluginBase):
    package = 'rescript.tests'

    def setUp(self):
        super().setUp()

        self.valid_taxonomies = {
            'k__Bacteria',
            'k__Bacteria; p__Firmicutes',
            'k__Bacteria; p__Firmicutes; c__Bacilli',
            'k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales',
            'k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; '
            'f__Lactobacillaceae',
            'k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; '
            'f__Lactobacillaceae; g__Lactobacillus',
            'k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; '
            'f__Lactobacillaceae; g__Lactobacillus; s__casei'}

    def test_relabel_stratified_taxonomy_known_species(self):
        species = ('k__Bacteria; p__Firmicutes; c__Bacilli; '
                   'o__Lactobacillales; f__Lactobacillaceae; '
                   'g__Lactobacillus; s__casei')
        exp = ('k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; '
               'f__Lactobacillaceae; g__Lactobacillus; s__casei')
        obs = cross_validate._relabel_stratified_taxonomy(
            species, self.valid_taxonomies)
        self.assertEquals(exp, obs)

    def test_relabel_stratified_taxonomy_unknown_species(self):
        species = ('k__Bacteria; p__Firmicutes; c__Bacilli; '
                   'o__Lactobacillales; f__Lactobacillaceae; '
                   'g__Lactobacillus; s__reuteri')
        exp = ('k__Bacteria; p__Firmicutes; c__Bacilli; o__Lactobacillales; '
               'f__Lactobacillaceae; g__Lactobacillus')
        obs = cross_validate._relabel_stratified_taxonomy(
            species, self.valid_taxonomies)
        self.assertEquals(exp, obs)

    def test_relabel_stratified_taxonomy_unknown_kingdom(self):
        species = 'k__Peanut'
        with self.assertRaisesRegex(RuntimeError, "unknown kingdom"):
            cross_validate._relabel_stratified_taxonomy(
                species, self.valid_taxonomies)
