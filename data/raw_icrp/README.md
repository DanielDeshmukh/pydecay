# Raw ICRP-07 drop directory

Official ICRP-07 CD/supplement files (`ICRP-07.NDX`, `ICRP-07.RAD`,
`ICRP-07.BET`, ACK, NSF) land here when available. Large raw files are
gitignored; only `.gitkeep` and this README are tracked.

## Official source

- Preferred: official ICRP Publication 107 supplement / DECDATA zip.
- Direct zip URL currently returns **HTTP 403** without a session; use a
  browser or institutional access if needed.
- After download, record the real digest here:

```text
SUPPL_ZIP_SHA256=<fill-in-after-download>
```

## Extract instructions

1. Place the official zip (or extracted `ICRP-07.*` files) in this folder.
2. Rebuild the catalog and spectra:

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pydecay.data._fetch_icrp --ndx-path data/raw_icrp/ICRP-07.NDX
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pydecay.data._fetch_icrp --spectra --raddata-path path\to\RadData_1.0.2.tar.gz
```

Until the official zip is available, RAD/BET artifacts are bootstrapped
from the CRAN `RadData` package (SHA-pinned in `_fetch_icrp.py`).
