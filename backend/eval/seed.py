"""Public evaluation seed — clearly fictional ACME INDUSTRIES demo data.

Builds the eval workspace end-to-end through the REAL pipeline
(upload → process → clauses → obligations → review → deadlines →
recurrence → risk → comments/evidence → audit), so recruiters exercise the
same code paths as production workspaces.
"""
from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

EVAL_ORG_SLUG = "acme-industries"
EVAL_PUBLIC_SLUG = "eval"
VISITOR_EMAIL = "eval-visitor@clauseradar.local"

# (title, counterparty, renewal, end, sentences)
CONTRACTS: list[tuple] = [
    ("Vendor Master Services Agreement", "Globex Corporation", date(2027, 3, 15), date(2027, 3, 14), [
        "The Vendor shall maintain valid cyber insurance throughout the term.",
        "The Vendor shall provide monthly reports detailing service performance.",
        "Payment terms: invoices are due net 30 days from receipt of invoice.",
        "The Vendor shall notify the Client 60 days before renewal of the agreement.",
        "Either party may terminate for convenience with 30 days notice of termination.",
        "The Vendor agrees to protect all confidential information disclosed under this agreement.",
        "The Vendor shall maintain 99.9% uptime as measured monthly with service credits.",
        "The Client shall have the right to audit the Vendor's records once per year.",
        "The Vendor shall deliver all milestones according to the delivery schedule.",
        "The Vendor shall comply with all applicable data protection laws including GDPR.",
        "The Vendor shall submit all invoices electronically with detailed time records.",
        "The Client must approve any subcontractors in writing before work begins.",
        "The Vendor shall retain all project records for at least three years here.",
    ]),
    ("Cloud SaaS Subscription", "Initech LLC", date(2026, 11, 10), date(2027, 11, 9), [
        "The Provider shall maintain SOC 2 compliance throughout the subscription term.",
        "The Provider shall deliver monthly uptime reports to the Customer liaison.",
        "Subscription fees are due net 15 days from the invoice date without exception.",
        "The Customer must provide 30 days notice before renewal of the subscription.",
        "The Provider shall encrypt all customer data at rest and in transit always.",
        "The Provider agrees to notify the Customer within 72 hours of any data breach.",
        "Service levels require 99.95% uptime with response times under one hour daily.",
        "The Customer shall pay all overage fees within 30 days of invoice receipt.",
        "The Provider shall provide annual penetration test summaries to the Customer.",
        "The Customer must keep its account credentials confidential at all times.",
    ]),
    ("Facilities Lease — HQ", "Hooli Properties", date(2028, 1, 31), date(2028, 1, 30), [
        "The Tenant shall maintain property insurance throughout the lease term period.",
        "Rent is due monthly on the first day of each calendar month without fail.",
        "The Tenant shall not make alterations without written consent of the Landlord.",
        "The Landlord shall provide 90 days notice before renewal of the lease term.",
        "The Tenant agrees to comply with all building safety regulations at all times.",
        "The Tenant shall deliver a certificate of insurance annually to the Landlord.",
        "The Tenant must report any maintenance issues within 24 hours of discovery.",
        "The Landlord shall maintain common areas in good repair throughout the term.",
    ]),
    ("Cyber Insurance Policy", "Stark Assurance", date(2027, 6, 30), date(2027, 6, 29), [
        "The Insurer shall provide cyber liability coverage up to five million dollars.",
        "Premiums are due quarterly in advance of each coverage period start date.",
        "The Policyholder must notify the Insurer within 48 hours of any incident.",
        "The Policyholder shall complete an annual security assessment questionnaire.",
        "Coverage excludes losses arising from unpatched systems known for over 30 days.",
        "The Insurer shall deliver claim decisions within 30 days of receipt here.",
        "The Policyholder shall maintain multi-factor authentication on all systems.",
        "The Insurer must provide written renewal terms 60 days before expiry here.",
    ]),
    ("Consulting Statement of Work", "Umbrella Labs", None, date(2026, 12, 20), [
        "The Contractor shall deliver the discovery report within 30 days of kickoff.",
        "The Contractor shall provide weekly status reports throughout the engagement.",
        "Fees are payable net 30 days from acceptance of each deliverable milestone.",
        "The Client shall assign a project liaison within 5 days of project start.",
        "All work product must meet the acceptance criteria defined in Exhibit A.",
        "The Contractor agrees to keep all client materials strictly confidential always.",
        "The Contractor shall obtain written approval before exceeding budgeted hours.",
        "The Client must provide timely feedback within 10 days of each delivery.",
    ]),
    ("Logistics & Delivery Agreement", "Wayne Freight", date(2027, 9, 1), date(2027, 8, 31), [
        "The Carrier shall deliver all shipments according to the agreed delivery schedule.",
        "The Carrier shall maintain cargo insurance at all times during the transport.",
        "The Carrier shall provide monthly delivery performance reports with metrics.",
        "Late deliveries beyond 48 hours will incur service credits against invoices.",
        "Either party may terminate this agreement with 60 days notice for any reason.",
        "The Carrier must comply with all transportation safety regulations at all times.",
        "The Carrier shall notify the Shipper immediately of any delays over 12 hours.",
        "The Shipper must provide accurate manifests at least 24 hours before pickup.",
    ]),
]

