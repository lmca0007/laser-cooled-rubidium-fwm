# Lost MOT, recovery, CMOT/PGC check and FWM probe plan (22 Oct 2026, evening)

This continues [the morning report](../2026-10-22_mot_scan_fwm/README.md). It covers shots 0055–0063, after the 200 mW beam was routed out of the old side-imaging path.

Every number here can be reproduced without the lab share. `mot_comparison.py` reads the reduced shot data in [data/2026-10-22](../../data/2026-10-22) and writes `mot_comparison.csv`.

```
python reports/2026-10-22_lost_mot_and_fwm_probe/mot_comparison.py
```

## Summary

- **The MOT disappeared after the beam was rerouted (0057–0060).** The shot files rule out code, coil, vacuum and camera-trigger causes, so the loss was optical.
- **Re-aligning the fibres brought the MOT back (0061), but it is about 70–200× dimmer than 0056.** The cloud has also moved about 260 px (1.2 mm) horizontally on the side camera.
- **`keep_2d_mot_on` is not the cause.** 0063 has it on and is still about 200× dimmer than 0056. Look at the optics instead. The vertical MOT beam is 11 mW, against 25 mW for each horizontal beam. That is a candidate, though an imbalance between axes alone rarely costs this much.
- **CMOT/PGC (0062 against 0061):** no atoms are lost, but these shots can't show any cooling. A repump-shutter timing clash also makes the fluorescence image unreliable in PGC shots.
- **FWM probe plan:** out of date. See section 4.

## Timeline

| Shots | Time | What happened |
|---|---|---|
| 0055–0056 | 20:28–20:31 | Last good MOT. `keep_2d_mot_on` = True (left on by `mot_scan.py`), 1 s load |
| — | 20:31–22:03 | 200 mW routed out of the old side-imaging path into a beam dump, controlled by `side_imaging_shutter` |
| 0057–0059 | 22:03–22:06 | No MOT. `keep_2d_mot_on` = False, 6 s load |
| 0060 | 22:55 | No MOT. The master laser shutter no longer gated the vertical MOT beam |
| — | 22:55–22:59 | Fibres re-aligned |
| 0061 | 22:59 | MOT back, weak. CMOT and PGC off |
| 0062 | 23:07 | Same with CMOT and PGC on |
| 0063 | 23:45 | `keep_2d_mot_on` = True, exposure 0.6 → 1.0 ms, CMOT and PGC on |

## 1. Lost MOT (0057–0060)

| Check | Good (0056) | Bad (0057–0059) | Conclusion |
|---|---|---|---|
| Atoms − dark in the MOT region | about 6300 counts | 0.0 ± 0.6 | Nothing on the camera, not even a weak cloud |
| Stored script and connection table | — | Identical | Not a code change |
| Quad / Z-bias monitors during the load | 0.700 / 0.165 V | 0.700 / 0.165 V | Coils fine |
| Pressure gauge (IGC) during the load | 0.120 V | 0.121 V | Vacuum fine |
| `mot_fluorescence` photodiode | 0.214 V | 0.214 V | See below |
| Camera dark frame | 161.9, same structure | 162.0, same structure | The camera triggers and exposes normally |

The lyse fits on 0057–0059 report N ≈ 10⁶–10⁷ at random positions. These are fits to noise.

**`mot_fluorescence` measures MOT beam light, not atoms.** It reads 0.214 V during the load in every shot, whether or not there is a MOT (0057–0060 have none). In 0061 it falls to 0.047 V when `science_trap_aom` switches off. Don't use it to judge the MOT.

The suspected causes, in the order they were checked: push beam power or alignment (it shares `imaging_push_aom` with the old imaging path), a blocked camera view, the repump lock, stray 200 mW light. The vertical beam then turned out to be no longer passing the master laser shutter, and the MOT came back once the fibres were re-aligned.

### Vertical MOT beam: no documentation found

No document says how the vertical beam takes its light from the master laser or which shutter it passes. These places were searched:
- this repo, which covers only the horizontal axes 1-5 and 3-7;
- the krb2 OneNote notebook (`Z:\Experiments\krb2\KRb2Apparatus`), which has alignment tips only;
- the SolidWorks MOT-beam parts in `Z:\Projects\NewDualSpeciesExperiment\MOT Beams`;
- `Z:\Apparatus\dualspecies\Laser Table Layout.pdf` and `motsplit.ai`, which date from 2012 and are probably the older experiment;
- the Troubleshooting Guide in `Z:\Apparatus`, which is for the spinor lab;
- `Z:\Experiments\krb2\ShutterCalibration`, which holds 2017 data only.

**To do:** write the vertical beam route and the shutter-to-path map into the repo once traced.

What the sequence does show:
- `master_laser_shutter` is on port0/line18. It is the only light shutter with delay (0, 0), so its timing was probably never calibrated.
- `science_mot_shutter` is on line23 and `repump_laser_shutter` on line19. Both gate MOT light.

## 2. Recovered MOT (0061–0063)

From `mot_comparison.py`. Sum is the background-subtracted fluorescence around the cloud, from the side camera. Sizes are rms, in raw pixels (× 4.485 µm).

