import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api import (
    accounting_periods,
    audit_checklists,
    audit_engagements,
    audit_findings,
    audit_reports,
    audit_reviews,
    auth,
    bank_accounts,
    bank_matches,
    bank_reconciliations,
    bank_reports,
    bank_statements,
    bank_transactions,
    companies,
    compliance_calendar,
    compliance_obligations,
    compliance_reports,
    compliance_rules,
    compliance_tasks,
    credit_notes,
    customers,
    debit_notes,
    documents,
    financial_years,
    gst_profile,
    gst_reconciliation,
    gst_reports,
    gst_return_periods,
    gst_return_snapshots,
    gst_tax_rates,
    gstr1,
    gstr2b,
    gstr3b,
    health,
    imports,
    income_tax_capital_gains,
    income_tax_computations,
    income_tax_deductions,
    income_tax_income,
    income_tax_losses,
    income_tax_payments,
    income_tax_profile,
    income_tax_reports,
    itc,
    itr_preparations,
    journal_entries,
    ledgers,
    notifications,
    opening_balances,
    payments,
    products,
    purchase_invoices,
    receipts,
    reports,
    roles,
    sales_invoices,
    tds_challans,
    tds_profile,
    tds_reconciliation,
    tds_reports,
    tds_return_periods,
    tds_return_snapshots,
    tds_review_notes,
    tds_rules,
    tds_sections,
    tds_transactions,
    deductees,
    users,
    vendors,
    audit_logs,
)
from app.core.config import settings
from app.core.exceptions import AppException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    sweep_task = None
    if settings.COMPLIANCE_SWEEP_ENABLED and settings.COMPLIANCE_SWEEP_INTERVAL_SECONDS > 0:
        from app.services.compliance_scheduler import periodic_compliance_sweep

        sweep_task = asyncio.create_task(
            periodic_compliance_sweep(settings.COMPLIANCE_SWEEP_INTERVAL_SECONDS)
        )
    yield
    if sweep_task is not None:
        sweep_task.cancel()
        try:
            await sweep_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Phase 1: Foundation, Authentication, RBAC & Multi-Tenant Architecture",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