# Version-2 texts: payment term changed 30 → 15 + one added sentence.
V2_OVERRIDES = {
    "Vendor Master Services Agreement": (
        "Payment terms: invoices are due net 15 days from receipt of invoice.",
        "The Vendor shall provide quarterly business reviews in addition to reports.",
    ),
    "Cloud SaaS Subscription": (
        "Subscription fees are due net 30 days from the invoice date without exception.",
        "The Provider shall appoint a dedicated account manager for the Customer.",
    ),
}


def _pdf_bytes(title: str, sentences: list[str]) -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    y = 72
    page.insert_text((72, y), title)
    y += 28
    for s in sentences:
        if y > 750:
            page = doc.new_page()
            y = 72
        page.insert_text((72, y), s, fontsize=10)
        y += 22
    data = bytes(doc.tobytes())
    doc.close()
    return data


@transaction.atomic
def seed_eval_workspace() -> dict:
    """Seed the eval workspace, or no-op when healthy seed data exists.

    Safe to run on every production build: an existing workspace that
    already holds contracts is left untouched (recruiter uploads and review
    state survive redeploys). A missing or contract-less workspace triggers
    a full wipe-and-rebuild inside one transaction (all-or-nothing).
    Returns summary stats including "skipped".
    """
    from contracts.models import Contract
    from workspaces.models import Workspace

    existing = Workspace.objects.filter(
        workspace_type="PUBLIC_EVAL", public_slug=EVAL_PUBLIC_SLUG
    ).first()
    if existing is not None and Contract.objects.filter(workspace=existing).exists():
        return _summarize(existing, skipped=True)
    return _build_eval_workspace()


def _summarize(ws, *, skipped: bool) -> dict:
    from audit.models import AuditEvent
    from clauses.models import Clause
    from contracts.models import Contract, ContractVersion
    from deadlines.models import Deadline
    from documents.models import Document as _D
    from obligations.models import Obligation
    from risks.models import RiskFinding

    return {
        "skipped": skipped,
        "workspace": str(ws.id),
        "contracts": Contract.objects.filter(workspace=ws).count(),
        "versions": ContractVersion.objects.filter(contract__workspace=ws).count(),
        "documents": _D.objects.filter(workspace=ws).count(),
        "clauses": Clause.objects.filter(workspace=ws).count(),
        "obligations": Obligation.objects.filter(workspace=ws).count(),
        "deadlines": Deadline.objects.filter(workspace=ws).count(),
        "risks": RiskFinding.objects.filter(workspace=ws).count(),
        "audit": AuditEvent.objects.filter(workspace=ws).count(),
    }


