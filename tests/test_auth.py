"""
Tests fonctionnels pour l'authentification (be_auth).
"""

import pytest
from fastapi import status


class TestLogin:
    """Tests pour l'endpoint de login"""

    def test_login_success(self, client, test_user):
        """Test login avec credentials valides"""
        response = client.post(
            "/be_auth/login", data={"username": test_user["email"], "password": test_user["password"]}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert data["message"] == "Connexion réussie"
        assert "user" in data
        assert data["user"]["email"] == test_user["email"]

        # Vérifier que le cookie est défini
        assert "access_token" in response.cookies

    def test_login_invalid_password(self, client, test_user):
        """Test login avec mot de passe incorrect"""
        response = client.post("/be_auth/login", data={"username": test_user["email"], "password": "WrongPassword"})

        # L'API retourne 400 pour mot de passe incorrect
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_nonexistent_user(self, client):
        """Test login avec un email inexistant"""
        response = client.post("/be_auth/login", data={"username": "nonexistent@example.com", "password": "password"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_inactive_user(self, client, db_session):
        """Test login avec un compte non activé
        Note: Actuellement l'API permet le login des utilisateurs inactifs.
        TODO: Implémenter le blocage des utilisateurs inactifs.
        """
        from backend.db import models
        from utils.password import get_password_hash

        # Créer un utilisateur inactif
        user = models.User(
            firstname="Inactive",
            lastname="User",
            email="inactive@example.com",
            password=get_password_hash("Password123"),
            is_active=False,
            is_superuser=False,
        )
        db_session.add(user)
        db_session.commit()

        response = client.post("/be_auth/login", data={"username": "inactive@example.com", "password": "Password123"})

        # L'API accepte actuellement les utilisateurs inactifs (comportement à changer)
        assert response.status_code == status.HTTP_200_OK


class TestAuthentication:
    """Tests pour la vérification d'authentification"""

    def test_access_protected_route_with_token(self, client, auth_headers):
        """Test accès à une route protégée avec token valide"""
        response = client.get("/be_auth/me", cookies=auth_headers["cookies"])

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "email" in data

    def test_access_protected_route_without_token(self, client):
        """Test accès à une route protégée sans token"""
        response = client.get("/be_auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_protected_route_with_invalid_token(self, client):
        """Test accès avec un token invalide"""
        response = client.get("/be_auth/me", cookies={"access_token": "Bearer invalid_token_here"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestSignup:
    """Tests pour l'inscription (endpoint /be_auth/create/)"""

    def test_signup_success(self, client):
        """Test inscription avec données valides"""
        response = client.post(
            "/be_auth/create/",
            json={
                "firstname": "New",
                "lastname": "User",
                "email": "newuser@example.com",
                "password": "SecurePassword123",
                "is_active": False,
                "is_superuser": False,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "newuser@example.com"

    def test_signup_duplicate_email(self, client, test_user):
        """Test inscription avec email déjà existant"""
        response = client.post(
            "/be_auth/create/",
            json={
                "firstname": "Another",
                "lastname": "User",
                "email": test_user["email"],  # Email déjà utilisé
                "password": "SecurePassword123",
                "is_active": False,
                "is_superuser": False,
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestActivateAndAdminEndpoints:
    """Tests SEC-01 : vérification que activate et admin exigent is_superuser"""

    def _get_target_user_id(self, client, superuser_auth_headers) -> int:
        """Crée un utilisateur cible via l'API et retourne son id."""
        resp = client.post(
            "/be_auth/create/",
            json={
                "firstname": "Target",
                "lastname": "User",
                "email": "target_sec01@example.com",
                "password": "TargetPassword123",
                "is_active": False,
                "is_superuser": False,
            },
        )
        assert resp.status_code == status.HTTP_200_OK
        return resp.json()["id"]

    # --- /activate ---

    def test_activate_forbidden_for_normal_user(self, client, test_user, auth_headers, db_session):
        """Un utilisateur standard ne peut pas activer un compte (doit recevoir 403)."""
        from backend.db import models
        from utils.password import get_password_hash

        target = models.User(
            firstname="Target",
            lastname="Sec01",
            email="target_activate@example.com",
            password=get_password_hash("Password123"),
            is_active=False,
            is_superuser=False,
        )
        db_session.add(target)
        db_session.commit()
        db_session.refresh(target)

        response = client.post(
            f"/be_auth/activate/{target.id}/",
            params={"is_active": True},
            cookies=auth_headers["cookies"],
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_activate_allowed_for_superuser(self, client, superuser_auth_headers, db_session):
        """Un superuser peut activer un compte (doit recevoir 200)."""
        from backend.db import models
        from utils.password import get_password_hash

        target = models.User(
            firstname="Target",
            lastname="Sec01",
            email="target_activate_su@example.com",
            password=get_password_hash("Password123"),
            is_active=False,
            is_superuser=False,
        )
        db_session.add(target)
        db_session.commit()
        db_session.refresh(target)

        response = client.post(
            f"/be_auth/activate/{target.id}/",
            params={"is_active": True},
            cookies=superuser_auth_headers["cookies"],
        )
        assert response.status_code == status.HTTP_200_OK

    def test_activate_forbidden_for_unauthenticated(self, client, db_session):
        """Un appel sans cookie doit recevoir 401."""
        from backend.db import models
        from utils.password import get_password_hash

        target = models.User(
            firstname="Target",
            lastname="Sec01",
            email="target_activate_anon@example.com",
            password=get_password_hash("Password123"),
            is_active=False,
            is_superuser=False,
        )
        db_session.add(target)
        db_session.commit()
        db_session.refresh(target)

        response = client.post(f"/be_auth/activate/{target.id}/", params={"is_active": True})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # --- /admin ---

    def test_promote_admin_forbidden_for_normal_user(self, client, auth_headers, db_session):
        """Un utilisateur standard ne peut pas promouvoir un compte admin (doit recevoir 403)."""
        from backend.db import models
        from utils.password import get_password_hash

        target = models.User(
            firstname="Target",
            lastname="Sec01",
            email="target_admin@example.com",
            password=get_password_hash("Password123"),
            is_active=True,
            is_superuser=False,
        )
        db_session.add(target)
        db_session.commit()
        db_session.refresh(target)

        response = client.post(
            f"/be_auth/admin/{target.id}/",
            params={"is_superuser": True},
            cookies=auth_headers["cookies"],
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_promote_admin_allowed_for_superuser(self, client, superuser_auth_headers, db_session):
        """Un superuser peut promouvoir un compte admin (doit recevoir 200)."""
        from backend.db import models
        from utils.password import get_password_hash

        target = models.User(
            firstname="Target",
            lastname="Sec01",
            email="target_admin_su@example.com",
            password=get_password_hash("Password123"),
            is_active=True,
            is_superuser=False,
        )
        db_session.add(target)
        db_session.commit()
        db_session.refresh(target)

        response = client.post(
            f"/be_auth/admin/{target.id}/",
            params={"is_superuser": True},
            cookies=superuser_auth_headers["cookies"],
        )
        assert response.status_code == status.HTTP_200_OK

    def test_promote_admin_forbidden_for_unauthenticated(self, client, db_session):
        """Un appel sans cookie doit recevoir 401."""
        from backend.db import models
        from utils.password import get_password_hash

        target = models.User(
            firstname="Target",
            lastname="Sec01",
            email="target_admin_anon@example.com",
            password=get_password_hash("Password123"),
            is_active=True,
            is_superuser=False,
        )
        db_session.add(target)
        db_session.commit()
        db_session.refresh(target)

        response = client.post(f"/be_auth/admin/{target.id}/", params={"is_superuser": True})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPasswordReset:
    """Tests pour la réinitialisation de mot de passe"""

    def test_forgot_password_existing_email(self, client, test_user):
        """Test demande de reset pour email existant"""
        response = client.post("/be_auth/forgot-password", json={"email": test_user["email"]})

        # Doit toujours retourner 200 pour ne pas révéler si l'email existe
        assert response.status_code == status.HTTP_200_OK

    def test_forgot_password_nonexistent_email(self, client):
        """Test demande de reset pour email inexistant"""
        response = client.post("/be_auth/forgot-password", json={"email": "nonexistent@example.com"})

        # Doit toujours retourner 200 (sécurité)
        assert response.status_code == status.HTTP_200_OK

    def test_reset_password_invalid_token(self, client):
        """Test reset avec token invalide"""
        response = client.post(
            "/be_auth/reset-password", json={"token": "invalid_token", "new_password": "NewSecurePassword123"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestJWTAlgorithmConfinement:
    """SEC (condition 2) : le décodage JWT est épinglé à HS256.

    Rejette explicitement ``alg: none`` (token non signé) et toute confusion
    d'algorithme (ex. token signé HS512), sur le helper ``decode_token`` comme
    sur un endpoint protégé.
    """

    @staticmethod
    def _payload() -> dict:
        from datetime import UTC, datetime, timedelta

        # ``exp`` en epoch (int) pour une sérialisation JSON directe (token forgé).
        exp = int((datetime.now(UTC) + timedelta(hours=1)).timestamp())
        return {"sub": "attacker@example.com", "id": 1, "exp": exp}

    @staticmethod
    def _make_alg_none_token(payload: dict) -> str:
        """Forge un JWT non signé (``alg: none``) sans dépendre de l'encodeur jose."""
        import base64
        import json

        def _b64url(data: dict) -> str:
            raw = json.dumps(data, separators=(",", ":")).encode()
            return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

        header = {"alg": "none", "typ": "JWT"}
        # Signature vide : la forme d'un token non signé.
        return f"{_b64url(header)}.{_b64url(payload)}."

    def test_decode_token_rejects_alg_none(self):
        """Un token non signé (``alg: none``) doit être rejeté par decode_token."""
        from jose.exceptions import JWTError

        from backend.routers.be_auth import decode_token

        none_token = self._make_alg_none_token(self._payload())
        with pytest.raises(JWTError):
            decode_token(none_token)

    def test_decode_token_rejects_wrong_algorithm(self):
        """Un token signé avec un autre algorithme (HS512) doit être rejeté."""
        from jose import jwt
        from jose.exceptions import JWTError

        from backend.routers.be_auth import SECRET_KEY, decode_token

        wrong_alg_token = jwt.encode(self._payload(), SECRET_KEY, algorithm="HS512")
        with pytest.raises(JWTError):
            decode_token(wrong_alg_token)

    def test_protected_route_rejects_alg_none_token(self, client):
        """L'endpoint protégé ``/be_auth/me`` doit renvoyer 401 pour un token alg:none."""
        none_token = self._make_alg_none_token(self._payload())
        response = client.get("/be_auth/me", cookies={"access_token": f"Bearer {none_token}"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestSecurityHeaders:
    """H-3 (conditions 3/4/7) : la CSP et les en-têtes de sécurité sont émis.

    Vérifie que le middleware ``SecurityHeadersMiddleware`` (câblé via
    ``configure_security``) pose bien la CSP et les en-têtes clés sur les réponses.
    Couvre le durcissement Phase 3.9 (CSP à deux niveaux : repli Jinja vs SPA).
    """

    def test_security_headers_present_on_response(self, client):
        """Une réponse porte la CSP + nosniff + protection frame + referrer-policy."""
        # 401 attendu sans token : les en-têtes middleware sont posés quel que soit le statut.
        response = client.get("/be_auth/me")

        assert "Content-Security-Policy" in response.headers
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "object-src 'none'" in csp

        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "Permissions-Policy" in response.headers

    def test_csp_never_allows_unsafe_eval_or_wildcard(self, client):
        """Invariant durcissement 3.9 : jamais 'unsafe-eval' ni source large '*'.

        S'applique à la CSP de repli Jinja (route API / non-/app).
        """
        csp = client.get("/be_auth/me").headers["Content-Security-Policy"]

        # 'unsafe-eval' est interdit sur toute surface (aucun eval() côté client).
        assert "'unsafe-eval'" not in csp
        # Aucune directive ne doit contenir une source large '*' (fetch/img/script...).
        for directive in csp.split(";"):
            tokens = directive.strip().split()
            assert "*" not in tokens, f"source large '*' interdite dans : {directive.strip()!r}"

    def test_csp_has_no_cdn_after_jinja_decommission(self, client):
        """Après le décommissionnement Jinja, AUCUN CDN ne figure dans la CSP.

        La politique applicative est désormais UNIQUE et durcie sur toute la surface
        (SPA + API) : ``script-src 'self'`` seul, sans aucun hôte CDN. Seul
        ``style-src`` conserve le ``'unsafe-inline'`` résiduel (styles runtime).
        """
        csp = client.get("/be_auth/me").headers["Content-Security-Policy"]

        # Les CDN de l'ancienne couche Jinja ont disparu de la CSP.
        assert "https://cdn.tailwindcss.com" not in csp
        assert "https://unpkg.com" not in csp
        assert "https://releases.transloadit.com" not in csp

        # script-src est durci à 'self' seul (aucun CDN, aucun inline).
        script_src = next(
            (d.strip() for d in csp.split(";") if d.strip().startswith("script-src")),
            "",
        )
        assert script_src == "script-src 'self'", f"script-src non durci : {script_src!r}"

        # Le 'unsafe-inline' résiduel subsiste UNIQUEMENT sur style-src.
        assert "'unsafe-inline'" in csp
        # Pas d'allocation de schéma large ni de wildcard d'hôte.
        assert "https:*" not in csp
        assert "https://*" not in csp

    def test_spa_csp_is_tightened_same_origin_only(self, client):
        """La surface SPA ``/app`` reçoit la CSP DURCIE : script-src 'self', aucun CDN.

        Le shell buildé ne charge que des assets same-origin hachés ; ``script-src``
        n'autorise donc ni CDN ni ``'unsafe-inline'``. Le middleware pose la CSP quelle
        que soit la présence du build (404 si ``dist`` absent, en-tête tout de même posé).
        """
        response = client.get("/app")
        csp = response.headers["Content-Security-Policy"]

        # Isole la directive script-src pour des assertions précises.
        script_src = next(
            (d.strip() for d in csp.split(";") if d.strip().startswith("script-src")),
            "",
        )
        assert script_src == "script-src 'self'", f"script-src SPA non durci : {script_src!r}"

        # Aucun CDN ni 'unsafe-inline'/'unsafe-eval' dans la politique SPA.
        assert "https://cdn.tailwindcss.com" not in csp
        assert "https://unpkg.com" not in csp
        assert "https://releases.transloadit.com" not in csp
        assert "'unsafe-eval'" not in csp
        # Directives same-origin déjà prêtes pour la PWA Phase 4.
        assert "worker-src 'self' blob:" in csp
        assert "manifest-src 'self'" in csp
        # Aucune source large.
        for directive in csp.split(";"):
            assert "*" not in directive.strip().split()


class TestDurableRateLimit:
    """M-2 (condition 6) : le rate limiting est durable, persisté en base.

    Le lockout survit dans ``rate_limit_entries`` (aucun identifiant en clair) et
    est visible depuis une autre session DB (partage inter-workers).
    """

    def test_lockout_after_max_attempts_persists_in_db(self, db_session):
        """Après ``max_attempts`` échecs, la clé est bloquée (429) et persistée."""
        from fastapi import HTTPException

        from backend.db.models import RateLimitEntry
        from utils.config import rate_limiting
        from utils.rate_limit import check_rate_limit, record_failed_attempt

        key = "login:ratelimit_test@example.com"

        for _ in range(rate_limiting.max_attempts):
            record_failed_attempt(db_session, key)

        # L'entrée est persistée en base, avec une clé hashée (jamais l'email en clair).
        entries = db_session.query(RateLimitEntry).all()
        assert len(entries) == 1
        assert entries[0].key_hash != key
        assert entries[0].attempts >= rate_limiting.max_attempts

        # La clé est désormais bloquée : check_rate_limit lève une 429.
        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(db_session, key)
        assert exc_info.value.status_code == 429

    def test_lockout_survives_session_cache_flush(self, db_session):
        """Le blocage est relu depuis la base (durable), pas seulement du cache session.

        On expire l'identity map SQLAlchemy pour forcer une relecture depuis le
        store DB : le blocage doit persister (429), prouvant la durabilité.
        """
        from fastapi import HTTPException

        from backend.db.models import RateLimitEntry
        from utils.config import rate_limiting
        from utils.rate_limit import check_rate_limit, record_failed_attempt

        key = "pin:share_lockout_test"

        for _ in range(rate_limiting.max_attempts):
            record_failed_attempt(db_session, key)

        # Vider le cache d'identité : la prochaine lecture vient réellement de la DB.
        db_session.expire_all()
        reloaded = db_session.query(RateLimitEntry).all()
        assert len(reloaded) == 1
        assert reloaded[0].blocked_until > 0

        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(db_session, key)
        assert exc_info.value.status_code == 429


class TestGroupMutationSuperuserGate:
    """FU-group (OWASP A01) : les mutations ``be_group`` sont réservées aux admins.

    Les endpoints ``be_group`` qui MODIFIENT l'état (create/update/delete,
    gestion des membres et des albums) étaient authentifiés mais non protégés
    côté serveur par une garde superuser — la restriction n'existait que dans
    l'UI Jinja (masquage des boutons). Le correctif ajoute
    ``Depends(require_superuser)`` au niveau de la route : un utilisateur
    authentifié mais non-administrateur reçoit désormais un 403, tandis qu'un
    superuser réussit. On exerce la mutation représentative ``create_group``.
    """

    def test_create_group_forbidden_for_normal_user(self, client, auth_headers):
        """Un utilisateur authentifié non-admin reçoit 403 (garde côté serveur)."""
        response = client.post(
            "/be_group/create_group/",
            json={"name": "Groupe non-admin", "description": "tentative interdite"},
            cookies=auth_headers["cookies"],
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_group_allowed_for_superuser(self, client, superuser_auth_headers):
        """Un superuser peut créer un groupe (mutation autorisée)."""
        response = client.post(
            "/be_group/create_group/",
            json={"name": "Groupe admin", "description": "création autorisée"},
            cookies=superuser_auth_headers["cookies"],
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Groupe admin"

    def test_create_group_forbidden_for_unauthenticated(self, client):
        """Sans session, la mutation est refusée (401)."""
        response = client.post(
            "/be_group/create_group/",
            json={"name": "Groupe anonyme", "description": "sans session"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_group_forbidden_for_normal_user(self, client, auth_headers, test_group):
        """La suppression d'un groupe est aussi refusée (403) à un non-admin."""
        response = client.delete(
            f"/be_group/delete_group/{test_group['id']}",
            cookies=auth_headers["cookies"],
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
