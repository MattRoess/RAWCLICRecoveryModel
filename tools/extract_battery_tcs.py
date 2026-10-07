"""
The battery study's transfer coefficients, per element, per process family.

    ./.venv/bin/python tools/extract_battery_tcs.py

READS, NEVER WRITES, THE STUDY. Its source is the supplementary workbook of

    Maisel, Tippner, Mainuddin, Yamamoto, Iattoni (2026)
    "Quantifying transfer coefficients in battery recycling routes for
     material flow analysis: current state and future scenarios"
    documentation/BatteryStudy/1-s2.0-S0956053X2600543X-main.pdf
    documentation/BatteryStudy/1-s2.0-S0956053X2600543X-mmc1.xlsx

sheet `TC_data_Python`: 2,746 coefficients, every one carrying its value, its
uncertainty, a data-quality score, a year, a scenario and a reference.

⚠️ THE SHEET IS ALREADY IN THIS MODEL'S SCHEMA. `Input_FlowID`, `Output_FlowID`,
`TC_target_layer` and `TC_target_key` are the column names this project's cases
use, and all four are filled on all 2,746 rows. That is not a coincidence --
the study built a Python recovery model of its own on the same idea -- but it
does NOT make the sheet a case. See the end of this docstring.

THE THREE PROCESS FAMILIES, which is what `processKey` names:

    mechanical     breaking and separating, fragmentation
    hydro          leaching and solvent extraction, calcination, re-lithiation,
                   Zn-electrowinning
    thermal        pyrolysis, Waelz kiln, rotary furnace, vacuum distillation,
                   pyrometallurgy

and, upstream of all three, `preparation for reuse` -- inspection and
pack/module/cell disassembly.

⚠️ A FAMILY IS NOT A ROUTE. The paper's five routes are CHAINS of families:

    Route 1  pyrolysis (optional) + mechanical + pyrometallurgy + hydrometallurgy
    Route 2  pyrolysis (optional) + mechanical + hydrometallurgy
    Route 3  mechanical ONLY
    Route 4  pyrolysis (optional) + mechanical + pyrometallurgy + hydrometallurgy
    Route 5  direct recycling, LFP ONLY -- re-lithiation and graphite
             regeneration, to keep the cathode compound rather than dissolve it

So "mechanical" is route 3 AND the pre-treatment inside 1, 2 and 4; "direct" is
route 5 and nothing else. `processID` is the position in the chain, which is
how a family's rows are placed in a route.

⚠️ AND THE COEFFICIENTS ARE CHEMISTRY-BLIND, which the paper states as a
limitation in its own words:

    the TCs for LIB recycling are defined for a generic LIB input stream
    without differentiation by cathode chemistry, except for direct recycling
    (Route 5) explicitly designed for LFP batteries. This represents an
    important limitation, since different cathode chemistries can yield
    systematically different recovery pathways.

Searched across all 2,746 rows, `NMC`, `LFP` and `LMFP` appear ZERO times.
Sodium does appear -- `SIB` 99 times, `battNaRechargeable` on 200 rows. So a
split into NMC low/middle/high, LFP, LMFP and two sodium chemistries cannot
come from these coefficients: the recovery performance here is per ELEMENT, and
the chemistry has to enter through composition instead.

WHAT THIS WRITES, all under documentation/:

    battery_transfer_coefficients.csv   every row, flattened, with its
                                        provenance -- the table to check
    battery_family_summary.csv          per family x element: how many
                                        coefficients, their range, the spread
                                        of the data-quality scores
    BATTERY_COEFFICIENTS.md             the same, written out, with what is
                                        missing stated as plainly as what is
                                        there
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

STUDY = ('documentation/BatteryStudy/'
         '1-s2.0-S0956053X2600543X-mmc1.xlsx')
SHEET = 'TC_data_Python'
OUT = 'documentation'

# ⚠️ THE FAMILIES ARE THE STUDY'S OWN `processKey`, GROUPED, NOT INVENTED HERE.
# Seven keys appear; they fall into three families plus the preparation step
# that precedes all of them. Anything unrecognised is kept and labelled, rather
# than dropped -- a key this map does not know about is a fact about the study,
# not a row to discard.
FAMILY = {
    'mechanical recovery processes': 'mechanical',
    'hydrometallurgy batteries': 'hydro',
    'chemical recovery processes': 'hydro',
    'pyrometallurgy batteries ': 'thermal',
    'pyrometallurgy batteries': 'thermal',
    'thermal recovery processes': 'thermal',
    'pyrolysis': 'thermal',
    'preparation for reuse': 'preparation',
}

KEEP = ['dataEntryID', 'processID', 'descriptionFromDataSource', 'processLevel',
        'processKey', 'TCtype', 'Input_FlowID', 'Input_layer',
        'Input_layer_key', 'Output_FlowID', 'TC_target_layer', 'TC_target_key',
        'value', 'valueLowerLimit', 'uncertainty%', 'Factors that influence the TC',
        'Year', 'dataQuality', 'valueGeneration', 'reference', 'referenceURL']


def read_study() -> pd.DataFrame:
    """The coefficient sheet, with a `family` column and nothing else added."""
    path = os.path.join(os.path.dirname(HERE), STUDY) \
        if not os.path.exists(STUDY) else STUDY
    frame = pd.read_excel(path, sheet_name=SHEET, header=1).dropna(how='all')
    present = [column for column in KEEP if column in frame.columns]
    frame = frame[present].copy()
    keys = frame['processKey'].astype(str).str.strip()
    frame['family'] = keys.map(
        {k.strip(): v for k, v in FAMILY.items()}).fillna('UNMAPPED')
    frame['scenario'] = frame['Factors that influence the TC']
    return frame


def spread(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Per family and element: how many coefficients, and what they say.

    `value` is a share, so min and max are the span the study reports for that
    element in that family ACROSS its processes, years and scenarios -- it is
    not an uncertainty range on one number. The uncertainty of a single
    coefficient is its own `uncertainty%`, carried through to the CSV.
    """
    rows = []
    for (family, element), block in frame.groupby(['family', 'TC_target_key']):
        values = pd.to_numeric(block['value'], errors='coerce').dropna()
        if values.empty:
            continue
        quality = pd.to_numeric(block['dataQuality'], errors='coerce').dropna()
        rows.append({
            'family': family,
            'element': element,
            'layer': block['TC_target_layer'].iloc[0],
            'coefficients': len(block),
            'processes': block['descriptionFromDataSource'].nunique(),
            'min': round(float(values.min()), 4),
            'median': round(float(values.median()), 4),
            'max': round(float(values.max()), 4),
            'years': f"{int(block['Year'].min())}-{int(block['Year'].max())}",
            'scenarios': ';'.join(sorted(block['scenario'].astype(str).unique())),
            'data_quality_best': round(float(quality.min()), 1) if len(quality) else None,
            'data_quality_worst': round(float(quality.max()), 1) if len(quality) else None,
            'references': block['reference'].nunique(),
        })
    return pd.DataFrame(rows).sort_values(['family', 'coefficients'],
                                          ascending=[True, False])


def main() -> int:
    frame = read_study()
    os.makedirs(OUT, exist_ok=True)

    full = os.path.join(OUT, 'battery_transfer_coefficients.csv')
    frame.to_csv(full, index=False)

    summary = spread(frame)
    short = os.path.join(OUT, 'battery_family_summary.csv')
    summary.to_csv(short, index=False)

    print(f'{full}: {len(frame)} coefficients')
    print(f'{short}: {len(summary)} family x element combinations\n')
    counts = frame.groupby('family').size().sort_values(ascending=False)
    for family, n in counts.items():
        elements = frame[frame.family == family]['TC_target_key'].nunique()
        print(f'  {family:14s} {n:5d} coefficients, {elements:3d} targets')
    unmapped = frame[frame.family == 'UNMAPPED']['processKey'].unique()
    if len(unmapped):
        print(f'\n  ⚠️ processKey not in FAMILY: {list(unmapped)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
