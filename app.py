import os
from datetime import datetime
import streamlit as st

st.set_page_config(page_title="CryptoShield", page_icon="🛡️", layout="wide")

from blockchain import trace_wallet
from demo_data import get_demo_transactions, get_demo_wallet
from transaction_dna import analyze_transaction_dna
from abnormal_detection import detect_abnormal_transactions
from vasp_detection import detect_vasp
from exchange_intelligence import check_exchange_associations
from fund_flow_graph import render_fund_flow_graph
from report_generator import generate_investigation_pdf, generate_rpa_request_pdf
from kyc_rpa import prepare_request, mark_human_review, authorize_submission, simulate_vasp_response

CHAINS={"Ethereum":"ethereum","Base":"base","Polygon":"polygon","Arbitrum":"arbitrum","Optimism":"optimism","BNB Chain":"bsc"}

def risk_score(dna, alerts, vasp, exchange):
    score=0; reasons=[]
    dna=dna or {}
    if dna.get("rapid_movements"): score+=20; reasons.append("Rapid fund movement")
    if dna.get("fan_out",0)>=5: score+=15; reasons.append("High fan-out behaviour")
    if dna.get("fan_in",0)>=5: score+=10; reasons.append("High fan-in behaviour")
    if dna.get("transaction_count",0)>=100: score+=10; reasons.append("High transaction activity")
    high=sum(1 for a in (alerts or []) if a.get("severity")=="HIGH")
    med=sum(1 for a in (alerts or []) if a.get("severity")=="MEDIUM")
    score += min(high*15,30)+min(med*5,15)
    if high: reasons.append(f"{high} high-severity transaction alert(s)")
    if med: reasons.append(f"{med} medium-severity transaction alert(s)")
    if vasp: score+=10; reasons.append("Known VASP endpoint identified as an investigative lead")
    if exchange: score+=10; reasons.append("Known exchange/VASP endpoint identified")
    score=min(score,100)
    return score, ("HIGH" if score>=70 else "MEDIUM" if score>=40 else "LOW"), reasons

def run_analysis(wallet, chain_name, max_hop, demo):
    if demo:
        txs=get_demo_transactions()
        hops={get_demo_wallet():0}
        # Assign demo hops from transaction chain.
        for tx in txs:
            tx.setdefault("hop", 1 if tx["from"]==get_demo_wallet() else 2)
        chain="Ethereum"
    else:
        result=trace_wallet(wallet, chain=CHAINS[chain_name], max_hop=max_hop)
        txs=result.get("transactions",[]) if isinstance(result,dict) else []
        hops=result.get("wallet_hops",{}) if isinstance(result,dict) else {}
        chain=chain_name
    dna=analyze_transaction_dna(txs,wallet) if txs else {}
    try: alerts=detect_abnormal_transactions(txs,wallet)
    except TypeError: alerts=detect_abnormal_transactions(txs)
    vasp=detect_vasp(txs,wallet_hops=hops) or []
    exchange=check_exchange_associations(txs,wallet_hops=hops) or []
    score,level,reasons=risk_score(dna,alerts,vasp,exchange)
    return {"case_id":"CS-"+datetime.now().strftime("%Y%m%d%H%M%S"),"wallet":wallet,"blockchain":chain,"max_hop":max_hop,"transactions":txs,"wallet_hops":hops,"dna":dna,"alerts":alerts,"vasp":vasp,"exchange":exchange,"risk_score":score,"risk_level":level,"risk_reasons":reasons}

st.title("🛡️ CryptoShield")
st.caption("Real-Time Crypto Fraud Attribution & Investigator Workflow")

with st.sidebar:
    st.header("🔎 Investigation")
    mode=st.radio("Data mode",["Demo / SIH Mode","Live Blockchain Mode"])
    wallet=st.text_input("Reported suspect wallet", value=get_demo_wallet() if mode.startswith("Demo") else "")
    chain_name=st.selectbox("Blockchain",list(CHAINS.keys()))
    max_hop=st.slider("Maximum trace depth",1,6,3)
    analyze=st.button("🚀 Analyze Wallet",type="primary",use_container_width=True)
    st.divider()
    st.caption("Wallet analysis produces investigative leads. It does not directly identify a person from a blockchain address.")

