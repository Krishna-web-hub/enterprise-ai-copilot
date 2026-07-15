"""
Security Audit Logging

Logs security-relevant events (login, logout, registration, failed auth)
to a dedicated logger that can be routed to a SIEM or log aggregator.

Why separate audit logs from application logs?
- Compliance: Regulations (SOC2, GDPR, HIPAA) require auth event records.
- Forensics: After an incident, you need to know who logged in when.
- Alerting: Spikes in failed logins trigger security team alerts.
- Separation: Audit logs can be stored longer than application logs.

In production, route the "app.audit" logger to:
- A dedicated CloudWatch log group
- A SIEM (Splunk, Elastic SIEM, Datadog Security)
- An immutable audit trail (S3 + Object Lock)
"""

import logging
from typing import Optional

audit_logger = logging.getLogger("app.audit")


def log_auth_event(
    event: str,
    email: str,
    success: bool,
    ip_address: Optional[str] = None,
    user_id: Optional[int] = None,
    detail: Optional[str] = None,
) -> None:
    """
    Log an authentication event.

    Events: LOGIN, LOGOUT, REGISTER, REFRESH, FAILED_LOGIN, LOCKOUT
    """
    level = logging.INFO if success else logging.WARNING
    msg = (
        f"AUTH_EVENT={event} "
        f"email={email} "
        f"success={success} "
        f"ip={ip_address or 'unknown'} "
        f"user_id={user_id or 'none'}"
    )
    if detail:
        msg += f" detail={detail}"

    audit_logger.log(level, msg)
