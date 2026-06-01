import pytest

from reproductions.ts_dfm_2511_17229.data import make_synthetic_rows


np = pytest.importorskip("numpy")

from reproductions.ts_dfm_2511_17229.geometry import classical_mds, pairwise_distances
from reproductions.ts_dfm_2511_17229.metrics import dmae, rmsd


def test_pairwise_distances_are_symmetric():
    coords = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 2.0, 0.0]])

    distances = pairwise_distances(coords)

    assert distances.shape == (3, 3)
    assert np.allclose(distances, distances.T)
    assert np.allclose(np.diag(distances), 0.0)


def test_mds_recovers_distance_geometry_up_to_small_error():
    coords = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    distances = pairwise_distances(coords)

    recovered = classical_mds(distances)

    assert dmae(recovered, coords) < 1e-6


def test_rmsd_handles_rigid_translation():
    coords = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    shifted = coords + np.array([10.0, -2.0, 1.0])

    assert rmsd(shifted, coords) < 1e-6


def test_synthetic_rows_have_reaction_triplets():
    rows = make_synthetic_rows(count=2, atoms=4)

    assert len(rows) == 2
    assert set(rows[0]) == {"z", "reactant", "product", "ts"}
