"""Random-number construction for reproducible worlds and experiments."""

import numpy as np


def make_rng(seed: int | None) -> np.random.Generator:
    """Construct a random-number generator owned by one caller."""

    return np.random.default_rng(seed)


def spawn_rngs(seed: int | None, count: int) -> tuple[np.random.Generator, ...]:
    """Create reproducible, statistically separated child generators."""

    if count < 0:
        raise ValueError("count must be non-negative")
    children = np.random.SeedSequence(seed).spawn(count)
    return tuple(np.random.default_rng(child) for child in children)
