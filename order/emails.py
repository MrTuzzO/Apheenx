import threading
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class EmailThread(threading.Thread):
    def __init__(self, subject, message, recipient_list):
        self.subject = subject
        self.message = message
        self.recipient_list = recipient_list
        threading.Thread.__init__(self)

    def run(self):
        try:
            send_mail(
                subject=self.subject,
                message=self.message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=self.recipient_list,
                fail_silently=False,
            )
            logger.info(f"Async email sent to {self.recipient_list}")
        except Exception as e:
            logger.error(f"Failed to send async email: {e}")

def send_admin_order_notification(order_id):
    subject = f"New Product Order Paid: #{order_id}"
    message = f"A product order has been successfully placed and payment captured.\n\nOrder ID: {order_id}\n\nPlease check the admin panel for details."
    
    # Send from DEFAULT_FROM_EMAIL to DEFAULT_FROM_EMAIL (admin)
    admin_email = settings.DEFAULT_FROM_EMAIL
    
    EmailThread(subject, message, [admin_email]).start()
