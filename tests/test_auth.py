"""
Tests fonctionnels pour l'authentification (be_auth).
"""

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
