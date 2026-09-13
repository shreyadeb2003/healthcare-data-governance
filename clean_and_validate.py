"""
Healthcare Data Governance and Cleaning
----------------------------------------
Reproducible validation + cleaning pipeline for the synthetic patient
records sample.

Rules are applied in two passes:
  1. VALIDATE  - check types, ranges, missing values, duplicates, formats.
                 Every finding is logged; nothing is silently dropped.
  2. CLEAN     - apply only non-inventive, structural fixes:
                 whitespace trimming, categorical casing standardization,
                 correct dtypes, and splitting BloodPressure into
                 SystolicBP / DiastolicBP. No clinical value is guessed,
                 imputed, or estimated.

Run:
    python3 clean_and_validate.py

Outputs:
    data/cleaned_healthcare_patients_sample.csv
    quality_exception_log.md   (overwritten with the latest run's findings)
"""

import re
import sys
from pathlib import Path

import pandas as pd

RAW_PATH = Path("data/raw_healthcare_patients_sample.csv")
CLEAN_PATH = Path("data/cleaned_healthcare_patients_sample.csv")
LOG_PATH = Path("quality_exception_log.md")

# ---- Reference validation rules (documented assumptions, not invented data) ----
VALID_GENDERS = {"Male", "Female"}
VALID_READMITTED = {"Yes", "No"}
AGE_RANGE = (0, 120)
DOSAGE_RANGE = (0, 2000)          # generous upper bound in mg; flags only implausible entries
DURATION_RANGE = (1, 3650)        # 1 day to 10 years
CHOLESTEROL_RANGE = (100, 400)    # mg/dL, plausible clinical bound
SYSTOLIC_RANGE = (70, 250)
DIASTOLIC_RANGE = (40, 150)
PATIENT_ID_PATTERN = re.compile(r"^PAT-\d+$")
BP_PATTERN = re.compile(r"^\s*(\d{2,3})\s*/\s*(\d{2,3})\s*$")

findings = []  # list of dicts: {rule, field, row/PatientID, detail, severity}


def log(rule, field, patient_id, detail, severity="INFO"):
    findings.append(
        {"rule": rule, "field": field, "patient_id": patient_id, "detail": detail, "severity": severity}
    )


