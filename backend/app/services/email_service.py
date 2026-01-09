# Copyright (c) 2024 RackPlane <info@rackplane.com>
# Version: 1.0.0

"""
Email Service
Handles sending emails via SendGrid or SMTP

Supports multiple backends:
- SendGrid (recommended for production)
- SMTP (for development or self-hosted)
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings
from app.core.templates import render_template

logger = logging.getLogger(__name__)


class EmailBackend(ABC):
    """Abstract base class for email backends"""
    
    @abstractmethod
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None
    ) -> bool:
        """Send an email"""
        pass


class SendGridBackend(EmailBackend):
    """SendGrid email backend"""
    
    def __init__(self, api_key: str, from_email: str):
        self.api_key = api_key
        self.from_email = from_email
        self._client = None
    
    def _get_client(self):
        """Lazy load SendGrid client"""
        if self._client is None:
            try:
                import sendgrid
                from sendgrid.helpers.mail import Mail
                self.sendgrid = sendgrid
                self.Mail = Mail
                self._client = sendgrid.SendGridAPIClient(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "sendgrid package not installed. Install with: pip install sendgrid"
                )
        return self._client
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None
    ) -> bool:
        """Send email via SendGrid"""
        try:
            client = self._get_client()
            from_addr = from_email or self.from_email
            
            message = self.Mail(
                from_email=from_addr,
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            
            if text_content:
                message.plain_text_content = text_content
            
            response = client.send(message)
            
            if response.status_code in [200, 202]:
                logger.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"SendGrid error: {response.status_code} - {response.body}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email via SendGrid: {e}")
            return False


class SMTPBackend(EmailBackend):
    """SMTP email backend for self-hosted or development"""
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: str,
        use_tls: bool = True
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.use_tls = use_tls
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None
    ) -> bool:
        """Send email via SMTP"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_email or self.from_email
            msg['To'] = to_email
            
            # Add text and HTML parts
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email} via SMTP")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email via SMTP: {e}")
            return False



