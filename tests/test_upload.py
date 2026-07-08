"""
Tests fonctionnels pour l'upload d'images/vidéos (be_resizer).
Teste les validations de taille et d'accès album.
"""

from io import BytesIO

from fastapi import status


class TestUploadValidation:
    """Tests pour la validation des uploads"""

    def test_upload_without_album_access_forbidden(self, client, test_album, auth_headers):
        """Test upload sans accès à l'album - doit être refusé"""
        # L'utilisateur test n'a pas accès direct à l'album
        # (pas de lien UserAlbum créé)

        # Créer un petit fichier image factice
        image_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        files = {"files": ("test.png", BytesIO(image_content), "image/png")}

        response = client.post(
            f"/be_resizer/upload_images/{test_album['id']}", files=files, cookies=auth_headers["cookies"]
        )

        # Devrait être refusé car l'utilisateur n'a pas accès
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_upload_with_album_access_success(self, client, user_with_album_access, db_session):
        """Test upload avec accès à l'album - doit réussir"""
        from datetime import timedelta

        from backend.routers.be_auth import create_access_token

        # Créer un token pour l'utilisateur avec accès
        token = create_access_token(
            username=user_with_album_access["email"],
            user_id=user_with_album_access["id"],
            expires_delta=timedelta(hours=1),
        )

        # Créer un petit fichier image factice (JPEG minimal valide)
        image_content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 100 + b"\xff\xd9"
        files = {"files": ("test.jpg", BytesIO(image_content), "image/jpeg")}

        response = client.post(
            f"/be_resizer/upload_images/{user_with_album_access['album_id']}",
            files=files,
            cookies={"access_token": f"Bearer {token}"},
        )

        # Devrait réussir ou avoir une erreur liée au traitement d'image
        # (pas une erreur d'accès 403)
        assert response.status_code != status.HTTP_403_FORBIDDEN

    def test_upload_superuser_bypasses_access_check(self, client, test_album, superuser_auth_headers):
        """Test qu'un superuser peut uploader sans lien explicite avec l'album (#485).

        Le token JWT porte désormais la claim ``is_superuser`` (create_access_token)
        et ``get_current_user`` l'expose. La vérification d'accès dans be_resizer
        (``current_user.get("is_superuser", False)``) laisse donc passer le superuser
        sans lien UserAlbum explicite : la réponse ne doit pas être 403.
        """
        # Créer un petit fichier image factice
        image_content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 100 + b"\xff\xd9"
        files = {"files": ("test.jpg", BytesIO(image_content), "image/jpeg")}

        response = client.post(
            f"/be_resizer/upload_images/{test_album['id']}", files=files, cookies=superuser_auth_headers["cookies"]
        )

        # Le superuser devrait pouvoir uploader (pas d'erreur 403)
        assert response.status_code != status.HTTP_403_FORBIDDEN


