from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak


def _safe(v):
    return "" if v is None else str(v)


def _short(v, n=22):
    s=_safe(v)
    return s if len(s)<=n else s[:n]+"..."


def _header_footer(canvas, doc):
    canvas.saveState()
    w,h=A4
    canvas.setFont("Helvetica-Bold",8)
    canvas.drawString(15*mm,h-10*mm,"CRYPTOSHIELD")
    canvas.setFont("Helvetica",7)
    canvas.drawRightString(w-15*mm,h-10*mm,"Blockchain Fraud Intelligence")
    canvas.setStrokeColor(colors.lightgrey)
    canvas.line(15*mm,12*mm,w-15*mm,12*mm)
    canvas.drawString(15*mm,7*mm,"CryptoShield — Investigation Intelligence")
    canvas.drawRightString(w-15*mm,7*mm,f"Page {doc.page}")
    canvas.restoreState()


def generate_investigation_pdf(path, case, kyc_response=None, rpa_request=None):
    doc=SimpleDocTemplate(path,pagesize=A4,rightMargin=15*mm,leftMargin=15*mm,topMargin=18*mm,bottomMargin=18*mm,title="CryptoShield Investigation Report",author="CryptoShield")
    styles=getSampleStyleSheet()
    title=ParagraphStyle("t",parent=styles["Title"],alignment=TA_CENTER,fontSize=22,leading=26,spaceAfter=5)
    sub=ParagraphStyle("s",parent=styles["Normal"],alignment=TA_CENTER,fontSize=9,textColor=colors.grey,spaceAfter=14)
    sec=ParagraphStyle("sec",parent=styles["Heading2"],fontSize=13,leading=16,spaceBefore=10,spaceAfter=6)
    body=ParagraphStyle("body",parent=styles["BodyText"],fontSize=8.5,leading=12)
    small=ParagraphStyle("small",parent=body,fontSize=7,textColor=colors.grey)
    story=[]
    story += [Paragraph("CRYPTO SHIELD",title),Paragraph("Blockchain Fraud Intelligence & Investigation System",sub)]
    story.append(Paragraph("INVESTIGATION REPORT",sec))
    summary=[
        ["Case ID",_safe(case.get("case_id"))],
        ["Reported wallet",_safe(case.get("wallet"))],
        ["Blockchain",_safe(case.get("blockchain"))],
        ["Transactions analyzed",str(len(case.get("transactions",[])))],
        ["Trace depth",str(case.get("max_hop",""))],
        ["Analytical risk",f"{case.get('risk_score',0)}/100 — {case.get('risk_level','UNKNOWN')}"],
        ["Generated",datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
    ]
    t=Table(summary,colWidths=[52*mm,123*mm])
    t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.4,colors.grey),("BACKGROUND",(0,0),(0,-1),colors.HexColor("#EEEEEE")),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    story.append(t)
    story.append(Paragraph("1. ANALYTICAL FINDINGS",sec))
    reasons=case.get("risk_reasons",[])
    if reasons:
        for r in reasons: story.append(Paragraph("• "+_safe(r),body))
    else: story.append(Paragraph("No major risk indicators recorded.",body))
    story.append(Paragraph("2. KNOWN VASP / EXCHANGE ATTRIBUTION",sec))
    vasp_data=case.get("vasp") or []
    if isinstance(vasp_data, dict): vasp_data=[vasp_data]
    v=vasp_data[0] if vasp_data else {}
    if v:
        rows=[["Field","Value"],["Name",_safe(v.get("name"))],["Type",_safe(v.get("type"))],["Address",_safe(v.get("address"))],["Hop",_safe(v.get("hop"))],["Source",_safe(v.get("source"))],["Confidence",_safe(v.get("confidence"))]]
        tv=Table(rows,colWidths=[45*mm,130*mm])
        tv.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.4,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#EDEDED")),("VALIGN",(0,0),(-1,-1),"TOP"),("FONTSIZE",(0,0),(-1,-1),7)]))
        story.append(tv)
        story.append(Paragraph("A labelled blockchain endpoint is an investigative lead; it does not by itself prove ownership, control, identity, fraud, or criminal activity.",small))
    else:
        story.append(Paragraph("No known VASP endpoint was identified in the analyzed flow.",body))
    story.append(Paragraph("3. KYC / IDENTITY ATTRIBUTION WORKFLOW",sec))
    if kyc_response and kyc_response.get("status")=="RESPONSE_RECEIVED":
        story.append(Paragraph("Identity information shown below is from the synthetic hackathon KYC response dataset. A production deployment must obtain such information only through an authorized process.",small))
        rows=[["Field","Response"],["VASP",_safe(kyc_response.get("vasp_name"))],["Customer reference",_safe(kyc_response.get("customer_reference"))],["Account holder",_safe(kyc_response.get("account_holder"))],["KYC status",_safe(kyc_response.get("kyc_status"))],["Country",_safe(kyc_response.get("country"))],["Phone",_safe(kyc_response.get("phone"))],["Email",_safe(kyc_response.get("email"))],["Account created",_safe(kyc_response.get("account_created"))],["Linked wallets",_safe(kyc_response.get("linked_wallets"))]]
        tk=Table(rows,colWidths=[55*mm,120*mm]); tk.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.4,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#EDEDED")),("FONTSIZE",(0,0),(-1,-1),7),("VALIGN",(0,0),(-1,-1),"TOP")]))
        story.append(tk)
    else:
        story.append(Paragraph("No KYC identity data was automatically exposed. The system prepares an authorized request to the identified VASP and keeps human review before submission.",body))
    story.append(Paragraph("4. RPA-READY REQUEST WORKFLOW",sec))
    workflow=["Case evidence collected","Official request prepared","Permitted request fields filled","Transaction evidence attached","Human investigator reviews","Authorized submission"]
    for i,x in enumerate(workflow,1): story.append(Paragraph(f"{i}. {x}",body))
    if rpa_request:
        story.append(Paragraph(f"Request ID: {_safe(rpa_request.get('request_id'))} — Status: {_safe(rpa_request.get('status'))}",body))
    story.append(Paragraph("5. TRANSACTION EVIDENCE",sec))
    txs=case.get("transactions",[])
    rows=[["Hash","From","To","Value","Asset","Hop"]]
    for tx in txs[:40]: rows.append([_short(tx.get("hash",tx.get("transaction_hash",""))),_short(tx.get("from")),_short(tx.get("to")),_safe(tx.get("value",0)),_safe(tx.get("asset", "")),_safe(tx.get("hop", ""))])
    te=Table(rows,colWidths=[32*mm,37*mm,37*mm,18*mm,22*mm,12*mm],repeatRows=1)
    te.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.25,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#EDEDED")),("FONTSIZE",(0,0),(-1,-1),6),("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(te)
    story.append(Spacer(1,6))
    story.append(Paragraph("Important: This report is an analytical prototype output for investigation support. Identity attribution and enforcement action require appropriate authority, verification, and applicable legal process.",small))
    doc.build(story,onFirstPage=_header_footer,onLaterPages=_header_footer)