class SyncEmailService:
    """
    Synchronous Email Service (Internal Use Only)
    
    This service performs the actual network I/O to send emails.
    It should NOT be used directly by API endpoints to avoid blocking the event loop.
    Use EmailService (the facade) instead, or call this from background tasks.
    """
    
    def __init__(self):
        self.backend = self._create_backend()
        self.from_email = self._get_from_email()
    
    def _create_backend(self) -> EmailBackend:
        """Create email backend based on configuration"""
        email_provider = getattr(settings, 'EMAIL_PROVIDER', 'sendgrid').lower()
        
        if email_provider == 'sendgrid':
            api_key = getattr(settings, 'SENDGRID_API_KEY', '')
            if not api_key:
                logger.warning("SENDGRID_API_KEY not set, falling back to SMTP")
                return self._create_smtp_backend()
            return SendGridBackend(
                api_key=api_key,
                from_email=getattr(settings, 'FROM_EMAIL', 'alerts@rackplane.com')
            )
        else:
            return self._create_smtp_backend()
    
    def _create_smtp_backend(self) -> SMTPBackend:
        """Create SMTP backend from settings"""
        return SMTPBackend(
            smtp_host=getattr(settings, 'SMTP_HOST', 'localhost'),
            smtp_port=int(getattr(settings, 'SMTP_PORT', '587')),
            smtp_user=getattr(settings, 'SMTP_USER', ''),
            smtp_password=getattr(settings, 'SMTP_PASSWORD', ''),
            from_email=getattr(settings, 'FROM_EMAIL', 'alerts@rackplane.com'),
            use_tls=getattr(settings, 'SMTP_USE_TLS', True)
        )
    
    def _get_from_email(self) -> str:
        """Get from email address"""
        return getattr(settings, 'FROM_EMAIL', 'alerts@rackplane.com')
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send an email synchronously"""
        return self.backend.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            from_email=self.from_email
        )
    
    def send_low_stock_alert(
        self,
        to_email: str,
        container_name: str,
        item_type: str,
        current_count: int,
        threshold: int,
        container_id: Optional[int] = None,
        low_stock_types: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Send low stock alert email"""
        subject = f"Low Stock Alert: {item_type} in {container_name}"
        
        # Build context
        app_url = getattr(settings, 'APP_URL', 'https://app.rackplane.com')
        action_url = f"{app_url}/storage-containers/{container_id}" if container_id else None
        
        context = {
            'title': '⚠️ Low Stock Alert',
            'container_name': container_name,
            'item_type': item_type,
            'current_count': current_count,
            'threshold': threshold,
            'container_id': container_id,
            'action_url': action_url,
            'action_text': 'View Container',
            'header_color': '#f59e0b', # Amber/Orange for warning
            'low_stock_types': low_stock_types
        }
        
        html_content = render_template('email/low_stock_alert.html', context)
        
        text_content = f"""
Low Stock Alert

{container_name} is running low on {item_type}.

Current Stock: {current_count}
Minimum Threshold: {threshold}

It's time to reorder {item_type} for {container_name}.
"""
        if low_stock_types:
            text_content += "\nSpecific Items Low on Stock:\n"
            for item in low_stock_types:
                manufacturer = item.get('manufacturer', '')
                model = item.get('model', '')
                count = item.get('count', 0)
                text_content += f"- {manufacturer} {model} ({count})\n"

        if action_url:
            text_content += f"\nView Container: {action_url}"
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_maintenance_due_alert(
        self,
        to_email: str,
        asset_tag: str,
        maintenance_type: str,
        scheduled_date: str,
        asset_id: Optional[int] = None,
        description: Optional[str] = None
    ) -> bool:
        """Send maintenance due alert email"""
        subject = f"Maintenance Due: {asset_tag} - {maintenance_type}"
        
        app_url = getattr(settings, 'APP_URL', 'https://app.rackplane.com')
        action_url = f"{app_url}/assets/{asset_id}" if asset_id else None
        
        context = {
            'title': '🔧 Maintenance Due',
            'asset_tag': asset_tag,
            'maintenance_type': maintenance_type,
            'scheduled_date': scheduled_date,
            'description': description,
            'action_url': action_url,
            'action_text': 'View Asset',
            'header_color': '#2563eb' # Blue
        }
        
        html_content = render_template('email/maintenance_due.html', context)
        
        text_content = f"""
Maintenance Due Alert

{asset_tag} requires {maintenance_type} maintenance.

Scheduled Date: {scheduled_date}
"""
        if description:
            text_content += f"\nNotes:\n{description}\n"
            
        if action_url:
            text_content += f"\nView Asset: {action_url}"
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_warranty_expiring_alert(
        self,
        to_email: str,
        asset_tag: str,
        warranty_expiry: str,
        days_remaining: int,
        asset_id: Optional[int] = None
    ) -> bool:
        """Send warranty expiring alert email"""
        subject = f"Warranty Expiring Soon: {asset_tag}"
        
        app_url = getattr(settings, 'APP_URL', 'https://app.rackplane.com')
        action_url = f"{app_url}/assets/{asset_id}" if asset_id else None
        
        context = {
            'title': '⚠️ Warranty Expiring Soon',
            'asset_tag': asset_tag,
            'warranty_expiry': warranty_expiry,
            'days_remaining': days_remaining,
            'action_url': action_url,
            'action_text': 'View Asset',
            'header_color': '#ef4444' # Red
        }
        
        html_content = render_template('email/warranty_expiring.html', context)
        
        text_content = f"""
Warranty Expiring Alert

{asset_tag} warranty expires in {days_remaining} days.

Warranty Expiry Date: {warranty_expiry}

Please review the asset status and consider extending coverage or planning for replacement if necessary.
"""
        if action_url:
            text_content += f"\nView Asset: {action_url}"
        
        return self.send_email(to_email, subject, html_content, text_content)


class EmailService(SyncEmailService):
    """
    Async-First Email Service Facade
    
    This service handles email formatting logic locally but dispatches the actual
    sending to a background Celery task. This prevents API blocking.
    Inherits formatting methods from SyncEmailService.
    """
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Dispatch email sending to background task.
        Returns True immediately if task is queued.
        """
        try:
            # Import task lazily to avoid circular imports
            from app.tasks.email import send_email_task
            
            # Dispatch to Celery
            send_email_task.delay(
                to_email=to_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            return True
        except Exception as e:
            # Fallback to synchronous sending if Celery fails (e.g. during development/testing without worker)
            logger.warning(f"Failed to queue email task, falling back to sync: {e}")
            return super().send_email(to_email, subject, html_content, text_content)


# Global email service instance
_sync_email_service: Optional[SyncEmailService] = None
_email_service: Optional[EmailService] = None

def get_sync_email_service() -> SyncEmailService:
    """Get or create synchronous email service (internal use)"""
    global _sync_email_service
    if _sync_email_service is None:
        _sync_email_service = SyncEmailService()
    return _sync_email_service

def get_email_service() -> EmailService:
    """Get or create async email service (public use)"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service



