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


def test_convert_transition1x_reads_official_hdf5_shape(tmp_path):
    h5py = pytest.importorskip("h5py")
    from reproductions.ts_dfm_2511_17229.data import convert_transition1x, load_jsonl

    h5_path = tmp_path / "Transition1x.h5"
    with h5py.File(h5_path, "w") as handle:
        reaction = handle.create_group("train/C2H6/rxn000")
        for name in ["reactant", "product", "transition_state"]:
            group = reaction.create_group(name)
            group.create_dataset("atomic_numbers", data=np.array([6, 6, 1, 1]))
            group.create_dataset("positions", data=np.zeros((1, 4, 3)))

    output = tmp_path / "sample.jsonl"
    count = convert_transition1x(h5_path, output, split="train", limit=1)

    rows = load_jsonl(output)
    assert count == 1
    assert rows[0]["z"] == [6, 6, 1, 1]