def validate(df: pd.DataFrame) -> pd.DataFrame:
    # 1. Missing values (blank / NaN) in any column
    for col in df.columns:
        n_missing = df[col].isna().sum() + (df[col].astype(str).str.strip() == "").sum()
        if n_missing:
            log("missing_values", col, "multiple", f"{n_missing} missing/blank value(s)", "WARN")
        else:
            log("missing_values", col, "-", "0 missing values", "PASS")

    # 2. Duplicate PatientIDs
    dup_mask = df["PatientID"].duplicated(keep=False)
    if dup_mask.any():
        dup_ids = df.loc[dup_mask, "PatientID"].unique().tolist()
        log("duplicate_patient_id", "PatientID", ",".join(dup_ids), "Duplicate PatientID values found", "FAIL")
    else:
        log("duplicate_patient_id", "PatientID", "-", "No duplicate PatientIDs", "PASS")

    # 3. PatientID format
    bad_ids = df.loc[~df["PatientID"].astype(str).str.match(PATIENT_ID_PATTERN), "PatientID"].tolist()
    if bad_ids:
        log("id_format", "PatientID", ",".join(bad_ids), "Does not match PAT-### pattern", "WARN")
    else:
        log("id_format", "PatientID", "-", "All IDs match PAT-### pattern", "PASS")

    # 4. Type / range checks
    def check_range(col, lo, hi):
        bad = df.loc[(df[col] < lo) | (df[col] > hi), ["PatientID", col]]
        if len(bad):
            for _, r in bad.iterrows():
                log("range_check", col, r["PatientID"], f"{col}={r[col]} outside [{lo}, {hi}]", "WARN")
        else:
            log("range_check", col, "-", f"All values within [{lo}, {hi}]", "PASS")

    check_range("Age", *AGE_RANGE)
    check_range("DosageMg", *DOSAGE_RANGE)
    check_range("TreatmentDurationDays", *DURATION_RANGE)
    check_range("CholesterolLevel", *CHOLESTEROL_RANGE)

    # 5. Categorical domain checks
    bad_gender = df.loc[~df["Gender"].isin(VALID_GENDERS), ["PatientID", "Gender"]]
    if len(bad_gender):
        for _, r in bad_gender.iterrows():
            log("categorical_domain", "Gender", r["PatientID"], f"Unexpected value '{r['Gender']}'", "WARN")
    else:
        log("categorical_domain", "Gender", "-", "All values in {Male, Female}", "PASS")

    bad_readmit = df.loc[~df["Readmitted"].isin(VALID_READMITTED), ["PatientID", "Readmitted"]]
    if len(bad_readmit):
        for _, r in bad_readmit.iterrows():
            log("categorical_domain", "Readmitted", r["PatientID"], f"Unexpected value '{r['Readmitted']}'", "WARN")
    else:
        log("categorical_domain", "Readmitted", "-", "All values in {Yes, No}", "PASS")

    # 6. BloodPressure format + internal consistency (systolic > diastolic)
    bp_ok = df["BloodPressure"].astype(str).str.match(BP_PATTERN)
    if (~bp_ok).any():
        bad = df.loc[~bp_ok, ["PatientID", "BloodPressure"]]
        for _, r in bad.iterrows():
            log("bp_format", "BloodPressure", r["PatientID"], f"'{r['BloodPressure']}' not systolic/diastolic", "FAIL")
    else:
        log("bp_format", "BloodPressure", "-", "All values match systolic/diastolic format", "PASS")

    sys_vals, dia_vals = [], []
    for _, r in df.iterrows():
        m = BP_PATTERN.match(str(r["BloodPressure"]))
        s, d = (int(m.group(1)), int(m.group(2))) if m else (None, None)
        sys_vals.append(s)
        dia_vals.append(d)
        if s is not None and d is not None:
            if s <= d:
                log("bp_consistency", "BloodPressure", r["PatientID"], f"systolic {s} <= diastolic {d}", "WARN")
            if not (SYSTOLIC_RANGE[0] <= s <= SYSTOLIC_RANGE[1]):
                log("bp_consistency", "BloodPressure", r["PatientID"], f"systolic {s} outside {SYSTOLIC_RANGE}", "WARN")
            if not (DIASTOLIC_RANGE[0] <= d <= DIASTOLIC_RANGE[1]):
                log("bp_consistency", "BloodPressure", r["PatientID"], f"diastolic {d} outside {DIASTOLIC_RANGE}", "WARN")
    if not any(f["rule"] == "bp_consistency" for f in findings):
        log("bp_consistency", "BloodPressure", "-", "All systolic/diastolic pairs internally consistent", "PASS")

    df = df.copy()
    df["SystolicBP"] = sys_vals
    df["DiastolicBP"] = dia_vals
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Trim whitespace on all string/object columns
    obj_cols = df.select_dtypes(include="object").columns
    for col in obj_cols:
        df[col] = df[col].astype(str).str.strip()

    # Standardize categorical casing (structural, not inventive)
    df["Gender"] = df["Gender"].str.title()
    df["Readmitted"] = df["Readmitted"].str.title()
    df["Diagnosis"] = df["Diagnosis"].str.title()
    df["PrimaryMedication"] = df["PrimaryMedication"].str.title()

    # Enforce dtypes
    df["Age"] = df["Age"].astype(int)
    df["TreatmentDurationDays"] = df["TreatmentDurationDays"].astype(int)
    df["CholesterolLevel"] = df["CholesterolLevel"].astype(int)
    df["DosageMg"] = df["DosageMg"].astype(float)
    df["SystolicBP"] = df["SystolicBP"].astype("Int64")
    df["DiastolicBP"] = df["DiastolicBP"].astype("Int64")

    # Drop the composite BloodPressure text column now that it is split
    # into SystolicBP / DiastolicBP; no information is lost.
    df = df.drop(columns=["BloodPressure"])

    # De-duplicate on PatientID, keeping the first occurrence, if any exist
    before = len(df)
    df = df.drop_duplicates(subset="PatientID", keep="first")
    after = len(df)
    if before != after:
        log("duplicate_removal", "PatientID", "-", f"Removed {before - after} duplicate row(s)", "WARN")

    return df


def write_log():
    lines = [
        "# Quality Exception Log",
        "",
        f"Generated by `clean_and_validate.py` against `{RAW_PATH}`.",
        "",
        "| Rule | Field | PatientID | Detail | Severity |",
        "|---|---|---|---|---|",
    ]
    for f in findings:
        lines.append(f"| {f['rule']} | {f['field']} | {f['patient_id']} | {f['detail']} | {f['severity']} |")

    n_fail = sum(1 for f in findings if f["severity"] == "FAIL")
    n_warn = sum(1 for f in findings if f["severity"] == "WARN")
    n_pass = sum(1 for f in findings if f["severity"] == "PASS")

    lines += [
        "",
        f"**Summary:** {n_pass} rule(s) passed cleanly, {n_warn} warning(s), {n_fail} failure(s) "
        f"across {len(pd.read_csv(RAW_PATH))} source rows.",
        "",
        "No missing values were imputed and no clinical values were invented or estimated. "
        "Every action taken above is either (a) a validation check that only records a finding, "
        "or (b) a structural cleaning step listed in `data_dictionary.md` (whitespace trim, "
        "categorical casing, dtype enforcement, splitting BloodPressure into SystolicBP/DiastolicBP).",
    ]
    LOG_PATH.write_text("\n".join(lines))


def main():
    if not RAW_PATH.exists():
        sys.exit(f"Raw file not found at {RAW_PATH}")
    raw = pd.read_csv(RAW_PATH, dtype={"PatientID": str})
    validated = validate(raw)
    cleaned = clean(validated)
    CLEAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(CLEAN_PATH, index=False)
    write_log()
    print(f"Validated {len(raw)} rows.")
    print(f"Cleaned file written to {CLEAN_PATH}")
    print(f"Exception log written to {LOG_PATH}")


if __name__ == "__main__":
    main()
