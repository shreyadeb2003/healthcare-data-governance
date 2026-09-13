# Data Dictionary — Synthetic Patient Records

**Source file:** `data/raw_healthcare_patients_sample.csv`
**Records:** 10 rows, 10 columns
**Purpose:** Training dataset for data quality / governance practice (synthetic, not real patients)

## 1. Field classification

| Field | Data type | Category | Notes |
|---|---|---|---|
| `PatientID` | string | **Pseudonymous identifier** | Sequential synthetic code (`PAT-###`). Not a real Medical Record Number, name, or government ID. Used only to uniquely key a row within this file. |
| `Age` | integer | **Quasi-identifier** (demographic) | Combined with other quasi-identifiers, could narrow down an individual in a *large* real-world dataset. Low risk here given synthetic origin. |
| `Gender` | categorical string (`Male`/`Female`) | **Quasi-identifier** (demographic) | Two-category variable in this sample. |
| `Diagnosis` | categorical string | **Sensitive clinical attribute** | Protected health information category (condition). |
| `PrimaryMedication` | categorical string | **Sensitive clinical attribute** | Treatment detail; can imply diagnosis. |
| `DosageMg` | float | **Clinical measurement** | Medication dose in mg. |
| `TreatmentDurationDays` | integer | **Clinical measurement** | Length of treatment course, in days. |
| `Readmitted` | categorical string (`Yes`/`No`) | **Clinical outcome flag** | Binary outcome variable. |
| `BloodPressure` | string, composite (`systolic/diastolic`) | **Clinical measurement** | Stored as one text field in the raw file; split into two numeric columns during cleaning (see below). |
| `CholesterolLevel` | integer | **Clinical measurement** | mg/dL, implied unit (not stated in source). |

## 2. Why this sample is treated as de-identified

- **No direct identifiers are present**: no legal name, date of birth, Social Security/government ID, street address, phone number, email, or photograph.
- **No exact dates** are present (only a duration in days), and **no geographic detail** below "country" is present — both are direct-identifier categories under common de-identification frameworks (e.g., HIPAA Safe Harbor).
- `PatientID` is a **synthetic, sequential code** generated for this exercise. There is no key or crosswalk file provided that maps it back to a real person.
- The dataset is explicitly supplied as **"synthetic training data"** for a governance exercise, not a real clinical extract.

### Residual re-identification risk (documented, not eliminated)
- With only 10 rows, the combination of `Age` + `Gender` + `Diagnosis` is technically a quasi-identifier set that could single out a row *within this file*. This is a low-risk academic dataset, but the same combination in a **real, larger EHR export** would need additional controls (e.g., k-anonymity/generalization of age into bands, suppression of rare diagnosis/age/gender combinations) before being called "de-identified" in a production setting.
- No cell values were altered to reduce this risk in this exercise, since the task is a cleaning/validation task, not a statistical disclosure control task — this is called out explicitly as a limitation rather than silently ignored.

## 3. Derived fields added during cleaning

| Field | Derived from | Logic |
|---|---|---|
| `SystolicBP` | `BloodPressure` | Integer before the `/` |
| `DiastolicBP` | `BloodPressure` | Integer after the `/` |

No clinical value was invented, estimated, or imputed anywhere in this pipeline — see `quality_exception_log.md` for the full rule-by-rule result.
