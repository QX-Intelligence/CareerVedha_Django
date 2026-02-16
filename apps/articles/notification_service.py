import requests
import logging
from django.conf import settings
from typing import Optional

logger = logging.getLogger(__name__)


class SpringBootNotificationService:
    """
    Service to send notifications to Spring Boot application via HTTP.
    Handles role-based post notifications when articles are published.
    """

    def __init__(self):
        self.spring_boot_url = getattr(settings, 'SPRING_BOOT_NOTIFICATION_URL')
        self.timeout = getattr(settings, 'NOTIFICATION_TIMEOUT')
        self.auth_token = getattr(settings, 'SPRING_BOOT_AUTH_TOKEN')
        self.auth_header = getattr(settings, 'SPRING_BOOT_AUTH_HEADER')

    def _get_headers(self, token: Optional[str] = None) -> dict:
        """
        Build headers for Spring Boot request with Bearer token.
        
        Args:
            token: Optional Bearer token to use. If provided, uses this instead of configured token.
        
        Returns:
            dict: Headers with Bearer token authentication
        """
        headers = {
            'Content-Type': 'application/json',
        }
        
        # Use provided token, fallback to configured token
        auth_token = token or self.auth_token
        
        # Add authentication token
        if auth_token:
            if auth_token.startswith('Bearer '):
                headers[self.auth_header] = auth_token
            else:
                # Wrap plain token with Bearer
                headers[self.auth_header] = f'Bearer {auth_token}'
        
        return headers

    def send_notification(
        self,
        article_id: int,
        receiver_role: str,
        message: str,
        spring_boot_token: Optional[str] = None
    ) -> bool:
        """
        Send notification to Spring Boot application.
        
        Accepts token per-request, no hardcoding needed.
        If both configured token and request token are missing, skips gracefully.

        Args:
            article_id: ID of the published article
            receiver_role: Target role (EDITOR, PUBLISHER, ADMIN, SUPER_ADMIN)
            message: Notification message
            spring_boot_token: Bearer token for this request (optional)

        Returns:
            bool: True (notifications optional - always return True to not block operations)
        """
        # Check if we have token and URL
        token_to_use = spring_boot_token or self.auth_token
        
        if not self.spring_boot_url:
            logger.warning("Spring Boot URL not configured. Skipping notification.")
            return True
            
        if not token_to_use:
            logger.warning(
                f"No Spring Boot token provided for article {article_id}. "
                f"Pass X-Spring-Boot-Token header or set SPRING_BOOT_AUTH_TOKEN"
            )
            return True
        
        payload = {
            'postId': article_id,
            'receiverRole': receiver_role,
            'message': message
        }

        try:
            logger.info(f"Sending notification for article {article_id} to {self.spring_boot_url}")
            response = requests.post(
                self.spring_boot_url,
                json=payload,
                headers=self._get_headers(token=token_to_use),
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info(
                f" Notification sent successfully. Article: {article_id}, Role: {receiver_role}"
            )
            return True
        except requests.exceptions.HTTPError as e:
            # Log auth errors but don't block
            if response.status_code in [401, 403]:
                logger.error(
                    f" Authorization failed ({response.status_code}) for article {article_id}. "
                    f"Invalid or expired token."
                )
            else:
                logger.error(
                    f" HTTP error {response.status_code} for article {article_id}: {str(e)}"
                )
            return True  # Don't block article operations
        except requests.exceptions.Timeout:
            logger.error(
                f" Timeout sending notification for article {article_id}. Spring Boot slow or unreachable."
            )
            return True
        except requests.exceptions.ConnectionError:
            logger.error(
                f" Connection error for article {article_id}. Spring Boot may be down at {self.spring_boot_url}"
            )
            return True
        except requests.exceptions.RequestException as e:
            logger.error(
                f" Error sending notification for article {article_id}: {str(e)}"
            )
            return True

    def notify_on_review(
        self,
        article_id: int,
        article_title: str,
        contributor_id: str,
        receiver_role: Optional[str] = None,
        spring_boot_token: Optional[str] = None
    ) -> bool:
        """
        Notify editors/publishers when an article moves to REVIEW status.

        Args:
            article_id: ID of the article
            article_title: Title of the article
            contributor_id: ID of the contributor who submitted
            receiver_role: Optional override for the target role
            spring_boot_token: Optional Bearer token for Spring Boot notification

        Returns:
            bool: True if notification sent successfully
        """
        message = f"Article '{article_title}' (by {contributor_id}) is ready for review"
        return self.send_notification(
            article_id=article_id,
            receiver_role=receiver_role or 'EDITOR',
            message=message,
            spring_boot_token=spring_boot_token
        )

    def notify_on_publish(
        self,
        article_id: int,
        article_title: str,
        publisher_id: str,
        receiver_role: Optional[str] = None,
        spring_boot_token: Optional[str] = None
    ) -> bool:
        """
        Notify admins/super admins when an article is PUBLISHED.
        This is called after editor review and publisher approval.

        Args:
            article_id: ID of the article
            article_title: Title of the article
            publisher_id: ID of the publisher
            receiver_role: Optional override for the target role
            spring_boot_token: Optional Bearer token for Spring Boot notification

        Returns:
            bool: True if notification sent successfully
        """
        message = f"Article '{article_title}' has been published by {publisher_id}"
        return self.send_notification(
            article_id=article_id,
            receiver_role=receiver_role or 'ADMIN',
            message=message,
            spring_boot_token=spring_boot_token
        )

    def notify_on_create(
        self,
        article_id: int,
        article_title: str,
        contributor_id: str,
        spring_boot_token: Optional[str] = None
    ) -> bool:
        """
        Notify editors when an article is created by a contributor.

        Args:
            article_id: ID of the article
            article_title: Title of the article (or slug if no title)
            contributor_id: ID of the contributor who created the article
            spring_boot_token: Optional Bearer token for Spring Boot notification

        Returns:
            bool: True if notification sent successfully
        """
        message = f"New article '{article_title}' created by {contributor_id}"
        return self.send_notification(
            article_id=article_id,
            receiver_role='EDITOR',
            message=message,
            spring_boot_token=spring_boot_token
        )

    def notify_on_update(
        self,
        article_id: int,
        article_title: str,
        editor_id: str,
        receiver_role: Optional[str] = None,
        spring_boot_token: Optional[str] = None
    ) -> bool:
        """
        Notify admins when an article is updated/edited.

        Args:
            article_id: ID of the article
            article_title: Title of the article
            editor_id: ID of the editor who updated
            receiver_role: Optional override for the target role
            spring_boot_token: Optional Bearer token for Spring Boot notification

        Returns:
            bool: True if notification sent successfully
        """
        message = f"Article '{article_title}' has been updated by {editor_id}"
        return self.send_notification(
            article_id=article_id,
            receiver_role=receiver_role or 'ADMIN',
            message=message,
            spring_boot_token=spring_boot_token
        )
        
    def notify_on_deactivate(
        self,
        article_id: int,
        article_title: str,
        admin_id: str,
        receiver_role: Optional[str] = None,
        spring_boot_token: Optional[str] = None
    ) -> bool:
        """
        Notify super admins when an article is deactivated.

        Args:
            article_id: ID of the article
            article_title: Title of the article
            admin_id: ID of the admin who deactivated
            receiver_role: Optional override for the target role
            spring_boot_token: Optional Bearer token for Spring Boot notification
        """
        message = f"Article '{article_title}' has been deactivated by {admin_id}"
        return self.send_notification(
            article_id=article_id,
            receiver_role=receiver_role or 'SUPER_ADMIN',
            message=message,
            spring_boot_token=spring_boot_token
        )
        
        
    def notify_on_activate(
        self,
        article_id: int,
        article_title: str,
        admin_id: str,
        receiver_role: Optional[str] = None,
        spring_boot_token: Optional[str] = None
    ) -> bool:
        """
        Notify admins when an article is activated.
        Args:
            article_id: ID of the article
            article_title: Title of the article
            admin_id: ID of the admin who activated
            receiver_role: Optional override for the target role
            spring_boot_token: Optional Bearer token for Spring Boot notification
            """
        message = f"Article '{article_title}' has been activated by {admin_id}"
        return self.send_notification(
            article_id=article_id,
            receiver_role=receiver_role or 'ADMIN',
            message=message,
            spring_boot_token=spring_boot_token
        )
           
    def notify_on_reject(
        self,
        article_id: int,
        article_title: str,
        editor_id: str,
        reason: str,
        receiver_role: Optional[str] = None,
        spring_boot_token: Optional[str] = None
    ) -> bool:
        """
        Notify contributor when an article is rejected during review.

        Args:
            article_id: ID of the article
            article_title: Title of the article
            editor_id: ID of the editor who rejected
            reason: Reason for rejection    
            receiver_role: Optional override for the target role
            spring_boot_token: Optional Bearer token for Spring Boot notification
            """
        message = f"Article '{article_title}' has been rejected by {editor_id}. Reason: {reason}"
        return self.send_notification(
            article_id=article_id,
            receiver_role=receiver_role or 'CONTRIBUTOR',
            message=message,
            spring_boot_token=spring_boot_token
        )

    def notify_on_delete(
        self,
        article_id: int,
        article_title: str,
        admin_id: str,
        receiver_role: Optional[str] = None,
        spring_boot_token: Optional[str] = None
    ) -> bool:
        """
        Notify super admins when an article is deleted.

        Args:
            article_id: ID of the article
            article_title: Title of the article
            admin_id: ID of the admin who deleted
            receiver_role: Optional override for the target role
            spring_boot_token: Optional Bearer token for Spring Boot notification
        """
        message = f"Article '{article_title}' has been deleted by {admin_id}"
        return self.send_notification(
            article_id=article_id,
            receiver_role=receiver_role or 'SUPER_ADMIN',
            message=message,
            spring_boot_token=spring_boot_token
        )
        
        
# Singleton instance
notification_service = SpringBootNotificationService()