def generate_rpa_request_pdf(path, request):
    doc=SimpleDocTemplate(path,pagesize=A4,rightMargin=15*mm,leftMargin=15*mm,topMargin=18*mm,bottomMargin=18*mm,title="CryptoShield Authorized Information Request Draft")
    styles=getSampleStyleSheet(); title=ParagraphStyle("rt",parent=styles["Title"],alignment=TA_CENTER,fontSize=18); sec=ParagraphStyle("rs",parent=styles["Heading2"],fontSize=12); body=ParagraphStyle("rb",parent=styles["BodyText"],fontSize=8.5,leading=12)
    story=[Paragraph("CRYPTO SHIELD",title),Spacer(1,5*mm),Paragraph("AUTHORIZED INFORMATION REQUEST — DRAFT",sec)]
    data=[["Request ID",_safe(request.get("request_id"))],["Case ID",_safe(request.get("case_id"))],["VASP",_safe(request.get("vasp_name"))],["VASP address",_safe(request.get("vasp_address"))],["Status",_safe(request.get("status"))],["Purpose",_safe(request.get("purpose"))],["Evidence hash",_safe(request.get("evidence",{}).get("evidence_hash"))]]
    t=Table(data,colWidths=[45*mm,130*mm]); t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.4,colors.grey),("BACKGROUND",(0,0),(0,-1),colors.HexColor("#EEEEEE")),("FONTSIZE",(0,0),(-1,-1),8),("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(t); story.append(Paragraph("Requested fields",sec))
    for x in request.get("requested_fields",[]): story.append(Paragraph("• "+_safe(x),body))
    story.append(Spacer(1,5*mm)); story.append(Paragraph("Workflow control: This document is a prepared request packet. It is not an automatic demand for information. Human investigator review and authorized submission are required.",body))
    doc.build(story,onFirstPage=_header_footer,onLaterPages=_header_footer)
