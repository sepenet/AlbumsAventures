"""Regression tests for the media bridge (URL-preservation seam).

These tests lock the two authorization contracts that were preserved verbatim
when the SPA-facing media endpoints moved from ``frontend/routers/fe_router.py``
to ``backend/routers/be_media_bridge.py``:

* ``GET /album/{album_id}/images`` requires authentication (401 when the caller
  has no valid session cookie) — the auth check runs in-process before any
  backend call, so this is deterministic without a live backend.
* ``GET /album/shared/images`` enforces a 6-character ``pin`` at the request
  boundary; a short/malformed PIN is rejected (422) before any backend call.

Both assertions also prove the endpoints resolve at their BARE URLs (not 404),
which is the whole point of the compatibility seam.
"""


class TestMediaBridgeAuthz:
    """Authorization contracts preserved by the media bridge relocation."""

    def test_album_images_requires_authentication(self, client):
        """Unauthenticated access to the authenticated media endpoint -> 401."""
        response = client.get("/album/1/images")
        assert response.status_code == 401
        assert response.json() == {"detail": "Non authentifié"}

    def test_album_images_bare_url_resolves(self, client):
        """The endpoint is reachable at its bare URL (401, not 404)."""
        response = client.get("/album/1/images")
        assert response.status_code != 404

    def test_shared_images_rejects_short_pin(self, client):
        """A PIN shorter than 6 chars is rejected at the boundary (422)."""
        response = client.get("/album/shared/images", params={"token": "abc", "pin": "123"})
        assert response.status_code == 422

    def test_shared_images_rejects_long_pin(self, client):
        """A PIN longer than 6 chars is rejected at the boundary (422)."""
        response = client.get("/album/shared/images", params={"token": "abc", "pin": "1234567"})
        assert response.status_code == 422

    def test_shared_images_requires_token(self, client):
        """A missing token is rejected at the boundary (422)."""
        response = client.get("/album/shared/images", params={"pin": "123456"})
        assert response.status_code == 422
