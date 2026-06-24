# SAP Ariba — Technical Architecture Primer

## The #1 Misconception: Ariba is NOT S/4HANA

This is the most important thing to understand:

| | SAP S/4HANA | SAP Ariba |
|---|---|---|
| **What it is** | ERP system (finance, logistics, manufacturing) | Cloud procurement platform (sourcing, buying, invoicing) |
| **Built on** | ABAP stack, HANA database | Java-based cloud-native stack (pre-acquisition: proprietary Java platform) |
| **Where it runs** | On-premise or SAP private cloud | SAP's multi-tenant public cloud (now migrating to BTP) |
| **Data model** | Materials, vendors, FI/CO postings, ABAP tables | Procurement documents, supplier profiles, spend categories |
| **UI** | SAP Fiori (SAPUI5) | Ariba's own web UI (now converging to Fiori-based via BTP) |

**Ariba was never built on ABAP.** It was a standalone Java/web-based SaaS product long before SAP acquired it in 2012 for $4.3B. After acquisition, SAP kept it running on its own stack — they didn't rewrite it in ABAP.

---

## Ariba's Architecture History

### Pre-SAP Era (1996–2012)
- Founded 1996, IPO 1999 — one of the first B2B internet companies
- Built as a **Java-based web application** — cloud-native before the term existed
- Core product: **Ariba Network** — a B2B marketplace connecting buyers and suppliers
- Ran on its own proprietary cloud infrastructure (not AWS/Azure at the time)
- Acquired FreeMarkets (2004) for sourcing / e-auction capabilities

### Post-Acquisition Legacy (2012–2025)
- SAP kept Ariba running on its **original Java-based monolithic architecture**
- Bolted on integrations to S/4HANA and ECC via middleware
- Architecture became a **tightly coupled monolith** — adding features required modifying the core system
- This created long release cycles, stability risks, and integration complexity
- The UI stayed as Ariba's own web interface — not Fiori, not SAPUI5

### Next-Gen Ariba (2026+)
- **Complete ground-up rebuild on SAP BTP** (Business Technology Platform)
- Cloud-native microservices architecture — independent module deployment
- API-first design (not screen-first like the old version)
- Quarterly release cadence (Feb, May, Aug, Nov) instead of multi-year cycles
- Joule AI agent integration via SAP AI Core
- Unified data model across source-to-pay (previously siloed by module)

---

## How Ariba Integrates with S/4HANA

Ariba and S/4HANA are **separate systems** that talk to each other through an integration layer. They are NOT the same platform.

### Integration Architecture

```
┌─────────────────┐         ┌──────────────────────────────┐        ┌──────────────────┐
│                 │         │   Integration Layer          │        │                  │
│   SAP Ariba     │ ──────> │   (CIG / Integration Suite)  │ ─────> │  S/4HANA or ECC  │
│   (Cloud)       │ <────── │   on SAP BTP                 │ <───── │  (On-prem/Cloud) │
│                 │         │                              │        │                  │
└─────────────────┘         └──────────────────────────────┘        └──────────────────┘
```

### The Integration Layer: CIG

**CIG = Cloud Integration Gateway** (now called "SAP Integration Suite, managed gateway for spend management and SAP Business Network")

- Runs on **SAP BTP** (Business Technology Platform)
- Pre-built mappings between Ariba documents and S/4HANA objects
- Handles master data sync (vendors, cost centres, GL accounts) and transactional data (requisitions, POs, invoices)
- Wizard-based setup — not custom ABAP development

### Protocols Used

| Protocol | Where Used | Direction |
|---|---|---|
| **SOAP web services** | S/4HANA ↔ CIG (legacy primary method) | Both |
| **OData** | S/4HANA Fiori apps, some newer APIs | Mostly read |
| **REST APIs** | Ariba ↔ external systems, custom integrations | Both |
| **IDoc** | S/4HANA ↔ CIG (traditional SAP document exchange) | Outbound from S/4 |

**Key point:** The S/4HANA side exposes SOAP and OData services. The Ariba side uses REST APIs. CIG sits in the middle and translates between them.

### What Gets Synced