if analyze:
    with st.spinner("Tracing wallet and analyzing transaction behaviour..."):
        try:
            st.session_state["case"]=run_analysis(wallet.strip(),chain_name,max_hop,mode.startswith("Demo"))
            st.session_state.pop("rpa",None); st.session_state.pop("kyc",None)
        except Exception as e:
            st.error("Analysis failed.")
            st.exception(e)
            st.stop()

if "case" not in st.session_state:
    st.info("👈 Start with Demo / SIH Mode to test the complete workflow without external API keys.")
    st.markdown("""
### CryptoShield investigation flow

**Victim-reported wallet** → **Blockchain tracing** → **Fund-flow / intermediary analysis** → **Known VASP identification** → **KYC request preparation** → **Human investigator review** → **Authorized submission** → **VASP KYC response** → **Investigation report (PDF)**

> KYC identity data is not fetched directly from the blockchain. The prototype models the lawful, authorized request workflow and uses synthetic demo KYC data.
""")
    st.stop()

case=st.session_state["case"]
txs=case["transactions"]
vasps=case["vasp"]
exchanges=case["exchange"]

c1,c2,c3,c4,c5=st.columns(5)
c1.metric("Transactions",len(txs)); c2.metric("Connected wallets",len(case["wallet_hops"])); c3.metric("Trace depth",case["max_hop"]); c4.metric("Risk",f'{case["risk_score"]}/100'); c5.metric("Level",case["risk_level"])
st.markdown(f"### Case `{case['case_id']}`")
st.write(f"**Reported wallet:** `{case['wallet']}`  •  **Blockchain:** {case['blockchain']}")

tabs=st.tabs(["📊 Overview","🕸️ Fund Flow","🚨 Suspicious","🧬 Transaction DNA","🏦 Known VASP","🪪 KYC / Identity","🤖 RPA Workflow","📄 PDF Report"])

with tabs[0]:
    if case["risk_level"]=="HIGH": st.error(f'⚠️ HIGH RISK — {case["risk_score"]}/100')
    elif case["risk_level"]=="MEDIUM": st.warning(f'⚠️ MEDIUM RISK — {case["risk_score"]}/100')
    else: st.success(f'LOW RISK — {case["risk_score"]}/100')
    st.subheader("Why this score?")
    for r in case["risk_reasons"]: st.write("• "+r)
    st.subheader("Investigation principle")
    st.info("CryptoShield first identifies a known VASP/exchange endpoint. It does not claim to know the person's identity from the wallet. Identity information is requested from the VASP through an authorized KYC process.")

with tabs[1]:
    render_fund_flow_graph(txs,case["wallet"],case["max_hop"])

with tabs[2]:
    alerts=case["alerts"]
    if alerts:
        for i,a in enumerate(alerts[:50],1):
            with st.expander(f'{i}. {a.get("severity","MEDIUM")} — {a.get("hash","Unknown")}'):
                st.write(f'**From:** {a.get("from","N/A")}'); st.write(f'**To:** {a.get("to","N/A")}'); st.write(f'**Value:** {a.get("value",0)}'); st.write(f'**Score:** {a.get("score",0)}')
                for r in a.get("reasons",[]): st.write("• "+str(r))
    else: st.success("No major suspicious transaction alerts detected.")

with tabs[3]:
    st.subheader("Transaction DNA")
    st.json(case["dna"])
    st.dataframe(txs,use_container_width=True,hide_index=True)

with tabs[4]:
    st.subheader("Known VASP / Exchange Endpoint")
    if vasps:
        for v in vasps:
            st.markdown(f"### 🏦 {v.get('name','Unknown')}")
            cols=st.columns(4); cols[0].metric("Type",v.get("type","")); cols[1].metric("Hop",v.get("hop","N/A")); cols[2].metric("Country",v.get("country","")); cols[3].metric("Confidence",v.get("confidence","Analytical lead"))
            st.code(v.get("address",""))
            st.write("**Evidence:**",v.get("evidence",""))
            st.warning("This is a labelled endpoint lead. It does not prove ownership, control, identity, fraud, or criminal activity.")
            st.success("Next step: prepare an authorized KYC/account-information request to this VASP.")
    else:
        st.warning("No known VASP endpoint was found in this trace. Expand the trace depth or use a richer address-label dataset.")