def _error_response(code: str, message: str, status_code: int, fields: dict | None = None):
    body = {"success": False, "error": {"code": code, "message": message}}
    if fields:
        body["error"]["fields"] = fields
    return JSONResponse(status_code=status_code, content=body)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return _error_response(exc.code, exc.message, exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    fields: dict[str, list[str]] = {}
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        fields.setdefault(field or "body", []).append(error["msg"])
    return _error_response(
        "VALIDATION_ERROR", "One or more fields are invalid", 422, fields=fields
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.warning("Database integrity error on %s: %s", request.url.path, exc.orig)
    return _error_response(
        "DUPLICATE_RESOURCE", "This operation violates a data integrity constraint", 409
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    logger.exception("Unhandled error on %s (request_id=%s)", request.url.path, request_id)
    return _error_response("INTERNAL_ERROR", "An unexpected error occurred", 500)


app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(companies.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(roles.router, prefix=settings.API_V1_PREFIX)
app.include_router(audit_logs.router, prefix=settings.API_V1_PREFIX)
app.include_router(documents.router, prefix=settings.API_V1_PREFIX)
app.include_router(financial_years.router, prefix=settings.API_V1_PREFIX)
app.include_router(accounting_periods.router, prefix=settings.API_V1_PREFIX)
app.include_router(ledgers.router, prefix=settings.API_V1_PREFIX)
app.include_router(customers.router, prefix=settings.API_V1_PREFIX)
app.include_router(vendors.router, prefix=settings.API_V1_PREFIX)
app.include_router(products.router, prefix=settings.API_V1_PREFIX)
app.include_router(sales_invoices.router, prefix=settings.API_V1_PREFIX)
app.include_router(purchase_invoices.router, prefix=settings.API_V1_PREFIX)
app.include_router(credit_notes.router, prefix=settings.API_V1_PREFIX)
app.include_router(debit_notes.router, prefix=settings.API_V1_PREFIX)
app.include_router(payments.router, prefix=settings.API_V1_PREFIX)
app.include_router(receipts.router, prefix=settings.API_V1_PREFIX)
app.include_router(journal_entries.router, prefix=settings.API_V1_PREFIX)
app.include_router(opening_balances.router, prefix=settings.API_V1_PREFIX)
app.include_router(imports.router, prefix=settings.API_V1_PREFIX)
app.include_router(reports.router, prefix=settings.API_V1_PREFIX)
app.include_router(gst_profile.router, prefix=settings.API_V1_PREFIX)
app.include_router(gst_tax_rates.router, prefix=settings.API_V1_PREFIX)
app.include_router(gst_return_periods.router, prefix=settings.API_V1_PREFIX)
app.include_router(gst_return_snapshots.router, prefix=settings.API_V1_PREFIX)
app.include_router(gst_reports.router, prefix=settings.API_V1_PREFIX)
app.include_router(gstr1.router, prefix=settings.API_V1_PREFIX)
app.include_router(gstr2b.router, prefix=settings.API_V1_PREFIX)
app.include_router(gst_reconciliation.router, prefix=settings.API_V1_PREFIX)
app.include_router(itc.router, prefix=settings.API_V1_PREFIX)
app.include_router(gstr3b.router, prefix=settings.API_V1_PREFIX)
app.include_router(tds_profile.router, prefix=settings.API_V1_PREFIX)
app.include_router(tds_sections.router, prefix=settings.API_V1_PREFIX)
app.include_router(tds_rules.router, prefix=settings.API_V1_PREFIX)
app.include_router(deductees.router, prefix=settings.API_V1_PREFIX)
app.include_router(tds_transactions.router, prefix=settings.API_V1_PREFIX)
app.include_router(tds_challans.router, prefix=settings.API_V1_PREFIX)
app.include_router(tds_reconciliation.router, prefix=settings.API_V1_PREFIX)
app.include_router(tds_return_periods.router, prefix=settings.API_V1_PREFIX)
app.include_router(tds_return_snapshots.router, prefix=settings.API_V1_PREFIX)
app.include_router(tds_review_notes.router, prefix=settings.API_V1_PREFIX)
app.include_router(tds_reports.router, prefix=settings.API_V1_PREFIX)
app.include_router(bank_accounts.router, prefix=settings.API_V1_PREFIX)
app.include_router(bank_statements.router, prefix=settings.API_V1_PREFIX)
app.include_router(bank_transactions.router, prefix=settings.API_V1_PREFIX)
app.include_router(bank_matches.router, prefix=settings.API_V1_PREFIX)
app.include_router(bank_reconciliations.router, prefix=settings.API_V1_PREFIX)
app.include_router(bank_reports.router, prefix=settings.API_V1_PREFIX)
app.include_router(audit_engagements.router, prefix=settings.API_V1_PREFIX)
app.include_router(audit_checklists.router, prefix=settings.API_V1_PREFIX)
app.include_router(audit_findings.router, prefix=settings.API_V1_PREFIX)
app.include_router(audit_reviews.router, prefix=settings.API_V1_PREFIX)
app.include_router(audit_reports.router, prefix=settings.API_V1_PREFIX)
app.include_router(income_tax_profile.router, prefix=settings.API_V1_PREFIX)
app.include_router(income_tax_income.router, prefix=settings.API_V1_PREFIX)
app.include_router(income_tax_capital_gains.router, prefix=settings.API_V1_PREFIX)
app.include_router(income_tax_deductions.router, prefix=settings.API_V1_PREFIX)
app.include_router(income_tax_losses.router, prefix=settings.API_V1_PREFIX)
app.include_router(income_tax_payments.router, prefix=settings.API_V1_PREFIX)
app.include_router(income_tax_computations.router, prefix=settings.API_V1_PREFIX)
app.include_router(itr_preparations.router, prefix=settings.API_V1_PREFIX)
app.include_router(income_tax_reports.router, prefix=settings.API_V1_PREFIX)
app.include_router(compliance_rules.router, prefix=settings.API_V1_PREFIX)
app.include_router(compliance_obligations.router, prefix=settings.API_V1_PREFIX)
app.include_router(compliance_tasks.router, prefix=settings.API_V1_PREFIX)
app.include_router(compliance_calendar.router, prefix=settings.API_V1_PREFIX)
app.include_router(compliance_reports.router, prefix=settings.API_V1_PREFIX)
app.include_router(notifications.router, prefix=settings.API_V1_PREFIX)
