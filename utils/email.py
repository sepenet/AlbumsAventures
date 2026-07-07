"""
Module d'envoi d'emails pour AlbumsAventures.
Utilise smtplib (stdlib Python) pour envoyer des emails via SMTP.
Fournisseur SMTP : Nuxit.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from utils.config import email_config, password_reset

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body_html: str) -> bool:
    """Envoie un email via SMTP.

    :param to: adresse email du destinataire
    :param subject: sujet de l'email
    :param body_html: contenu HTML de l'email
    :return: True si l'envoi a réussi, False sinon
    """
    if not email_config.enabled:
        logger.info(f"[EMAIL DÉSACTIVÉ] Destinataire: {to} | Sujet: {subject}")
        logger.info(f"[EMAIL DÉSACTIVÉ] Corps HTML:\n{body_html}")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{email_config.sender_name} <{email_config.sender}>"
    msg["To"] = to

    # Version texte brut (fallback)
    # Extraction simplifiée du texte depuis le HTML
    import re

    text_body = re.sub(r"<[^>]+>", "", body_html)
    text_body = re.sub(r"\s+", " ", text_body).strip()
    msg.attach(MIMEText(text_body, "plain", "utf-8"))

    # Version HTML
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        # Déterminer le mode de sécurité
        security = email_config.smtp_security.lower()
        if security == "auto":
            security = "tls" if email_config.smtp_port == 465 else "starttls"

        if security == "tls":
            # SSL/TLS implicite (port 465) — connexion chiffrée dès le départ
            with smtplib.SMTP_SSL(email_config.smtp_host, email_config.smtp_port, timeout=10) as server:
                server.login(email_config.smtp_user, email_config.smtp_password)
                server.sendmail(email_config.sender, to, msg.as_string())
        else:
            # STARTTLS (port 587) — connexion en clair puis upgrade TLS
            with smtplib.SMTP(email_config.smtp_host, email_config.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(email_config.smtp_user, email_config.smtp_password)
                server.sendmail(email_config.sender, to, msg.as_string())

        logger.info(f"Email envoyé avec succès à {to} — Sujet: {subject}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"Erreur d'authentification SMTP: {e}")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"Erreur SMTP lors de l'envoi à {to}: {e}")
        return False
    except Exception as e:
        logger.error(f"Erreur inattendue lors de l'envoi d'email à {to}: {e}")
        return False


# ─────────────────────────────────────────────────────────────
# Templates d'emails
# ─────────────────────────────────────────────────────────────

_BASE_STYLE = """
<div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto;
     background: #ffffff; border-radius: 12px; overflow: hidden;
     box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
  <div style="background: linear-gradient(135deg, #0ea5e9, #2563eb); padding: 24px 32px;">
    <h1 style="color: #ffffff; margin: 0; font-size: 22px;">🏔️ AlbumsAventures</h1>
  </div>
  <div style="padding: 32px;">
    {content}
  </div>
  <div style="background: #f8fafc; padding: 16px 32px; text-align: center;
       color: #94a3b8; font-size: 12px;">
    Cet email a été envoyé automatiquement par AlbumsAventures.
  </div>
</div>
"""


def send_new_group_access_email(to: str, firstname: str, group_name: str, album_titles: list[str] | None = None):
    """Notifie un utilisateur qu'il a accès à un nouveau groupe.

    :param to: adresse email du destinataire
    :param firstname: prénom de l'utilisateur
    :param group_name: nom du groupe
    :param album_titles: liste optionnelle des titres d'albums du groupe
    """
    albums_section = ""
    if album_titles:
        albums_list = "".join(f"<li>{title}</li>" for title in album_titles[:10])
        more = f"<li><i>… et {len(album_titles) - 10} autres</i></li>" if len(album_titles) > 10 else ""
        albums_section = f"""
        <p style="margin-top: 16px; color: #475569;">Albums disponibles dans ce groupe :</p>
        <ul style="color: #334155;">{albums_list}{more}</ul>
        """

    content = f"""
    <h2 style="color: #1e293b; margin-top: 0;">Bonjour {firstname},</h2>
    <p style="color: #475569; line-height: 1.6;">
      Vous avez maintenant accès au groupe <b style="color: #0ea5e9;">« {group_name} »</b>
      sur AlbumsAventures.
    </p>
    {albums_section}
    <div style="text-align: center; margin: 32px 0;">
      <a href="{password_reset.frontend_url}/"
         style="background: linear-gradient(135deg, #0ea5e9, #2563eb); color: white;
                padding: 12px 32px; text-decoration: none; border-radius: 8px;
                font-weight: 600; display: inline-block;">
        Voir mes albums
      </a>
    </div>
    """
    body = _BASE_STYLE.format(content=content)
    return send_email(to, f"Nouvel accès : groupe « {group_name} »", body)


def send_new_album_access_email(to: str, firstname: str, album_title: str):
    """Notifie un utilisateur qu'il a un accès direct à un nouvel album.

    :param to: adresse email du destinataire
    :param firstname: prénom de l'utilisateur
    :param album_title: titre de l'album
    """
    content = f"""
    <h2 style="color: #1e293b; margin-top: 0;">Bonjour {firstname},</h2>
    <p style="color: #475569; line-height: 1.6;">
      Un nouvel album vous a été partagé : <b style="color: #0ea5e9;">« {album_title} »</b>
    </p>
    <div style="text-align: center; margin: 32px 0;">
      <a href="{password_reset.frontend_url}/"
         style="background: linear-gradient(135deg, #0ea5e9, #2563eb); color: white;
                padding: 12px 32px; text-decoration: none; border-radius: 8px;
                font-weight: 600; display: inline-block;">
        Voir l'album
      </a>
    </div>
    """
    body = _BASE_STYLE.format(content=content)
    return send_email(to, f"Nouvel album partagé : « {album_title} »", body)


def send_password_reset_email(to: str, firstname: str, reset_url: str, expire_minutes: int):
    """Envoie l'email de réinitialisation de mot de passe.

    :param to: adresse email du destinataire
    :param firstname: prénom de l'utilisateur
    :param reset_url: URL complète de réinitialisation (avec token)
    :param expire_minutes: durée de validité du lien en minutes
    """
    content = f"""
    <h2 style="color: #1e293b; margin-top: 0;">Bonjour {firstname},</h2>
    <p style="color: #475569; line-height: 1.6;">
      Vous avez demandé la réinitialisation de votre mot de passe sur AlbumsAventures.
    </p>
    <p style="color: #475569; line-height: 1.6;">
      Cliquez sur le bouton ci-dessous pour définir un nouveau mot de passe.
      Ce lien est valide <b>{expire_minutes} minutes</b>.
    </p>
    <div style="text-align: center; margin: 32px 0;">
      <a href="{reset_url}"
         style="background: linear-gradient(135deg, #0ea5e9, #2563eb); color: white;
                padding: 12px 32px; text-decoration: none; border-radius: 8px;
                font-weight: 600; display: inline-block;">
        Réinitialiser mon mot de passe
      </a>
    </div>
    <p style="color: #94a3b8; font-size: 13px;">
      Si vous n'avez pas fait cette demande, ignorez cet email.
    </p>
    <p style="color: #94a3b8; font-size: 12px; word-break: break-all;">
      Lien direct : {reset_url}
    </p>
    """
    body = _BASE_STYLE.format(content=content)
    return send_email(to, "Réinitialisation de votre mot de passe", body)
