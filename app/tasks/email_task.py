from app.tasks.celery_app import celery_app
import structlog

logger = structlog.get_logger()


@celery_app.task(name="send_verification_email")
def send_verification_email(email: str, token: str) -> None:
    logger.info("send_verification_email", email=email)
    # SMTP logic added in Step 7


@celery_app.task(name="send_password_reset_email")
def send_password_reset_email(email: str, token: str) -> None:
    logger.info("send_password_reset_email", email=email)
    # SMTP logic added in Step 7
