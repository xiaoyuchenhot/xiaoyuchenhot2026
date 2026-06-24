"""
Procurement Purchase Request AI Agent
Run: streamlit run app.py
"""

import streamlit as st
import json
import re
from datetime import datetime

# ---------------------------------------------------------------------------
# Procurement policy — realistic enterprise rules an FDE would configure
# ---------------------------------------------------------------------------

PROCUREMENT_POLICY = {
    "company": "Acme Global Corp",
    "spend_thresholds": {
        "auto_approve": 1000,
        "manager_approval": 10000,
        "director_approval": 50000,
        "vp_finance_approval": 200000,
        "cfo_approval": 500000,
        "board_notification": 1000000,
    },
    "preferred_vendors": {
        "IT Hardware": ["Dell", "Lenovo", "Apple", "HP"],
        "Cloud Services": ["AWS", "Google Cloud", "Microsoft Azure"],
        "Office Supplies": ["Staples", "Office Depot"],
        "Professional Services": ["Deloitte", "Accenture", "McKinsey", "KPMG"],
        "Software": ["Salesforce", "Microsoft", "Adobe", "Atlassian", "SAP"],
        "Travel": ["Amex GBT", "Corporate Travel Management"],
        "Facilities": ["CBRE", "JLL", "Cushman & Wakefield"],
    },
    "category_rules": {
        "IT Hardware": {
            "requires_it_review": True,
            "asset_tagging_required": True,
        },
        "Software": {
            "requires_security_review": True,
            "requires_it_review": True,
        },
        "Cloud Services": {
            "requires_security_review": True,
            "requires_it_review": True,
            "data_classification_required": True,
        },
        "Professional Services": {
            "requires_sow": True,
            "legal_review_above": 25000,
        },
        "Marketing": {
            "requires_brand_review": True,
        },
        "Travel": {
            "requires_pre_approval": True,
            "per_trip_cap": 5000,
        },
    },
    "compliance": {
        "sole_source_justification_above": 25000,
        "competitive_bid_required_above": 100000,
        "sox_audit_trail": True,
        "board_notification_above": 1000000,
    },
}

# ---------------------------------------------------------------------------
# System prompt — the core of the agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an enterprise procurement AI agent for {company}. You analyze purchase requests and return structured procurement guidance.

ACTIVE PROCUREMENT POLICY:
{policy}

When a user submits a purchase request, you MUST:

1. PARSE the request — extract item/service, vendor (if mentioned), estimated cost, requesting department, and urgency.

2. CLASSIFY the spend category — choose from: IT Hardware, Software, Cloud Services, Professional Services, Office Supplies, Marketing, Travel, Facilities, Other.

3. CHECK POLICY COMPLIANCE:
   - Match cost to the correct approval threshold
   - Check if vendor is on the preferred list for that category
   - Identify category-specific requirements (security review, legal review, SOW, IT review, etc.)
   - Flag compliance requirements (sole source justification, competitive bid, board notification)

4. ASSESS RISKS:
   - Non-preferred vendor usage
   - Missing required information
   - Policy violations
   - Budget or compliance concerns

5. DETERMINE APPROVAL CHAIN — the exact sequence of approvals needed, from first to last.

