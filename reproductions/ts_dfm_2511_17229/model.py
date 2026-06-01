from __future__ import annotations

from typing import Any


def require_torch() -> Any:
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("Install torch with `pip install -e '.[ts-dfm]'`.") from exc
    return torch


def build_tsdvnet(**kwargs: Any) -> Any:
    torch = require_torch()
    nn = torch.nn

    class TimeEmbedding(nn.Module):
        def __init__(self, dim: int) -> None:
            super().__init__()
            self.dim = dim

        def forward(self, t: Any) -> Any:
            half = self.dim // 2
            device = t.device
            scale = torch.exp(-torch.log(torch.tensor(10000.0, device=device)) * torch.arange(half, device=device) / max(half - 1, 1))
            values = t[:, None] * scale[None, :]
            return torch.cat([torch.sin(values), torch.cos(values)], dim=-1)

    class TSDVNet(nn.Module):
        """Compact two-branch approximation of the paper's TSDVNet.

        It preserves the reproduction-critical contract:
        input `(Z, D_R, D_P, D_TS_t, t)` and output a permutation-compatible
        pairwise velocity matrix. Full triangular updates can be swapped in later.
        """

        def __init__(
            self,
            atom_dim: int = 128,
            pair_dim: int = 128,
            layers: int = 6,
            rbf_dim: int = 64,
            cutoff: float = 20.0,
        ) -> None:
            super().__init__()
            self.cutoff = cutoff
            self.atom_embedding = nn.Embedding(119, atom_dim)
            self.time_embedding = TimeEmbedding(atom_dim)
            input_dim = 3 + atom_dim * 2
            blocks = []
            hidden = pair_dim
            for index in range(layers):
                blocks.append(nn.Linear(input_dim if index == 0 else hidden, hidden))
                blocks.append(nn.SiLU())
                blocks.append(nn.LayerNorm(hidden))
            self.pair_mlp = nn.Sequential(*blocks)
            self.output = nn.Linear(hidden, 1)

        def forward(self, z: Any, d_r: Any, d_p: Any, d_ts_t: Any, t: Any) -> Any:
            atom = self.atom_embedding(z.long())
            atom = atom + self.time_embedding(t)[:, None, :]
            atom_i = atom[:, :, None, :].expand(-1, -1, z.shape[1], -1)
            atom_j = atom[:, None, :, :].expand(-1, z.shape[1], -1, -1)
            pair_input = torch.cat([d_r[..., None], d_p[..., None], d_ts_t[..., None], atom_i, atom_j], dim=-1)
            velocity = self.output(self.pair_mlp(pair_input)).squeeze(-1)
            velocity = 0.5 * (velocity + velocity.transpose(-1, -2))
            diagonal = torch.eye(velocity.shape[-1], device=velocity.device, dtype=torch.bool)
            velocity = velocity.masked_fill(diagonal[None, :, :], 0.0)
            return velocity

    return TSDVNet(**kwargs)