with tabs[5]:
    st.subheader("🪪 KYC / Identity Attribution")
    st.write("**Important design:** the blockchain does not directly reveal the real-world identity. CryptoShield uses the known VASP endpoint as the bridge to an authorized KYC request.")
    if not vasps:
        st.warning("Identify a known VASP first. KYC request preparation is disabled until an endpoint is available.")
    else:
        v=vasps[0]
        st.write(f"Target VASP: **{v.get('name')}**"); st.write(f"Endpoint: `{v.get('address')}`")
        if st.button("📝 Prepare KYC Request",key="prepare_kyc"):
            st.session_state["rpa"]=prepare_request(case)
            st.session_state.pop("kyc",None)
            st.success("KYC request draft prepared. Human review is required before authorization.")
        req=st.session_state.get("rpa")
        if req:
            st.markdown("#### Requested information")
            for x in req["requested_fields"]: st.write("• "+x)
            st.caption("No identity data has been fetched yet.")
            if req.get("status")=="DRAFT" and st.checkbox("I am the investigator reviewing this request",key="review_kyc"):
                if st.button("✅ Complete Human Review",key="complete_review"):
                    st.session_state["rpa"]=mark_human_review(req); st.rerun()
            req=st.session_state["rpa"]
            if req.get("status")=="READY_FOR_AUTHORIZATION":
                st.success("Human review completed. Ready for authorized submission.")
                if st.button("🔐 Authorize Submission",key="authorize"):
                    try: st.session_state["rpa"]=authorize_submission(req); st.rerun()
                    except Exception as e: st.error(str(e))
            req=st.session_state["rpa"]
            if req.get("status")=="AUTHORIZED_FOR_SUBMISSION":
                st.success("Authorized submission stage reached.")
                if st.button("🤖 Simulate VASP KYC Response (Demo)",key="simulate_response"):
                    st.session_state["kyc"]=simulate_vasp_response(req); st.rerun()
        kyc=st.session_state.get("kyc")
        if kyc and kyc.get("status")=="RESPONSE_RECEIVED":
            st.markdown("#### VASP KYC response — synthetic demo")
            st.warning("These identity fields are synthetic hackathon data. In production, this step would use an authorized VASP response.")
            st.json(kyc)

with tabs[6]:
    st.subheader("🤖 RPA-Ready Investigator Workflow")
    steps=[("1","Case evidence",True),("2","Prepare official request",bool(st.session_state.get("rpa"))), ("3","Fill permitted case/request fields",bool(st.session_state.get("rpa"))), ("4","Attach transaction evidence",bool(st.session_state.get("rpa"))), ("5","Human investigator reviews",st.session_state.get("rpa",{}).get("human_review",False)), ("6","Authorized submission",st.session_state.get("rpa",{}).get("authorized_submission",False))]
    for n,label,done in steps: st.write(("✅" if done else "⬜")+f" **{label}**")
    req=st.session_state.get("rpa")
    if req:
        if st.button("📄 Download Official Request Draft (PDF)"):
            path=f"/tmp/{req['request_id']}.pdf"; generate_rpa_request_pdf(path,req); st.session_state["rpa_pdf"]=path
        if st.session_state.get("rpa_pdf") and os.path.exists(st.session_state["rpa_pdf"]):
            with open(st.session_state["rpa_pdf"],"rb") as f: st.download_button("⬇️ Download Request PDF",f,file_name=f"{req['request_id']}.pdf",mime="application/pdf")
    st.info("For a real deployment, the RPA bot should operate only against an authorized VASP portal/API, with human approval and audit logging. The prototype does not bypass authentication or submit unauthorized requests.")

with tabs[7]:
    st.subheader("📄 Investigation Report")
    st.write("The report is generated as PDF; JSON is not used as the investigator-facing report.")
    if st.button("📑 Generate Investigation PDF",type="primary"):
        path=f"/tmp/{case['case_id']}.pdf"
        generate_investigation_pdf(path,case,st.session_state.get("kyc"),st.session_state.get("rpa"))
        st.session_state["report_pdf"]=path
    if st.session_state.get("report_pdf") and os.path.exists(st.session_state["report_pdf"]):
        with open(st.session_state["report_pdf"],"rb") as f: st.download_button("⬇️ Download Investigation Report PDF",f,file_name=f"{case['case_id']}.pdf",mime="application/pdf",use_container_width=True)

st.divider()
st.caption("CryptoShield • SIH prototype • Analytical intelligence only. KYC/identity information requires applicable authority and process.")
