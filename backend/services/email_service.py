# backend/services/email_service.py
"""
Email service for sending verification and password reset emails.
Uses SendGrid for reliable email delivery.
"""
from __future__ import annotations
import os
import logging
from typing import Optional
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from pathlib import Path

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SendGrid."""
    
    def __init__(self):
        self.api_key = os.getenv("SENDGRID_API_KEY")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@yourdomain.com")
        self.from_name = os.getenv("FROM_NAME", "AI Document Search")
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        
        # Check if email is enabled
        self.enabled = bool(self.api_key and self.api_key != "your-sendgrid-api-key")
        
        if self.enabled:
            self.client = SendGridAPIClient(self.api_key)
            logger.info("Email service initialized with SendGrid")
        else:
            logger.warning("Email service disabled - no valid SENDGRID_API_KEY found")
    
    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """
        Send an email using SendGrid.
        
        Returns True if successful, False otherwise.
        """
        if not self.enabled:
            logger.warning(f"Email sending skipped (disabled): {subject} to {to_email}")
            return False
        
        try:
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            response = self.client.send(message)
            
            if response.status_code in (200, 201, 202):
                logger.info(f"Email sent successfully: {subject} to {to_email}")
                return True
            else:
                logger.error(f"Email failed with status {response.status_code}: {subject}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def send_verification_email(self, to_email: str, username: str, token: str) -> bool:
        """
        Send email verification link to user.
        
        Args:
            to_email: Recipient email address
            username: User's username
            token: Verification token
            
        Returns:
            True if email was sent successfully
        """
        verification_url = f"{self.frontend_url}/verify-email?token={token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .container {{
                    background: linear-gradient(to bottom right, #fef3c7, #ffffff, #fed7aa);
                    border-radius: 10px;
                    padding: 40px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    color: #d97706;
                    margin: 0;
                    font-size: 28px;
                }}
                .content {{
                    background: white;
                    border-radius: 8px;
                    padding: 30px;
                    margin: 20px 0;
                }}
                .button {{
                    display: inline-block;
                    background: linear-gradient(to right, #f59e0b, #d97706);
                    color: white;
                    padding: 14px 32px;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: 600;
                    margin: 20px 0;
                }}
                .button:hover {{
                    background: linear-gradient(to right, #d97706, #b45309);
                }}
                .footer {{
                    text-align: center;
                    color: #666;
                    font-size: 14px;
                    margin-top: 30px;
                }}
                .code {{
                    background: #f3f4f6;
                    padding: 12px;
                    border-radius: 4px;
                    font-family: 'Courier New', monospace;
                    font-size: 14px;
                    word-break: break-all;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Verify Your Email</h1>
                </div>
                
                <div class="content">
                    <p>Hi <strong>{username}</strong>,</p>
                    
                    <p>Welcome to <strong>AI Document Search</strong>! 🎉</p>
                    
                    <p>To complete your registration and start chatting with your documents, please verify your email address by clicking the button below:</p>
                    
                    <center>
                        <a href="{verification_url}" class="button">Verify Email Address</a>
                    </center>
                    
                    <p>Or copy and paste this link into your browser:</p>
                    <div class="code">{verification_url}</div>
                    
                    <p><strong>Note:</strong> This link will expire in 24 hours for security reasons.</p>
                    
                    <p>If you didn't create an account, you can safely ignore this email.</p>
                </div>
                
                <div class="footer">
                    <p>© 2025 AI Document Search. All rights reserved.</p>
                    <p>This is an automated email, please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(
            to_email=to_email,
            subject="Verify your email address",
            html_content=html_content
        )
    
    def send_password_reset_email(self, to_email: str, username: str, token: str) -> bool:
        """
        Send password reset link to user.
        
        Args:
            to_email: Recipient email address
            username: User's username
            token: Password reset token
            
        Returns:
            True if email was sent successfully
        """
        reset_url = f"{self.frontend_url}/reset-password?token={token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .container {{
                    background: linear-gradient(to bottom right, #fef3c7, #ffffff, #fed7aa);
                    border-radius: 10px;
                    padding: 40px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    color: #d97706;
                    margin: 0;
                    font-size: 28px;
                }}
                .content {{
                    background: white;
                    border-radius: 8px;
                    padding: 30px;
                    margin: 20px 0;
                }}
                .button {{
                    display: inline-block;
                    background: linear-gradient(to right, #f59e0b, #d97706);
                    color: white;
                    padding: 14px 32px;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: 600;
                    margin: 20px 0;
                }}
                .button:hover {{
                    background: linear-gradient(to right, #d97706, #b45309);
                }}
                .footer {{
                    text-align: center;
                    color: #666;
                    font-size: 14px;
                    margin-top: 30px;
                }}
                .code {{
                    background: #f3f4f6;
                    padding: 12px;
                    border-radius: 4px;
                    font-family: 'Courier New', monospace;
                    font-size: 14px;
                    word-break: break-all;
                    margin: 10px 0;
                }}
                .warning {{
                    background: #fef3c7;
                    border-left: 4px solid #f59e0b;
                    padding: 12px;
                    margin: 15px 0;
                    border-radius: 4px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔑 Reset Your Password</h1>
                </div>
                
                <div class="content">
                    <p>Hi <strong>{username}</strong>,</p>
                    
                    <p>We received a request to reset your password for your <strong>AI Document Search</strong> account.</p>
                    
                    <p>Click the button below to create a new password:</p>
                    
                    <center>
                        <a href="{reset_url}" class="button">Reset Password</a>
                    </center>
                    
                    <p>Or copy and paste this link into your browser:</p>
                    <div class="code">{reset_url}</div>
                    
                    <div class="warning">
                        <strong>⚠️ Security Notice:</strong>
                        <ul style="margin: 5px 0;">
                            <li>This link expires in 1 hour</li>
                            <li>If you didn't request this, ignore this email</li>
                            <li>Your password remains unchanged until you reset it</li>
                        </ul>
                    </div>
                    
                    <p>For security reasons, we cannot tell you your current password. You'll need to create a new one.</p>
                </div>
                
                <div class="footer">
                    <p>© 2025 AI Document Search. All rights reserved.</p>
                    <p>This is an automated email, please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(
            to_email=to_email,
            subject="Reset your password",
            html_content=html_content
        )
    
    def send_welcome_email(self, to_email: str, username: str) -> bool:
        """
        Send welcome email after successful verification.
        
        Args:
            to_email: Recipient email address
            username: User's username
            
        Returns:
            True if email was sent successfully
        """
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .container {{
                    background: linear-gradient(to bottom right, #fef3c7, #ffffff, #fed7aa);
                    border-radius: 10px;
                    padding: 40px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    color: #d97706;
                    margin: 0;
                    font-size: 28px;
                }}
                .content {{
                    background: white;
                    border-radius: 8px;
                    padding: 30px;
                    margin: 20px 0;
                }}
                .button {{
                    display: inline-block;
                    background: linear-gradient(to right, #f59e0b, #d97706);
                    color: white;
                    padding: 14px 32px;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: 600;
                    margin: 20px 0;
                }}
                .feature {{
                    margin: 15px 0;
                    padding-left: 30px;
                }}
                .footer {{
                    text-align: center;
                    color: #666;
                    font-size: 14px;
                    margin-top: 30px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome to AI Document Search!</h1>
                </div>
                
                <div class="content">
                    <p>Hi <strong>{username}</strong>,</p>
                    
                    <p>Your email has been verified successfully! You're all set to start using AI Document Search.</p>
                    
                    <h3>What you can do now:</h3>
                    
                    <div class="feature">📄 <strong>Upload PDFs</strong> - Upload any PDF document</div>
                    <div class="feature">💬 <strong>Chat with your documents</strong> - Ask questions and get instant answers</div>
                    <div class="feature">🔍 <strong>Smart search</strong> - Find information across all your documents</div>
                    <div class="feature">📚 <strong>Organize your library</strong> - Manage multiple PDFs easily</div>
                    
                    <center>
                        <a href="{self.frontend_url}" class="button">Get Started</a>
                    </center>
                    
                    <p>If you have any questions or need help, feel free to reach out!</p>
                </div>
                
                <div class="footer">
                    <p>© 2025 AI Document Search. All rights reserved.</p>
                    <p>Happy document searching! 📖✨</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(
            to_email=to_email,
            subject="Welcome to AI Document Search! 🎉",
            html_content=html_content
        )


# Global email service instance
_email_service: Optional[EmailService] = None

def get_email_service() -> EmailService:
    """Get the global email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service