@transaction.atomic
def _build_eval_workspace() -> dict:
    """Wipe-and-rebuild the eval workspace (used for first deploy + reset)."""
    from clauses.services import extract_clauses_for_document
    from contracts.models import Contract
    from contracts.versions import ensure_version_for_document
    from deadlines.services import generate_for_contract, generate_for_obligation
    from documents.models import Document
    from documents.services import process_document
    from obligations.models import Obligation
    from obligations.services import activate_obligation, confirm_obligation
    from organizations.models import Organization, OrganizationMembership
    from risks.services import assess_contract_risks
    from workflows.models import Evidence
    from workspaces.models import Workspace, WorkspaceMembership

    User = get_user_model()
    # Wipe previous eval data (cascade) but keep global visitor + demo accounts.
    Organization.objects.filter(slug=EVAL_ORG_SLUG).delete()

    owner = User.objects.filter(email="demo-owner@clauseradar.local").first()
    if owner is None:
        owner = User.objects.create_user(email="demo-owner@clauseradar.local", password="demo-fictional")
        owner.display_name = "Ava (demo admin)"
        owner.save()
    members = []
    for email, name in (("maya.chen@clauseradar.local", "Maya Chen (demo)"),
                        ("sam.rivera@clauseradar.local", "Sam Rivera (demo)")):
        u = User.objects.filter(email=email).first()
        if u is None:
            u = User.objects.create_user(email=email, password="demo-fictional")
            u.display_name = name
            u.save()
        members.append(u)
    visitor = User.objects.filter(email=VISITOR_EMAIL).first()
    if visitor is None:
        visitor = User.objects.create_user(email=VISITOR_EMAIL, password=None)
        visitor.display_name = "Evaluation visitor"
        visitor.set_unusable_password()
        visitor.save()

    org = Organization.objects.create(name="ACME INDUSTRIES (fictional demo)", slug=EVAL_ORG_SLUG, created_by=owner)
    for u, role in [(owner, "OWNER"), *[(m, "MEMBER") for m in members], (visitor, "MEMBER")]:
        OrganizationMembership.objects.create(organization=org, user=u, role=role)
    ws = Workspace.objects.create(
        organization=org, name="Evaluation", slug="evaluation", workspace_type="PUBLIC_EVAL",
        public_slug=EVAL_PUBLIC_SLUG, created_by=owner,
        description="Fictional demo data for evaluating ClauseRadar. Reset anytime.",
    )
    for u, role in [(owner, "OWNER"), *[(m, "MEMBER") for m in members], (visitor, "MEMBER")]:
        WorkspaceMembership.objects.create(workspace=ws, user=u, role=role)

    contracts = []
    for title, counterparty, renewal, end, sentences in CONTRACTS:
        contract = Contract.objects.create(
            workspace=ws, title=title, counterparty=counterparty, status="ACTIVE",
            start_date=date(2026, 1, 15), end_date=end, renewal_date=renewal,
            description=f"Fictional demo contract for evaluation ({title}).", created_by=owner)
        contracts.append((contract, sentences))
        data = _pdf_bytes(title, sentences)
        doc = Document(
            workspace=ws, contract=contract, original_filename=f"{title[:40]}.pdf",
            mime="application/pdf", size_bytes=len(data),
            sha256=__import__("hashlib").sha256(data).hexdigest(),
            status="UPLOADED", created_by=owner)
        doc.file.save(f"{doc.id}/{title[:20]}.pdf", ContentFile(data), save=False)
        doc.save()
        process_document(doc.id)
        extract_clauses_for_document(doc.id)
        from obligations.services import extract_obligations_for_document

        extract_obligations_for_document(doc.id)
        ensure_version_for_document(doc.id)
        generate_for_contract(contract.id)
        for ob in Obligation.objects.filter(document=doc):
            generate_for_obligation(ob.id)

    # Second versions for two contracts (payment term change + added sentence).
    for title, counterparty, renewal, end, sentences in CONTRACTS:
        if title not in V2_OVERRIDES:
            continue
        new_payment, added = V2_OVERRIDES[title]
        v2_sentences = [(new_payment if "net " in s and ("due" in s or "payable" in s) else s) for s in sentences] + [added]
        contract = next(c for c, _ in contracts if c.title == title)
        data = _pdf_bytes(title + " (Amendment 1)", v2_sentences)
        doc = Document(
            workspace=ws, contract=contract, original_filename=f"{title[:40]}-amendment.pdf",
            mime="application/pdf", size_bytes=len(data),
            sha256=__import__("hashlib").sha256(data).hexdigest(),
            status="UPLOADED", created_by=owner)
        doc.file.save(f"{doc.id}/amendment.pdf", ContentFile(data), save=False)
        doc.save()
        process_document(doc.id)
        extract_clauses_for_document(doc.id)
        from obligations.services import extract_obligations_for_document

        extract_obligations_for_document(doc.id)
        ensure_version_for_document(doc.id)

    # Human verification trail: confirm ~2/3, activate recurring + some others.
    all_obs = list(Obligation.objects.filter(workspace=ws).order_by("created_at"))
    for i, ob in enumerate(all_obs):
        if i % 3 == 2:
            continue  # leave every third one NEEDS_REVIEW (review queue demo)
        confirm_obligation(ob.id, reviewer=owner)
    for ob in Obligation.objects.filter(workspace=ws, status="CONFIRMED"):
        fresh = Obligation.objects.get(pk=ob.pk)
        if fresh.frequency in ("MONTHLY", "QUARTERLY", "ANNUAL", "WEEKLY", "SEMI_ANNUAL", "DAILY"):
            activate_obligation(fresh.id, actor=owner)
    # Ownership: assign some, leave others ownerless (risk demo).
    assignable = list(Obligation.objects.filter(workspace=ws, status__in=("CONFIRMED", "ACTIVE")))
    for i, ob in enumerate(assignable):
        if i % 3 == 0:
            from obligations.services import assign_owner

            assign_owner(ob.id, actor=owner, owner=members[i % len(members)])
    # Evidence on some insurance obligations; others stay missing (risk demo).
    insured = list(Obligation.objects.filter(workspace=ws, obligation_type="INSURANCE", status__in=("CONFIRMED", "ACTIVE")))
    for ob in insured[: max(1, len(insured) // 2)]:
        cert = _pdf_bytes("Certificate of Insurance (fictional)", ["Fictional certificate for demo purposes only."])
        ev = Evidence(workspace=ws, obligation=ob, original_filename="certificate.pdf",
                      mime="application/pdf", size_bytes=len(cert),
                      sha256=__import__("hashlib").sha256(cert).hexdigest(),
                      note="Fictional demo certificate.", uploaded_by=owner)
        ev.file.save(f"{ev.id}/certificate.pdf", ContentFile(cert), save=False)
        ev.save()
    # Comments trail.
    from workflows.models import Comment

    first_contract = contracts[0][0]
    Comment.objects.create(workspace=ws, contract=first_contract, author=owner,
                           body="Fictional demo: legal reviewed the MSA renewal terms.")
    first_ob = Obligation.objects.filter(workspace=ws).first()
    if first_ob:
        Comment.objects.create(workspace=ws, obligation=first_ob, author=members[0],
                               body="Fictional demo: broker confirmed coverage meets the requirement.")
    # Backdate a few NEEDS_REVIEW rows to demo the review-backlog risk rule.
    backlog = list(Obligation.objects.filter(workspace=ws, status="NEEDS_REVIEW")[:5])
    old_date = timezone.now() - timedelta(days=20)
    for ob in backlog:
        Obligation.objects.filter(pk=ob.pk).update(created_at=old_date)
    # Risk assessment for every contract.
    for contract, _ in contracts:
        assess_contract_risks(contract.id)

    return _summarize(ws, skipped=False)