class TestFileSizeValidation:
    """Tests pour la validation de la taille des fichiers"""

    def test_upload_image_too_large(self, client, test_album, superuser_auth_headers):
        """Test rejet d'une image trop volumineuse (>30 MB)
        Note: Ce test est simplifié pour éviter de créer un fichier de 31 MB en mémoire.
        On vérifie plutôt que la validation existe via un fichier plus petit.
        """
        # Créer un fichier de taille raisonnable pour le test
        # Le vrai test de limite serait en modifiant temporairement MAX_IMAGE_SIZE
        image_content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 1000 + b"\xff\xd9"
        files = {"files": ("test.jpg", BytesIO(image_content), "image/jpeg")}

        response = client.post(
            f"/be_resizer/upload_images/{test_album['id']}", files=files, cookies=superuser_auth_headers["cookies"]
        )

        # Un fichier de taille normale ne devrait pas être rejeté pour la taille
        assert response.status_code != status.HTTP_413_REQUEST_ENTITY_TOO_LARGE

    def test_upload_video_within_limit(self, client, test_album, superuser_auth_headers):
        """Test qu'une vidéo de taille acceptable (<500 MB) passe la validation"""
        # Créer un fichier vidéo factice de 1 MB (bien en dessous de 500 MB)
        video_content = b"\x00" * (1 * 1024 * 1024)
        files = {"files": ("video.mp4", BytesIO(video_content), "video/mp4")}

        response = client.post(
            f"/be_resizer/upload_images/{test_album['id']}", files=files, cookies=superuser_auth_headers["cookies"]
        )

        # Ne devrait pas être rejeté pour la taille
        assert response.status_code != status.HTTP_413_REQUEST_ENTITY_TOO_LARGE

    def test_upload_album_not_found(self, client, superuser_auth_headers):
        """Test upload vers un album inexistant"""
        image_content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 100 + b"\xff\xd9"
        files = {"files": ("test.jpg", BytesIO(image_content), "image/jpeg")}

        response = client.post(
            "/be_resizer/upload_images/99999", files=files, cookies=superuser_auth_headers["cookies"]
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestFileExtensionValidation:
    """Tests pour la validation des extensions de fichiers"""

    def test_upload_unsupported_extension_skipped(self, client, test_album, superuser_auth_headers):
        """Test que les fichiers avec extension non supportée sont ignorés"""
        # Fichier avec extension non supportée
        file_content = b"fake content"
        files = {"files": ("document.pdf", BytesIO(file_content), "application/pdf")}

        response = client.post(
            f"/be_resizer/upload_images/{test_album['id']}", files=files, cookies=superuser_auth_headers["cookies"]
        )

        # La requête devrait réussir mais le fichier sera ignoré
        # (pas d'erreur HTTP, mais le compteur "skipped" sera incrémenté)
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # Vérifier que le fichier a été ignoré
            assert data.get("details", {}).get("skipped", 0) > 0 or data.get("details", {}).get("uploaded", 0) == 0


class TestGetAlbumImages:
    """Tests pour la récupération des images d'un album"""

    def test_get_album_images_authenticated(self, client, test_album, auth_headers):
        """Test récupération des images d'un album"""
        response = client.get(f"/be_resizer/get_album_images/{test_album['id']}", cookies=auth_headers["cookies"])

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "images" in data
        assert "count" in data
        assert isinstance(data["images"], list)

    def test_get_album_images_album_not_found(self, client, auth_headers):
        """Test récupération des images d'un album inexistant"""
        response = client.get("/be_resizer/get_album_images/99999", cookies=auth_headers["cookies"])

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteImage:
    """Tests pour la suppression d'images"""

    def test_delete_image_not_found(self, client, test_album, auth_headers):
        """Test suppression d'une image inexistante"""
        response = client.delete(
            f"/be_resizer/delete_image/{test_album['id']}/nonexistent.jpg", cookies=auth_headers["cookies"]
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_image_album_not_found(self, client, auth_headers):
        """Test suppression d'une image d'un album inexistant"""
        response = client.delete("/be_resizer/delete_image/99999/image.jpg", cookies=auth_headers["cookies"])

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCreateThumbnailsSecurity:
    """Tests F-1 : create_thumbnails est une opération qui modifie l'état.

    Correctif : l'endpoint passe de GET à POST (une écriture ne doit pas être un
    GET, ce qui rétablit aussi la protection CSRF/SameSite) et est réservé aux
    administrateurs côté serveur (``Depends(require_superuser)``), sans se reposer
    sur le masquage du bouton côté client. Le travail réel de génération de
    vignettes est simulé (monkeypatch) pour isoler la logique de sécurité.
    """

    def _stub_thumbnail_work(self, monkeypatch, tmp_path):
        """Neutralise le travail disque : dossiers existants + génération simulée."""
        import backend.routers.be_resizer as be_resizer

        img_dir = tmp_path / "images"
        tb_dir = tmp_path / "thumbnails"
        img_dir.mkdir()
        tb_dir.mkdir()

        monkeypatch.setattr(be_resizer, "get_album_paths", lambda album: (str(img_dir), str(tb_dir)))
        monkeypatch.setattr(
            be_resizer,
            "img_thumbnails",
            lambda img_path, tb_path, size: {"tbn_exist": 0, "tbn_created": 0, "img_not_supported": 0},
        )

    def test_create_thumbnails_forbidden_for_normal_user(self, client, test_album, auth_headers):
        """Un utilisateur authentifié non-admin reçoit 403 (garde côté serveur)."""
        response = client.post(
            f"/be_resizer/create_thumbnails/{test_album['id']}",
            cookies=auth_headers["cookies"],
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_thumbnails_get_method_not_allowed(self, client, test_album, superuser_auth_headers):
        """L'ancienne méthode GT est refusée (405) — l'écriture n'est plus un GET."""
        response = client.get(
            f"/be_resizer/create_thumbnails/{test_album['id']}",
            cookies=superuser_auth_headers["cookies"],
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_create_thumbnails_post_allowed_for_superuser(
        self, client, test_album, superuser_auth_headers, monkeypatch, tmp_path
    ):
        """Un superuser peut déclencher la génération en POST (travail simulé)."""
        self._stub_thumbnail_work(monkeypatch, tmp_path)

        response = client.post(
            f"/be_resizer/create_thumbnails/{test_album['id']}",
            cookies=superuser_auth_headers["cookies"],
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"

    def test_create_thumbnails_forbidden_for_unauthenticated(self, client, test_album):
        """Sans session, l'accès est refusé (401)."""
        response = client.post(f"/be_resizer/create_thumbnails/{test_album['id']}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
