# CryptoShield — Enhanced SIH Prototype

## New investigation design

**Victim-reported wallet**
→ blockchain tracing
→ intermediary/fund-flow analysis
→ **known VASP/exchange endpoint**
→ **authorized KYC request**
→ human investigator review
→ authorized submission
→ VASP KYC response
→ investigation report PDF

The prototype deliberately does **not** claim that a blockchain address directly reveals a person's identity.

## KYC + RPA prototype

The `kyc_rpa.py` module models the workflow:

1. Case evidence
2. Prepare official request
3. Fill permitted request fields
4. Attach transaction evidence
5. Human investigator reviews
6. Authorized submission
7. Synthetic VASP KYC response (demo only)

The RPA portion is a safe prototype workflow. It does not bypass login, CAPTCHA, authorization, or submit an actual legal request.

## PDF reports

The investigator-facing report is now a **PDF**, not JSON. It can contain:
- case summary
- risk findings
- known VASP attribution
- KYC workflow state
- synthetic KYC response (only after the demo authorization flow)
- transaction evidence
- RPA request status

An additional PDF can be generated for the official-request draft.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Use **Demo / SIH Mode** first. It runs without blockchain API keys.

## Production boundary

A production implementation should obtain KYC/account information only through an authorized VASP interface or lawful request process. VASP labels are investigative leads and require verification.
