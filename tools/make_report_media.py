"""Make the images in media/report/ that the PHS3360 report includes.

pdflatex cannot read TIFF files, so this script converts the view-camera frames to PNG.
It also draws two figures from the repo data:
    probe_angle_limits.png     grating lifetime and Doppler width for the 4 deg probe
    optimisation_run_1.png,
    optimisation_run_2.png     N_f through each of the two optimisation runs

    python tools/make_report_media.py
"""
import csv
import datetime
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
MEDIA = REPO / 'media'
OUT = MEDIA / 'report'
REPORT = REPO / 'reports' / '2026-10-25_mot_characterisation'

SURFACE = '#fcfcfb'
INK = '#0b0b0b'
INK_2 = '#52514e'
GRID = '#e4e3df'
VALID_BAND = '#e8e7e2'
BLUE = '#2a78d6'
ORANGE = '#eb6834'
TEMP_RAMP = {100: '#86b6ee', 146: '#2a78d6', 700: '#0e3f7e'}     # one hue, light to dark

# Probe design of the report: the probe angle comes from geometry.py, the rest from fwm_model.json.
PROBE_ANGLE_DEG = 4.0
PROBE_PULSE_S = 100e-6
ZHAO_ANGLE_DEG, ZHAO_TAU_US, ZHAO_TAU_ERR_US = 3.0, 25.0, 1.0    # Zhao et al. 2009, Fig. 3, about 100 uK

# Each optimisation run, from its first scan shot to its last check shot.
RUNS = [dict(file='optimisation_run_1.png', first=20, last=36, color=BLUE,
             event_run='0034', event='repump corrected by hand'),
        dict(file='optimisation_run_2.png', first=41, last=56, color=ORANGE,
             pause=('0044', '0045'), event='pause: repump re-lock')]


def convert_tiff_frames():
    for name in ('nomot', 'WEGOTAMOT', 'motoptimised'):
        Image.open(MEDIA / f'{name}.tif').convert('L').save(OUT / f'{name}.png', optimize=True)


