# Measured comparison

Fixed-seed textured images. Fresh process per trial. Original batch sleep=0; fork sequential; default quality policies differ. Conversion includes redesign verification/fsync. Fidelity is checked outside timing for every page. Temporary logical byte samples every 5 ms are lower bounds. CBR not measured: no representative comic RAR fixture.

| Workload | Implementation | Workers | Median seconds | Peak RSS MiB | Output MiB | Exact ordered pixels | Pages |
|---|---|---:|---:|---:|---:|---:|---:|
| high-resolution | fork | 1 | 1.7605 | 191.4 | 11.53 | 0/4 | 4/4 |
| high-resolution | original | 1 | 1.2803 | 299.4 | 30.89 | 0/4 | 4/4 |
| high-resolution | original | 2 | 1.2914 | 299.1 | 30.89 | 0/4 | 4/4 |
| high-resolution | original | 4 | 1.2694 | 299.4 | 30.89 | 0/4 | 4/4 |
| high-resolution | redesigned | 1 | 0.2578 | 286.9 | 124.48 | 4/4 | 4/4 |
| high-resolution | redesigned | 2 | 0.2647 | 286.9 | 124.48 | 4/4 | 4/4 |
| high-resolution | redesigned | 4 | 0.2601 | 286.9 | 124.48 | 4/4 | 4/4 |
| large-jpeg | fork | 1 | 0.5078 | 487.0 | 212.72 | 24/24 | 24/24 |
| large-jpeg | original | 1 | 2.0812 | 408.4 | 52.88 | 0/24 | 24/24 |
| large-jpeg | original | 2 | 2.1806 | 408.6 | 52.88 | 0/24 | 24/24 |
| large-jpeg | original | 4 | 2.2022 | 408.8 | 52.88 | 0/24 | 24/24 |
| large-jpeg | redesigned | 1 | 0.3951 | 390.7 | 212.72 | 24/24 | 24/24 |
| large-jpeg | redesigned | 2 | 0.3996 | 390.9 | 212.72 | 24/24 | 24/24 |
| large-jpeg | redesigned | 4 | 0.4122 | 390.7 | 212.72 | 24/24 | 24/24 |
| many-small-volumes | fork | 1 | 0.1568 | 46.1 | 17.06 | 48/48 | 48/48 |
| many-small-volumes | original | 1 | 0.2564 | 45.9 | 4.28 | 0/48 | 48/48 |
| many-small-volumes | original | 2 | 0.1848 | 48.9 | 4.28 | 0/48 | 48/48 |
| many-small-volumes | original | 4 | 0.1557 | 56.4 | 4.28 | 0/48 | 48/48 |
| many-small-volumes | redesigned | 1 | 0.0742 | 56.6 | 17.06 | 48/48 | 48/48 |
| many-small-volumes | redesigned | 2 | 0.0624 | 57.3 | 17.06 | 48/48 | 48/48 |
| many-small-volumes | redesigned | 4 | 0.0621 | 53.9 | 17.06 | 48/48 | 48/48 |
| mixed-format | fork | 1 | 0.1100 | 60.7 | 4.85 | 2/6 | 5/6 |
| mixed-format | original | 1 | 0.0615 | 53.1 | 1.10 | 0/6 | 2/6 |
| mixed-format | original | 2 | 0.0617 | 53.0 | 1.10 | 0/6 | 2/6 |
| mixed-format | original | 4 | 0.0576 | 52.9 | 1.10 | 0/6 | 2/6 |
| mixed-format | redesigned | 1 | 0.2073 | 62.8 | 3.96 | 6/6 | 6/6 |
| mixed-format | redesigned | 2 | 0.2073 | 62.9 | 3.96 | 6/6 | 6/6 |
| mixed-format | redesigned | 4 | 0.2102 | 62.8 | 3.96 | 6/6 | 6/6 |
| nested | fork | 1 | 0.0628 | 48.6 | 2.14 | 12/12 | 12/12 |
| nested | original | 1 | 0.1055 | 69.0 | 3.75 | 0/12 | 12/12 |
| nested | original | 2 | 0.1112 | 68.4 | 3.75 | 0/12 | 12/12 |
| nested | original | 4 | 0.1095 | 68.8 | 3.75 | 0/12 | 12/12 |
| nested | redesigned | 1 | 0.0921 | 43.1 | 2.14 | 12/12 | 12/12 |
| nested | redesigned | 2 | 0.0934 | 43.0 | 2.14 | 12/12 | 12/12 |
| nested | redesigned | 4 | 0.0887 | 43.1 | 2.14 | 12/12 | 12/12 |
| png-heavy | fork | 1 | 0.0934 | 51.4 | 2.52 | 8/8 | 8/8 |
| png-heavy | original | 1 | 0.1584 | 95.7 | 7.21 | 0/8 | 8/8 |
| png-heavy | original | 2 | 0.1616 | 95.9 | 7.21 | 0/8 | 8/8 |
| png-heavy | original | 4 | 0.1572 | 96.2 | 7.21 | 0/8 | 8/8 |
| png-heavy | redesigned | 1 | 0.1428 | 47.6 | 2.52 | 8/8 | 8/8 |
| png-heavy | redesigned | 2 | 0.1436 | 47.6 | 2.52 | 8/8 | 8/8 |
| png-heavy | redesigned | 4 | 0.1383 | 47.6 | 2.52 | 8/8 | 8/8 |
| several-large-volumes | fork | 1 | 4.6684 | 146.4 | 89.21 | 0/24 | 24/24 |
| several-large-volumes | original | 1 | 2.5318 | 202.8 | 64.51 | 0/24 | 24/24 |
| several-large-volumes | original | 2 | 1.9654 | 365.2 | 64.51 | 0/24 | 24/24 |
| several-large-volumes | original | 4 | 1.3012 | 527.8 | 64.51 | 0/24 | 24/24 |
| several-large-volumes | redesigned | 1 | 0.7474 | 393.3 | 259.01 | 24/24 | 24/24 |
| several-large-volumes | redesigned | 2 | 0.5526 | 444.3 | 259.01 | 24/24 | 24/24 |
| several-large-volumes | redesigned | 4 | 0.3722 | 418.3 | 259.01 | 24/24 | 24/24 |
| small-jpeg | fork | 1 | 0.0556 | 65.4 | 10.90 | 12/12 | 12/12 |
| small-jpeg | original | 1 | 0.1510 | 61.3 | 2.72 | 0/12 | 12/12 |
| small-jpeg | original | 2 | 0.1477 | 61.7 | 2.72 | 0/12 | 12/12 |
| small-jpeg | original | 4 | 0.1450 | 61.5 | 2.72 | 0/12 | 12/12 |
| small-jpeg | redesigned | 1 | 0.0356 | 59.6 | 10.90 | 12/12 | 12/12 |
| small-jpeg | redesigned | 2 | 0.0354 | 59.7 | 10.90 | 12/12 | 12/12 |
| small-jpeg | redesigned | 4 | 0.0359 | 59.7 | 10.90 | 12/12 | 12/12 |

Exploratory scaling only: later trials shared the host with private fixture work and direct-stream verification was added during exploration. See comparison.json for final-code sequential results.