| Data Type | Direction | Example |
|---|---|---|
| **Vendor master** | S/4HANA → Ariba | Vendor names, addresses, bank details |
| **Cost centres / GL** | S/4HANA → Ariba | So requesters can code purchases correctly |
| **Purchase requisitions** | Ariba → S/4HANA | Approved req creates a PO in S/4 |
| **PO confirmations** | S/4HANA → Ariba | PO number, status synced back |
| **Goods receipts** | S/4HANA → Ariba | Receipt status for 3-way matching |
| **Invoices** | Ariba → S/4HANA | Invoice posted to FI for payment |

---

## Where OData Fits

You're right that SAP uses OData heavily — but mainly on the **S/4HANA side**, not the Ariba side:

- **S/4HANA Fiori apps** expose OData services for their UIs
- **S/4HANA public cloud APIs** increasingly use OData v4
- **CIG** consumes these S/4HANA OData/SOAP services to pull and push data
- **Ariba itself** exposes REST APIs (not OData) — these are what Zip and other third-party tools call

### Ariba's Own APIs

| API Type | What It's For |
|---|---|
| **Ariba Operational Reporting API** | Pull procurement data (spend, POs, invoices) — REST-based |
| **Ariba Procurement API** | Create/update requisitions, approvals — REST or SOAP |
| **Ariba Network API** | Supplier collaboration (cXML-based — XML standard for commerce) |
| **Ariba SOAP Web Services** | Legacy integration method — still widely used |
| **Ariba Open APIs** | Newer REST APIs with OAuth 2.0 authentication |

**cXML** is Ariba-specific — it's an XML standard for purchase orders, invoices, and catalogs exchanged over the Ariba Network between buyers and suppliers.

---

## Where BTP Fits

BTP is NOT Ariba's runtime — it's the **platform layer** that SAP is building everything on:

```
┌──────────────────────────────────────────────────────────────┐
│  SAP BTP (Business Technology Platform)                      │
│                                                              │
│  ┌────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │ Integration│  │  Next-Gen Ariba  │  │   SAP AI Core   │  │
│  │ Suite      │  │  (being rebuilt  │  │   (Joule, AI    │  │
│  │ (CIG)      │  │   here)         │  │   agents)       │  │
│  └────────────┘  └──────────────────┘  └─────────────────┘  │
│                                                              │
│  ┌────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │ HANA Cloud │  │  Analytics Cloud │  │  Event Mesh     │  │
│  │ (database) │  │                  │  │  (async events) │  │
│  └────────────┘  └──────────────────┘  └─────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

- **Legacy Ariba** → runs on its own infra, connects to BTP only via CIG
- **Next-Gen Ariba (2026+)** → being rebuilt to run natively ON BTP
- **CIG/Integration Suite** → already runs on BTP — this is how Ariba talks to S/4HANA today
- **SAP AI Core** → on BTP — this is where Joule and AI agents run

---

## Quick Reference: Ariba vs Other SAP Products

| Product | Built On | Language | UI | API Style |
|---|---|---|---|---|
| **S/4HANA** | HANA DB, NetWeaver | ABAP | Fiori (SAPUI5) | OData, BAPI, RFC |
| **Ariba (legacy)** | Proprietary Java cloud | Java | Ariba Web UI | REST, SOAP, cXML |
| **Ariba (next-gen)** | BTP (cloud-native) | Java/microservices | Fiori-based | REST (API-first) |
| **SuccessFactors** | Proprietary cloud | Java | Own UI → Fiori | OData |
| **Concur** | Proprietary cloud | .NET/Java mix | Own UI | REST |
| **Fieldglass** | Proprietary cloud | Java | Own UI | REST |

Notice the pattern: **every SAP cloud acquisition (Ariba, SuccessFactors, Concur, Fieldglass) kept its original tech stack.** None of them were rewritten in ABAP. The Next-Gen initiative (2026+) is SAP's attempt to finally bring them all onto one platform (BTP).

---

## Summary for Your Interview

When the SME asks about Ariba or you're discussing the "hiccups":

1. **Ariba is Java-based cloud SaaS** — it's not ABAP, not S/4HANA, not on HANA DB (legacy version)
2. **It connects to S/4HANA via CIG** (an integration layer on BTP) using SOAP/OData/IDoc
3. **Ariba exposes its own REST and SOAP APIs** — this is what Zip's connector calls
4. **The big transition happening now**: legacy monolith Ariba → Next-Gen Ariba on BTP (microservices, API-first, quarterly releases)
5. **The integration pain**: CIG mediates between two very different systems (ABAP world vs. Java world) — field mapping, data sync timing, and schema mismatches are where things break
