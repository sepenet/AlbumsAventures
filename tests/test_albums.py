"""
Tests fonctionnels pour les opérations CRUD sur les albums (be_album).
"""

from fastapi import status


class TestGetAlbums:
    """Tests pour la récupération des albums"""

    def test_get_all_albums_authenticated(self, client, test_album, auth_headers):
        """Test récupération de tous les albums avec authentification"""
        response = client.get("/be_album/get_all_albums/", cookies=auth_headers["cookies"])

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_all_albums_unauthenticated(self, client):
        """Test récupération sans authentification - doit échouer"""
        response = client.get("/be_album/get_all_albums/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_album_by_id(self, client, test_album, auth_headers):
        """Test récupération d'un album par son ID"""
        response = client.get(f"/be_album/get_album_by_id/{test_album['id']}", cookies=auth_headers["cookies"])

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_album["id"]
        assert data["title"] == test_album["title"]

    def test_get_album_by_id_not_found(self, client, auth_headers):
        """Test récupération d'un album inexistant"""
        response = client.get("/be_album/get_album_by_id/99999", cookies=auth_headers["cookies"])

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_albums_by_user(self, client, user_with_album_access, auth_headers):
        """Test récupération des albums d'un utilisateur"""
        response = client.get(
            f"/be_album/get_albums_by_user/{user_with_album_access['id']}", cookies=auth_headers["cookies"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        # L'utilisateur devrait avoir accès à au moins l'album de test
        assert len(data) >= 1

        # Vérifier que l'album de test est dans la liste
        album_ids = [a["id"] for a in data]
        assert user_with_album_access["album_id"] in album_ids


class TestCreateAlbum:
    """Tests pour la création d'albums"""

    def test_create_album_success(self, client, test_category, superuser_auth_headers):
        """Test création d'album avec données valides"""
        album_data = {
            "title": "Nouvel Album",
            "description": "Description du nouvel album",
            "category_id": test_category["id"],
            "date": "2024-07-20",
            "participants": "Pierre|Paul",
            "location": "Lyon",
            "tags": "été,famille",
            "image_cover": None,
        }

        response = client.post("/be_album/create_album/", json=album_data, cookies=superuser_auth_headers["cookies"])

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Nouvel Album"
        assert data["category_id"] == test_category["id"]
        assert "id" in data

    def test_create_album_missing_required_fields(self, client, superuser_auth_headers):
        """Test création d'album avec champs obligatoires manquants"""
        album_data = {
            "title": "Album sans catégorie"
            # category_id et date manquants
        }

        response = client.post("/be_album/create_album/", json=album_data, cookies=superuser_auth_headers["cookies"])

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_album_unauthenticated(self, client, test_category):
        """Test création d'album sans authentification"""
        album_data = {"title": "Album Test", "category_id": test_category["id"], "date": "2024-07-20"}

        response = client.post("/be_album/create_album/", json=album_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUpdateAlbum:
    """Tests pour la mise à jour d'albums"""

    def test_update_album_success(self, client, test_album, superuser_auth_headers):
        """Test mise à jour partielle d'un album"""
        update_data = {
            "title": "Titre Modifié",
            "description": "Nouvelle description",
            "date": test_album["date"],  # date est requise dans AlbumUpdate
        }

        response = client.patch(
            f"/be_album/update_album/{test_album['id']}", json=update_data, cookies=superuser_auth_headers["cookies"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Titre Modifié"
        assert data["description"] == "Nouvelle description"

    def test_update_album_single_field(self, client, test_album, superuser_auth_headers):
        """Test mise à jour d'un seul champ (avec date requise)"""
        update_data = {"location": "Marseille", "date": test_album["date"]}  # date est requise dans AlbumUpdate

        response = client.patch(
            f"/be_album/update_album/{test_album['id']}", json=update_data, cookies=superuser_auth_headers["cookies"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["location"] == "Marseille"
        # Le titre original doit être préservé
        assert data["title"] == test_album["title"]


class TestCategories:
    """Tests pour les catégories"""

    def test_get_categories(self, client, test_category, auth_headers):
        """Test récupération de toutes les catégories"""
        response = client.get("/be_album/get_categories/", cookies=auth_headers["cookies"])

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Vérifier que la catégorie de test est présente
        category_names = [c["category"] for c in data]
        assert test_category["category"] in category_names


class TestAlbumAccess:
    """Tests pour la vérification des accès aux albums"""

    def test_user_can_access_linked_album(self, client, user_with_album_access, auth_headers):
        """Test qu'un utilisateur peut accéder à un album auquel il est lié"""
        response = client.get(
            f"/be_album/get_albums_by_user/{user_with_album_access['id']}", cookies=auth_headers["cookies"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        album_ids = [a["id"] for a in data]
        assert user_with_album_access["album_id"] in album_ids

    def test_user_without_albums_returns_404(self, client, db_session, auth_headers):
        """Test qu'un utilisateur sans albums retourne 404"""
        from backend.db import models
        from utils.password import get_password_hash

        # Créer un utilisateur sans aucun album
        new_user = models.User(
            firstname="NoAlbum",
            lastname="User",
            email="noalbum@example.com",
            password=get_password_hash("Password123"),
            is_active=True,
            is_superuser=False,
        )
        db_session.add(new_user)
        db_session.commit()
        db_session.refresh(new_user)

        response = client.get(f"/be_album/get_albums_by_user/{new_user.id}", cookies=auth_headers["cookies"])

        # Devrait retourner 404 car aucun album trouvé
        assert response.status_code == status.HTTP_404_NOT_FOUND


def _valid_png_bytes() -> bytes:
    """Génère un petit PNG valide en mémoire (magic bytes réels pour PIL.verify)."""
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (8, 8), (120, 80, 200)).save(buf, format="PNG")
    return buf.getvalue()


class TestAlbumSuperuserGating:
    """Un utilisateur authentifié NON-superuser doit recevoir 403 sur les mutations."""

    def test_create_album_forbidden_for_non_superuser(self, client, test_category, auth_headers):
        album_data = {
            "title": "Album interdit",
            "description": None,
            "category_id": test_category["id"],
            "date": "2024-07-20",
            "participants": None,
            "location": None,
            "tags": None,
            "image_cover": None,
        }
        response = client.post("/be_album/create_album/", json=album_data, cookies=auth_headers["cookies"])
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_album_forbidden_for_non_superuser(self, client, test_album, auth_headers):
        response = client.patch(
            f"/be_album/update_album/{test_album['id']}",
            json={"title": "Hack", "date": test_album["date"]},
            cookies=auth_headers["cookies"],
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_album_folder_forbidden_for_non_superuser(self, client, test_album, auth_headers):
        response = client.post(
            f"/be_album/create_album_folder/{test_album['id']}", cookies=auth_headers["cookies"]
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_category_forbidden_for_non_superuser(self, client, auth_headers):
        response = client.post(
            "/be_category/create_category/", json={"category": "Interdite"}, cookies=auth_headers["cookies"]
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_be_album_create_category_forbidden_for_non_superuser(self, client, auth_headers):
        response = client.post(
            "/be_album/create_category/", json={"category": "Interdite"}, cookies=auth_headers["cookies"]
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_upload_cover_forbidden_for_non_superuser(self, client, test_album, auth_headers):
        files = {"image_cover": ("cover.png", _valid_png_bytes(), "image/png")}
        response = client.post(
            f"/be_album/upload_cover/{test_album['id']}", files=files, cookies=auth_headers["cookies"]
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_album_folder_superuser_ok(self, client, test_album, superuser_auth_headers, monkeypatch, tmp_path):
        from utils.config import image

        monkeypatch.setattr(image, "image_path", str(tmp_path / "images"))
        monkeypatch.setattr(image, "thumbnails_path", str(tmp_path / "thumbnails"))
        response = client.post(
            f"/be_album/create_album_folder/{test_album['id']}", cookies=superuser_auth_headers["cookies"]
        )
        assert response.status_code == status.HTTP_200_OK


class TestCoverUpload:
    """Endpoint durci POST /be_album/upload_cover/{id} (superuser)."""

    def test_upload_cover_happy_path(self, client, test_album, superuser_auth_headers, monkeypatch, tmp_path):
        from utils.config import image

        images_root = tmp_path / "images"
        thumbs_root = tmp_path / "thumbnails"
        monkeypatch.setattr(image, "image_path", str(images_root))
        monkeypatch.setattr(image, "thumbnails_path", str(thumbs_root))

        files = {"image_cover": ("cover.png", _valid_png_bytes(), "image/png")}
        response = client.post(
            f"/be_album/upload_cover/{test_album['id']}", files=files, cookies=superuser_auth_headers["cookies"]
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["image_cover"] == "cover.png"

        # L'image + la vignette existent sous la racine de l'album (test_album =
        # Vacances / 2024-06-15_Album-Test_Jean-Marie).
        written_images = list(images_root.rglob("cover.png"))
        written_thumbs = list(thumbs_root.rglob("cover.png"))
        assert written_images, "L'image de couverture n'a pas été écrite"
        assert written_thumbs, "La vignette de couverture n'a pas été écrite"

        # image_cover a bien été persisté en base.
        album = client.get(
            f"/be_album/get_album_by_id/{test_album['id']}", cookies=superuser_auth_headers["cookies"]
        ).json()
        assert album["image_cover"] == "cover.png"

    def test_upload_cover_rejects_path_traversal(self, client, test_album, superuser_auth_headers, monkeypatch, tmp_path):
        """Un nom de fichier `../evil.png` NE PEUT PAS s'échapper du dossier album."""
        from utils.config import image

        images_root = tmp_path / "images"
        thumbs_root = tmp_path / "thumbnails"
        monkeypatch.setattr(image, "image_path", str(images_root))
        monkeypatch.setattr(image, "thumbnails_path", str(thumbs_root))

        files = {"image_cover": ("../../../evil.png", _valid_png_bytes(), "image/png")}
        response = client.post(
            f"/be_album/upload_cover/{test_album['id']}", files=files, cookies=superuser_auth_headers["cookies"]
        )
        # basename neutralise la remontée : le nom stocké est "evil.png" et reste confiné.
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["image_cover"] == "evil.png"

        # Aucune écriture hors de la racine images (pas d'évasion vers tmp_path).
        assert not (tmp_path / "evil.png").exists()
        assert not (images_root.parent / "evil.png").exists()
        confined = list(images_root.rglob("evil.png"))
        assert confined, "Le fichier devrait rester confiné sous la racine de l'album"
        for p in confined:
            assert str(images_root.resolve()) in str(p.resolve())

    def test_upload_cover_rejects_bad_extension(self, client, test_album, superuser_auth_headers, monkeypatch, tmp_path):
        from utils.config import image

        monkeypatch.setattr(image, "image_path", str(tmp_path / "images"))
        monkeypatch.setattr(image, "thumbnails_path", str(tmp_path / "thumbnails"))
        files = {"image_cover": ("payload.svg", b"<svg></svg>", "image/svg+xml")}
        response = client.post(
            f"/be_album/upload_cover/{test_album['id']}", files=files, cookies=superuser_auth_headers["cookies"]
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_cover_rejects_non_image_bytes(self, client, test_album, superuser_auth_headers, monkeypatch, tmp_path):
        from utils.config import image

        monkeypatch.setattr(image, "image_path", str(tmp_path / "images"))
        monkeypatch.setattr(image, "thumbnails_path", str(tmp_path / "thumbnails"))
        # Extension autorisée mais contenu NON-image (magic bytes invalides).
        files = {"image_cover": ("fake.png", b"not really a png", "image/png")}
        response = client.post(
            f"/be_album/upload_cover/{test_album['id']}", files=files, cookies=superuser_auth_headers["cookies"]
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