def style_axes(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.tick_params(colors=INK_2, labelsize=8, length=3)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color('#b9b8b2')
    ax.xaxis.label.set_color(INK_2)
    ax.yaxis.label.set_color(INK_2)


def reference_line(ax, y, label, x_text):
    ax.axhline(y, color=INK_2, linewidth=1, linestyle='--')
    ax.text(x_text, y * 1.25, label, color=INK_2, fontsize=8, va='bottom', ha='left')


def draw_probe_angle_limits():
    """Draw the motional limits against the limits that apply with the MOT light on."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    sys.path.insert(0, str(REPO / 'analysis' / 'probe_angle'))
    import max_probe_angle as mpa

    zeeman = json.loads((REPORT / 'fwm_model.json').read_text())['zeeman']
    width_hz, split_hz = zeeman['raman_fwhm_Hz'], zeeman['raman_split_Hz']
    coherence_s = 1 / (math.pi * width_hz)
    theta_deg = np.logspace(-1, np.log10(30), 200)
    q = mpa.q_transmission(np.radians(theta_deg))
    q_probe = mpa.q_transmission(math.radians(PROBE_ANGLE_DEG))
    labels = {100: '100 µK', 146: '146 µK (Doppler limit)', 700: '700 µK (thesis MOT)'}
    temperature_k = {100: 100e-6, 146: mpa.T_DOPPLER, 700: 700e-6}

    fig, (left, right) = plt.subplots(1, 2, figsize=(10.5, 4.2), facecolor=SURFACE)
    for key, colour in TEMP_RAMP.items():
        left.plot(theta_deg, mpa.tau_dephasing(q, temperature_k[key]) * 1e6, color=colour, lw=2, label=labels[key])
        right.plot(theta_deg, mpa.raman_doppler_fwhm_hz(q, temperature_k[key]), color=colour, lw=2, label=labels[key])

    left.errorbar([ZHAO_ANGLE_DEG], [ZHAO_TAU_US], yerr=[ZHAO_TAU_ERR_US], fmt='o', color=INK, markersize=7,
                  markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=5, label='Zhao et al. 2009 (about 100 µK)')
    reference_line(left, PROBE_PULSE_S * 1e6, '100 µs probe pulse', 4.6)
    reference_line(left, coherence_s * 1e6, f'decay under the MOT light ({coherence_s * 1e6:.2f} µs)', 0.115)
    reference_line(right, split_hz, f'Raman resonance at 3 G, δ = {split_hz / 1e6:.1f} MHz', 0.115)
    reference_line(right, width_hz, f'width from the MOT light, {width_hz / 1e6:.1f} MHz', 0.115)

    tau_us = mpa.tau_dephasing(q_probe, 700e-6) * 1e6
    fwhm_hz = mpa.raman_doppler_fwhm_hz(q_probe, 700e-6)
    for ax, y, text, offset in ((left, tau_us, f'{tau_us:.1f} µs', (-40, -16)),
                                (right, fwhm_hz, f'{fwhm_hz / 1e3:.0f} kHz', (-44, 9))):
        ax.axvline(PROBE_ANGLE_DEG, color=INK_2, linewidth=1, linestyle=':')
        ax.plot([PROBE_ANGLE_DEG], [y], 'o', color=TEMP_RAMP[700], markersize=8, markeredgecolor=SURFACE,
                markeredgewidth=2, zorder=6)
        ax.annotate(text, (PROBE_ANGLE_DEG, y), xytext=offset, textcoords='offset points', fontsize=8.5, color=INK)

    left.set(xscale='log', yscale='log', xlim=(0.1, 30), ylim=(0.05, 3e3), xlabel='probe-pump angle θ (deg)',
             ylabel='lifetime from motion, τ$_D$ (µs)')
    right.set(xscale='log', yscale='log', xlim=(0.1, 30), ylim=(3e2, 2e7), xlabel='probe-pump angle θ (deg)',
              ylabel='Raman Doppler FWHM (Hz)')
    for ax in (left, right):
        style_axes(ax)
        ax.text(PROBE_ANGLE_DEG * 1.06, ax.get_ylim()[1] * 0.55, '4° probe', fontsize=8, color=INK_2)
    fig.legend(*left.get_legend_handles_labels(), frameon=False, fontsize=8.5, labelcolor=INK_2, ncol=4,
               loc='upper center')
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OUT / 'probe_angle_limits.png', dpi=200, facecolor=SURFACE)
    plt.close(fig)


def load_shots():
    with open(REPORT / 'mot_properties.csv', newline='') as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row['t'] = datetime.datetime.fromisoformat(row['time'])
        row['number'] = int(row['run'])
        row['N_f'] = float(row['N_f'])
    return rows


def load_scan_verdicts():
    with open(REPORT / 'scan_summary.csv', newline='') as handle:
        return {row['run']: row for row in csv.DictReader(handle)}


def draw_optimisation_runs():
    """Draw one panel for each run, on the same axes, against the minutes since the run start."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    rows, scans = load_shots(), load_scan_verdicts()
    for spec in RUNS:
        shots = [r for r in rows if spec['first'] <= r['number'] <= spec['last']]
        start = min(r['t'] for r in shots)
        minutes = lambda t: (t - start).total_seconds() / 60
        duration = minutes(max(r['t'] for r in shots))

        fig, ax = plt.subplots(figsize=(10.5, 3.2), facecolor=SURFACE)
        for run in sorted({r['run'] for r in shots}):
            if run not in scans:
                continue
            times = [minutes(r['t']) for r in shots if r['run'] == run]
            if scans[run]['verdict'] == 'valid':
                ax.axvspan(min(times), max(times), color=VALID_BAND, lw=0, zorder=0)
            ax.text((min(times) + max(times)) / 2, 8.3, scans[run]['scan'], rotation=90, va='top', ha='center',
                    fontsize=7.5, color=INK_2)

        scan_shots = [r for r in shots if r['run'] in scans]
        check_shots = [r for r in shots if r['run'] not in scans]
        ax.scatter([minutes(r['t']) for r in scan_shots], [r['N_f'] / 1e9 for r in scan_shots], s=11,
                   color=spec['color'], alpha=0.55, lw=0, zorder=2, label='scan shots')
        ax.scatter([minutes(r['t']) for r in check_shots], [r['N_f'] / 1e9 for r in check_shots], s=46,
                   color=spec['color'], edgecolor=SURFACE, lw=1.5, zorder=3, label='check shots')

        if 'event_run' in spec:
            times = [minutes(r['t']) for r in shots if r['run'] == spec['event_run'] and r['N_f'] > 1e9]
            ax.annotate(spec['event'], (min(times), 1.0), xytext=(min(times) - 9.5, 3.0), fontsize=8, color=INK,
                        arrowprops=dict(arrowstyle='-', color=INK_2, lw=0.8))
            pause_min = 0
        else:
            before, after = spec['pause']
            t0 = minutes(next(r['t'] for r in shots if r['run'] == before))
            t1 = minutes(next(r['t'] for r in shots if r['run'] == after))
            pause_min = t1 - t0
            ax.text((t0 + t1) / 2, 5.2, f"{spec['event']}\n({pause_min:.0f} min)", ha='center', fontsize=8, color=INK)

        style_axes(ax)
        ax.set(xlim=(-0.5, 40), ylim=(0, 8.5), xlabel='minutes since the start of the run', ylabel='$N_f$ ($10^9$ counts)')
        handles, names = ax.get_legend_handles_labels()
        handles.append(Patch(color=VALID_BAND))
        names.append('valid scan')
        ax.legend(handles, names, frameon=False, fontsize=8, labelcolor=INK_2, ncol=3, loc='lower left',
                  bbox_to_anchor=(0, 1.0), borderaxespad=0.2)
        fig.tight_layout()
        fig.savefig(OUT / spec['file'], dpi=200, facecolor=SURFACE)
        plt.close(fig)

        counted = [r for r in scans.values() if spec['first'] <= int(r['run']) <= spec['last']]
        valid = sum(r['verdict'] == 'valid' for r in counted)
        print(f"{spec['file']}: {len(shots)} shots, {duration:.1f} min, pause {pause_min:.1f} min, "
              f"{valid} valid of {len(counted)} scans")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    convert_tiff_frames()
    draw_probe_angle_limits()
    draw_optimisation_runs()
    for path in sorted(OUT.iterdir()):
        print(f'{path.name:32s} {path.stat().st_size / 1024:8.0f} kB')


if __name__ == '__main__':
    main()
