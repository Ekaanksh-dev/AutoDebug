# AutoDebug — Multi-Agent Bug Fixing System
# Copyright 2026 Ekaanksh (github.com/Ekaanksh-dev)
# Licensed under Apache License 2.0

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from rich.console import Console
from core.context import BugContext
from notifier.formatter import format_email_subject, format_email_body

load_dotenv()
console = Console()


def send_email(ctx: BugContext) -> bool:
    """
    Send bug report email via Gmail SMTP.
    Same approach as DevOps AI Notifier.
    """

    sender   = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    receiver = os.getenv("EMAIL_RECEIVER")

    if not all([sender, password, receiver]):
        console.print("[red]❌ Missing email config in .env[/red]")
        return False

    try:
        # Build email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = format_email_subject(ctx)
        msg["From"]    = f"AutoDebug Bot <{sender}>"
        msg["To"]      = receiver

        # Plain text body
        body = format_email_body(ctx)
        msg.attach(MIMEText(body, "plain"))

        # Send via Gmail SMTP
        console.print("[yellow]📧 Sending email...[/yellow]")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())

        console.print(f"[green]✅ Email sent to {receiver}![/green]")
        return True

    except smtplib.SMTPAuthenticationError:
        console.print("[red]❌ Gmail auth failed — check EMAIL_PASSWORD in .env[/red]")
        console.print("[dim]Tip: Use Gmail App Password, not your real password[/dim]")
        return False

    except Exception as e:
        console.print(f"[red]❌ Email error: {e}[/red]")
        return False


def send_test_email() -> bool:
    """Send a test email to verify config is correct"""

    sender   = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    receiver = os.getenv("EMAIL_RECEIVER")

    try:
        msg = MIMEMultipart()
        msg["Subject"] = "✅ AutoDebug — Email Config Working!"
        msg["From"]    = f"AutoDebug Bot <{sender}>"
        msg["To"]      = receiver

        body = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 AutoDebug Test Email
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Your email config is working correctly!

AutoDebug is ready to send bug reports
to this email whenever a bug is detected.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Powered by AutoDebug
github.com/Ekaanksh-dev/AutoDebug
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())

        console.print("[green]✅ Test email sent successfully![/green]")
        return True

    except Exception as e:
        console.print(f"[red]❌ Test email failed: {e}[/red]")
        return False
