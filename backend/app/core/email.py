import logging

logger = logging.getLogger(__name__)


async def send_verification_email(email: str, token: str, username: str) -> None:
    verification_url = f"/verify-email?token={token}"
    logger.info(f"[EMAIL] Verification → {email} | user={username} | url={verification_url}")


async def send_password_reset_email(email: str, token: str) -> None:
    reset_url = f"/reset-password?token={token}"
    logger.info(f"[EMAIL] Password reset → {email} | url={reset_url}")


async def send_order_confirmation(email: str, order_id: int, amount: float) -> None:
    logger.info(f"[EMAIL] Order confirmation → {email} | order=#{order_id} | total=${amount:.2f}")


async def send_order_shipped_notification(email: str, order_id: int, tracking: str) -> None:
    logger.info(f"[EMAIL] Order shipped → {email} | order=#{order_id} | tracking={tracking}")


async def send_dispute_opened(buyer_email: str, seller_email: str, order_id: int) -> None:
    logger.info(f"[EMAIL] Dispute opened → buyer={buyer_email} seller={seller_email} | order=#{order_id}")


async def send_dispute_resolved(email: str, order_id: int, resolution: str) -> None:
    logger.info(f"[EMAIL] Dispute resolved → {email} | order=#{order_id} | resolution={resolution}")


async def send_payout_notification(email: str, amount: float, payout_status: str) -> None:
    logger.info(f"[EMAIL] Payout {payout_status} → {email} | amount=${amount:.2f}")


async def send_refund_notification(email: str, order_id: int, amount: float) -> None:
    logger.info(f"[EMAIL] Refund processed → {email} | order=#{order_id} | amount=${amount:.2f}")
