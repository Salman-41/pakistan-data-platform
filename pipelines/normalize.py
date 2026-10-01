"""Reviewed geography and unit normalization, never national-to-district imputation."""
import pandas as pd
import numpy as np


def normalize_chunk(frame: pd.DataFrame, *, geography_aliases=None, units=None):
    """Return canonical long values using explicit, version-controlled mappings.

    units maps old unit to (canonical unit, multiplicative factor); no conversion
    is guessed. Percentages and currency bases require a reviewed source contract.
    """
    frame = frame.copy()
    frame['geography'] = frame['geography'].astype(str).str.strip()
    if geography_aliases:
        frame['geography'] = frame['geography'].replace(geography_aliases)
    frame['value'] = pd.to_numeric(frame['value'], errors='coerce')
    for old_unit, (new_unit, factor) in (units or {}).items():
        if not np.isfinite(factor) or factor <= 0:
            raise ValueError('Unit factors must be finite and positive')
        selected = frame['unit'].eq(old_unit)
        frame.loc[selected, 'value'] *= factor
        frame.loc[selected, 'unit'] = new_unit
    return frame
