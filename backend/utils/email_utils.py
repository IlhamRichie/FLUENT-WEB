from flask import current_app, render_template, url_for
from flask_mail import Message # Impor Message dari flask_mail
from backend import mail # Impor instance mail yang sudah diinisialisasi

def send_otp_email(recipient_email: str, otp_code: str):
    try:
        msg_subject = "Your OTP Verification Code - FLUENT"
        # Path template relatif dari folder 'templates'
        html_body = render_template("email/email_otp_template.html",
                                    otp=otp_code,
                                    app_name="FLUENT",
                                    config=current_app.config)
        msg = Message(subject=msg_subject,
                      recipients=[recipient_email],
                      html=html_body,
                      sender=current_app.config.get('MAIL_DEFAULT_SENDER')) # Tambahkan sender
        mail.send(msg)
        current_app.logger.info(f"OTP email successfully sent to {recipient_email}")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send OTP email to {recipient_email}: {e}", exc_info=True)
        return False

def send_reset_password_email(recipient_email: str, reset_token: str):
    try:
        # Pastikan route 'web.web_reset_password_form_route' ada dan benar
        reset_url = url_for('web.web_reset_password_form_route', token=reset_token, _external=True)
        msg_subject = "Your Password Reset Link - FLUENT"
        html_body = render_template("email/email_reset_password_template.html",
                                    reset_url=reset_url,
                                    app_name="FLUENT",
                                    config=current_app.config)
        msg = Message(subject=msg_subject,
                      recipients=[recipient_email],
                      html=html_body,
                      sender=current_app.config.get('MAIL_DEFAULT_SENDER')) # Tambahkan sender
        mail.send(msg)
        current_app.logger.info(f"Password reset email successfully sent to {recipient_email}")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send password reset email to {recipient_email}: {e}", exc_info=True)
        return False