Respond ONLY with valid JSON in this exact format (no markdown, no explanation outside the JSON):
{{
  "parsed_request": {{
    "item": "description of what is being purchased",
    "vendor": "vendor name or null if not specified",
    "estimated_cost": 0,
    "department": "requesting department or 'Not specified'",
    "urgency": "low|medium|high"
  }},
  "spend_category": "one of the categories listed above",
  "approval_level": "human-readable approval level name",
  "approval_chain": ["Approver 1", "Approver 2"],
  "policy_checks": [
    {{"rule": "rule name", "status": "pass|fail|warning", "detail": "explanation"}}
  ],
  "risks": [
    {{"severity": "low|medium|high", "description": "risk description"}}
  ],
  "additional_requirements": ["requirement 1", "requirement 2"],
  "recommendation": "approve|approve_with_conditions|escalate|reject",
  "reasoning": "1-2 sentence summary of the overall assessment"
}}"""

# ---------------------------------------------------------------------------
# LLM calls
# ---------------------------------------------------------------------------


def call_claude(api_key: str, user_message: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=SYSTEM_PROMPT.format(
            company=PROCUREMENT_POLICY["company"],
            policy=json.dumps(PROCUREMENT_POLICY, indent=2),
        ),
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


def call_openai(api_key: str, user_message: str) -> str:
    import openai

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=2000,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(
                    company=PROCUREMENT_POLICY["company"],
                    policy=json.dumps(PROCUREMENT_POLICY, indent=2),
                ),
            },
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def parse_agent_response(text: str) -> dict | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None


# ---------------------------------------------------------------------------
# UI rendering helpers
# ---------------------------------------------------------------------------

RECOMMENDATION_STYLES = {
    "approve": ("Approved", "#28a745", "Ready to proceed"),
    "approve_with_conditions": ("Approved with Conditions", "#ffc107", "Requires action before proceeding"),
    "escalate": ("Escalation Required", "#fd7e14", "Needs additional review"),
    "reject": ("Rejected", "#dc3545", "Does not meet policy requirements"),
}

STATUS_ICONS = {"pass": "&#9989;", "fail": "&#10060;", "warning": "&#9888;&#65039;"}
SEVERITY_COLORS = {"low": "#17a2b8", "medium": "#ffc107", "high": "#dc3545"}


def render_result(result: dict) -> None:
    rec = result.get("recommendation", "escalate")
    label, color, subtitle = RECOMMENDATION_STYLES.get(
        rec, ("Unknown", "#6c757d", "")
    )

    st.markdown(
        f"""<div style="background:{color}22; border-left:4px solid {color};
        padding:12px 16px; border-radius:4px; margin-bottom:16px;">
        <span style="color:{color}; font-weight:700; font-size:1.2em;">{label}</span>
        <br><span style="color:#666;">{subtitle}</span></div>""",
        unsafe_allow_html=True,
    )

    st.markdown(f"**Agent reasoning:** {result.get('reasoning', 'N/A')}")

    # --- Metrics row ---
    parsed = result.get("parsed_request", {})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Estimated Cost", f"${parsed.get('estimated_cost', 0):,.0f}")
    c2.metric("Category", result.get("spend_category", "N/A"))
    c3.metric("Urgency", parsed.get("urgency", "N/A").title())
    c4.metric("Approval Level", result.get("approval_level", "N/A"))

    # --- Parsed request ---
    with st.expander("Parsed Request Details", expanded=False):
        st.write(f"**Item:** {parsed.get('item', 'N/A')}")
        st.write(f"**Vendor:** {parsed.get('vendor') or 'Not specified'}")
        st.write(f"**Department:** {parsed.get('department', 'Not specified')}")

    # --- Approval chain ---
    chain = result.get("approval_chain", [])
    if chain:
        st.markdown("#### Approval Chain")
        cols = st.columns(min(len(chain), 5))
        for i, approver in enumerate(chain):
            with cols[i % 5]:
                step_color = "#28a745" if i == 0 else "#6c757d"
                st.markdown(
                    f"""<div style="text-align:center; padding:8px; background:{step_color}18;
                    border:1px solid {step_color}44; border-radius:6px;">
                    <div style="font-size:0.75em; color:#999;">Step {i + 1}</div>
                    <div style="font-weight:600;">{approver}</div></div>""",
                    unsafe_allow_html=True,
                )

    # --- Policy checks ---
    checks = result.get("policy_checks", [])
    if checks:
        st.markdown("#### Policy Compliance Checks")
        for check in checks:
            status = check.get("status", "warning")
            icon = STATUS_ICONS.get(status, "&#8226;")
            st.markdown(
                f"{icon} **{check.get('rule', '')}** — {check.get('detail', '')}",
                unsafe_allow_html=True,
            )

    # --- Risks ---
    risks = result.get("risks", [])
    if risks:
        st.markdown("#### Risk Flags")
        for risk in risks:
            sev = risk.get("severity", "low")
            sev_color = SEVERITY_COLORS.get(sev, "#6c757d")
            st.markdown(
                f"""<span style="background:{sev_color}; color:white; padding:2px 8px;
                border-radius:10px; font-size:0.8em; font-weight:600;">
                {sev.upper()}</span> {risk.get('description', '')}""",
                unsafe_allow_html=True,
            )

    # --- Additional requirements ---
    reqs = result.get("additional_requirements", [])
    if reqs:
        st.markdown("#### Additional Requirements")
        for r in reqs:
            st.markdown(f"- {r}")


# ---------------------------------------------------------------------------
# Sample requests for quick demo
# ---------------------------------------------------------------------------

SAMPLES = {
    "IT Hardware — $75K laptops": (
        "I need to purchase 50 Dell Latitude laptops for the engineering team. "
        "Budget is approximately $75,000. We need them within 3 weeks for new hires starting next month."
    ),
    "Professional Services — $250K consulting": (
        "We want to engage McKinsey for a 3-month supply chain optimization project. "
        "The estimated cost is $250,000. This is for the Operations department and is high priority — "
        "our CEO wants findings by Q3."
    ),
    "Software — $30K renewal": (
        "Need to renew our Salesforce Enterprise licenses — 200 seats at $150/seat/year, "
        "totaling $30,000. Current contract expires in 45 days. This is for the Sales department."
    ),
    "Non-preferred vendor — $80K": (
        "We'd like to purchase cloud GPU instances from CoreWeave for our ML training pipeline. "
        "Estimated annual spend is $80,000. The Data Science team needs this urgently — "
        "our current capacity is maxed out."
    ),
    "Low spend — $500 office supplies": (
        "I need to order some ergonomic keyboards and mice from Staples for my team of 10. "
        "Total should be around $500."
    ),
}

# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(
        page_title="Procurement AI Agent",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # --- Sidebar ---
    with st.sidebar:
        st.title("Configuration")

        provider = st.selectbox("LLM Provider", ["Claude (Anthropic)", "OpenAI"])
        api_key = st.text_input(
            "API Key",
            type="password",
            help="Your Anthropic or OpenAI API key",
        )

        st.divider()
        st.subheader("Active Procurement Policy")
        st.caption(PROCUREMENT_POLICY["company"])

        with st.expander("Spend Thresholds"):
            for level, amount in PROCUREMENT_POLICY["spend_thresholds"].items():
                label = level.replace("_", " ").title()
                st.markdown(f"**{label}:** ${amount:,}")

        with st.expander("Preferred Vendors"):
            for cat, vendors in PROCUREMENT_POLICY["preferred_vendors"].items():
                st.markdown(f"**{cat}:** {', '.join(vendors)}")

        with st.expander("Category Rules"):
            for cat, rules in PROCUREMENT_POLICY["category_rules"].items():
                items = ", ".join(
                    k.replace("_", " ") for k, v in rules.items() if v is True
                )
                extras = {
                    k: v for k, v in rules.items() if not isinstance(v, bool)
                }
                line = f"**{cat}:** {items}"
                if extras:
                    line += " | " + ", ".join(
                        f"{k.replace('_', ' ')}: ${v:,}"
                        if isinstance(v, (int, float))
                        else f"{k}: {v}"
                        for k, v in extras.items()
                    )
                st.markdown(line)

        with st.expander("Compliance Rules"):
            for rule, val in PROCUREMENT_POLICY["compliance"].items():
                display = "Yes" if isinstance(val, bool) and val else f"${val:,}"
                st.markdown(f"**{rule.replace('_', ' ').title()}:** {display}")

    # --- Header ---
    st.title("Procurement Purchase Request Agent")
    st.markdown(
        "AI-powered intake, policy compliance checking, and approval routing "
        "for enterprise procurement requests."
    )
    st.markdown("---")

    # --- Sample request buttons ---
    st.markdown("##### Quick Demo — click a sample request")
    cols = st.columns(len(SAMPLES))
    for i, (label, text) in enumerate(SAMPLES.items()):
        with cols[i]:
            if st.button(label, use_container_width=True, key=f"sample_{i}"):
                st.session_state["request_text"] = text

    # --- Input ---
    st.markdown("##### Or write your own purchase request")
    request_text = st.text_area(
        "Describe what you need to purchase",
        value=st.session_state.get("request_text", ""),
        height=100,
        placeholder=(
            "e.g. 'I need 10 standing desks from Herman Miller for the NYC office, "
            "budget around $15,000. Facilities team, medium urgency.'"
        ),
        label_visibility="collapsed",
    )

    if st.button("Analyze Request", type="primary", use_container_width=True):
        if not api_key:
            st.error("Enter your API key in the sidebar to enable the agent.")
            return
        if not request_text.strip():
            st.warning("Enter a purchase request first.")
            return

        with st.spinner("Agent analyzing request..."):
            try:
                if "Claude" in provider:
                    raw = call_claude(api_key, request_text)
                else:
                    raw = call_openai(api_key, request_text)

                result = parse_agent_response(raw)

                if result:
                    st.markdown("---")
                    st.markdown("### Agent Analysis")
                    render_result(result)

                    if "history" not in st.session_state:
                        st.session_state.history = []
                    st.session_state.history.insert(
                        0,
                        {
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "request": request_text[:80],
                            "recommendation": result.get("recommendation", "N/A"),
                            "cost": result.get("parsed_request", {}).get(
                                "estimated_cost", 0
                            ),
                            "category": result.get("spend_category", "N/A"),
                        },
                    )
                else:
                    st.error("Could not parse agent response.")
                    with st.expander("Raw response"):
                        st.code(raw)

            except Exception as e:
                st.error(f"Error: {e}")

    # --- History ---
    if st.session_state.get("history"):
        st.markdown("---")
        st.markdown("### Request History")
        for entry in st.session_state.history:
            rec = entry["recommendation"]
            color = RECOMMENDATION_STYLES.get(rec, ("", "#6c757d", ""))[1]
            st.markdown(
                f"**{entry['time']}** | {entry['request']}... | "
                f"${entry['cost']:,.0f} | {entry['category']} | "
                f"<span style='color:{color}; font-weight:600;'>{rec.replace('_', ' ').title()}</span>",
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    main()
