# Healthcare Data Governance and Cleaning

**Track:** Data Analytics — Healthcare/Pharmacy
**Deliverable type:** Privacy-aware data dictionary + reproducible validation/cleaning pipeline for a synthetic patient records sample.

## What's in this repo

| File | Purpose |
|---|---|
| `data/raw_healthcare_patients_sample.csv` | Original supplied sample (10 synthetic patient records), unmodified. |
| `data_dictionary.md` | Field-by-field classification (identifier / quasi-identifier / clinical), plus the reasoning for why this sample is treated as de-identified and its residual re-identification risk. |
| `clean_and_validate.py` | Reproducible Python script that (1) validates types, ranges, missing values, duplicate IDs, and formats, then (2) applies only structural cleaning rules — never inventing or imputing a clinical value. |
| `quality_exception_log.md` | Auto-generated output of the script: every rule that ran, what it found, and a pass/warn/fail summary. |
| `data/cleaned_healthcare_patients_sample.csv` | Cleaned output: trimmed whitespace, standardized categorical casing, enforced dtypes, `BloodPressure` split into `SystolicBP`/`DiastolicBP`. |

## How to reproduce

```bash
pip install pandas
python3 clean_and_validate.py
```

This regenerates `data/cleaned_healthcare_patients_sample.csv` and `quality_exception_log.md` from the raw file, so the pipeline is fully reproducible rather than a one-off manual edit.

## Summary of findings

The supplied sample was already well-formed: 10 rows, 10 columns, **zero missing values, zero duplicate `PatientID`s**, and all values fall within clinically plausible ranges. The pipeline still runs a full rule set (type, range, categorical-domain, format, and cross-field consistency checks) so the same script would catch and log any issues in a messier real-world extract — see `quality_exception_log.md` for the complete rule-by-rule result (20/20 checks passed on this sample).

## Governance notes

- No field was classified as a direct identifier (no name, DOB, address, SSN, or contact info in the source file).
- `PatientID` is a synthetic pseudonym with no crosswalk to a real identity supplied alongside it.
- The main residual risk, documented in `data_dictionary.md`, is that `Age` + `Gender` + `Diagnosis` together form a quasi-identifier set that could narrow down a specific row in a *larger* real dataset — worth flagging even though this sample is synthetic and low-risk.