| Shot | 2D MOT kept on | Load | Exposure | CMOT/PGC | Sum | vs 0056 | Centre y, x (px) | rms y, x (px) |
|---|---|---|---|---|---|---|---|---|
| 0055 (35 shots) | yes | 1 s | 0.6 ms | off | 1.27 × 10⁹ ± 9 % | 0.90 | 333, 1468 | 131, 125 |
| 0056 | yes | 1 s | 0.6 ms | off | 1.41 × 10⁹ | 1 | 325, 1459 | 131, 126 |
| 0057–0060 | no | 6 s | 0.6 ms | off | ≈ 1.5 × 10⁵ (noise) | 0.0001 | random | — |
| 0061 | no | 6 s | 0.6 ms | off | 1.51 × 10⁷ | 0.011 | 312, 1724 | 90, 114 |
| 0062 | no | 6 s | 0.6 ms | on | 2.02 × 10⁷ | 0.014 | 439, 1743 | 106, 119 |
| 0063 | yes | 6 s | 1.0 ms | on | 0.68 × 10⁷ | 0.005 | 435, 1718 | 103, 113 |

- **The MOT is 70–200× dimmer than at 20:30, even with a 6 s load against 1 s.**
- **0063 rules out the 2D MOT recovery time.** It ran with `keep_2d_mot_on` = True and a 1.7× longer exposure, and it is still 3× dimmer than 0062. These are single shots, so 0062 and 0063 are only roughly comparable. Even so, nothing points to the 2D MOT setting.
- **The cloud moved 260 px (1.2 mm) along x on the camera after the realignment.** That points to a change in the beam balance or overlap.
- **Vertical beam:** 11 mW against 25 mW for each horizontal beam (measured by hand). Each axis is retro-reflected, so it stays balanced with itself. Weaker axes mostly change the cloud's shape and position, and rarely cost a factor of 100 in atom number. Check also:
  - the fibre output powers after the re-coupling;
  - the balance between each beam and its retro, and their polarisation;
  - the push beam power, which shares `imaging_push_aom` with the new 200 mW path.

## 3. Do CMOT and PGC do anything? (0061 against 0062)

Only `s02_CMOT` and `s03_PGC` differ between the two shots.

| | 0061 (off) | 0062 (on) |
|---|---|---|
| Sum | 1.51 × 10⁷ | 2.02 × 10⁷ (+35 %) |
| Centre y | 312 px | 439 px |
| rms y, x | 90, 114 px | 106, 119 px |

- **No atoms are lost, but there is no evidence of cooling.** The drop time is 0.5 ms, too short for the cloud to expand. A time-of-flight series is needed: drop times of 1–10 ms with the stages on and off, fitting σ² = σ₀² + (k_B T/m) t².
- **CMOT turns the light up, not down.** At constant AOM amplitude (0.5), the photodiode rises from 0.214 to 0.256 V when the trap AOM ramps 83.5 → 79 MHz. That is 25 % more light above the 0.047 V background, because the AOM is more efficient at 79 MHz. A CMOT normally lowers the intensity.
- **CMOT runs for about 105 ms, not 5 ms.** The `t += 100e-3` hold after CMOT keeps the compressed settings.
- **The PGC repump ramp does nothing.** `pgc_repump_amp_initial` and `pgc_repump_amp_final` are both 0.5.
- **PGC bias fields are all 0 A, while the MOT uses 0.4 A on z.** If 0.4 A cancels a background field, PGC runs in an uncancelled field, which spoils sub-Doppler cooling.
- **Bug: repump shutter timing.**
  - PGC closes `repump_laser_shutter` at end − `repump_wait`. The command goes out at 6.7194 s, including the 3.32 ms close delay.
  - The fluorescence branch opens it at start − 10 ms, sent at 6.7111 s.
  - The later command wins, so in PGC shots the repump shutter is closed during both fluorescence frames.
  - 0062 still shows atoms. Either the shutter doesn't fully block the science repump, or the atoms weren't fully pumped into F = 1.
  - Either way, 0062's image isn't comparable with 0061's.
- **For FWM, keep the atoms in F = 2:** `repump_wait` = 0.

**Recommendation:** turn CMOT and PGC off for the first FWM attempts and use the steady-state MOT as the medium. Come back to PGC with a time-of-flight series. Fix the repump shutter timing first.

## 4. FWM probe plan (out of date)

This section planned an 8° punch-through probe at MOT beam 1-5, a 1 MΩ detector and a 10 µW probe. The three build sheets for that plan are deleted. The current design is a 4° arm beside MOT axis B, 3.2 mW at the cloud and a 100 kΩ load. See [optics/fwm_probe/README.md](../../optics/fwm_probe/README.md) for the current layout and [the 25 Oct report, section 5](../2026-10-25_mot_characterisation/README.md) for the probe power, the detection and the Zeeman settings.

## Open items

- **Find why the MOT is 70–200× weaker than 0056:**
  - fibre output powers;
  - vertical beam power (11 mW against 25 mW);
  - each beam against its retro;
  - push beam power.
- Trace and document the vertical MOT beam route and which shutter gates it.
- Fix the repump-shutter clash between PGC and fluorescence imaging, and set `repump_wait` = 0 for FWM.
- Add a probe window with a photodiode AnalogIn to `4wavemixing.py`. It needs a free AnalogIn channel.
- Run a time-of-flight series before deciding on CMOT/PGC.

## Files

| File | Contents |
|---|---|
| `mot_comparison.py` / `.csv` | Brightness, centre, size and photodiode levels for 0055–0063 from the reduced data |
| [data/2026-10-22](../../data/2026-10-22) | Reduced copies of all 851 shots from the day (see [data/README.md](../../data/README.md)) |
