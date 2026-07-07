"""
Script de test pour le système de partage d'albums avec token et PIN
"""

import requests

# Configuration
BASE_URL = "http://localhost:8003"
USER_EMAIL = "sebastien@pe-net.fr"  # À adapter selon vos données de test
USER_PASSWORD = "fake"  # À adapter selon vos données de test
ALBUM_ID = 1  # À adapter selon un album existant


def login():
    """Se connecter et obtenir un token utilisateur"""
    print("🔐 Connexion...")
    response = requests.post(f"{BASE_URL}/be_auth/login", data={"username": USER_EMAIL, "password": USER_PASSWORD})

    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✅ Connecté ! Token: {token[:30]}...")
        return token
    else:
        print(f"❌ Échec connexion: {response.text}")
        return None


def create_share_token(user_token, album_id, expiration_hours=24, pin=None):
    """Créer un token de partage pour un album"""
    print(f"\n📤 Création du lien de partage pour l'album {album_id}...")

    body = {"expiration_hours": expiration_hours}
    if pin:
        body["pin"] = pin

    response = requests.post(
        f"{BASE_URL}/be_album/create_share_token/{album_id}",
        headers={"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"},
        json=body,
    )

    if response.status_code == 200:
        data = response.json()
        print("✅ Lien de partage créé !")
        print(f"   URL: {data['share_url']}")
        print(f"   Code PIN: {data['pin']}")
        print(f"   Expire: {data['expires_at']}")
        return data
    else:
        print(f"❌ Échec création: {response.text}")
        return None


def access_shared_album(share_token, pin):
    """Accéder à un album partagé (sans authentification)"""
    print(f"\n🔓 Tentative d'accès à l'album avec PIN: {pin}...")

    response = requests.get(f"{BASE_URL}/be_album/shared", params={"token": share_token, "pin": pin})

    if response.status_code == 200:
        album = response.json()
        print("✅ Accès réussi !")
        print(f"   Album: {album['title']}")
        print(f"   Description: {album['description']}")
        print(f"   Catégorie: {album.get('category', 'N/A')}")
        return album
    else:
        print(f"❌ Accès refusé: {response.text}")
        return None


def test_wrong_pin(share_token):
    """Test avec un mauvais PIN"""
    print("\n🧪 Test avec un mauvais PIN...")

    response = requests.get(f"{BASE_URL}/be_album/shared", params={"token": share_token, "pin": "WRONG1"})

    if response.status_code == 403:
        print("✅ Rejet correct du mauvais PIN")
        return True
    else:
        print(f"⚠️ Comportement inattendu: {response.status_code}")
        return False


def test_rate_limiting(share_token):
    """Test du rate limiting avec 6 tentatives échouées"""
    print("\n🧪 Test du rate limiting (6 tentatives échouées)...")

    for i in range(1, 7):
        print(f"   Tentative {i}/6 avec mauvais PIN...")
        response = requests.get(f"{BASE_URL}/be_album/shared", params={"token": share_token, "pin": f"WRONG{i}"})

        if response.status_code == 429:
            print(f"✅ Blocage rate limiting activé après {i} tentatives")
            print(f"   Message: {response.json().get('detail', 'N/A')}")
            return True
        elif response.status_code == 403:
            print(f"   Tentative {i} rejetée (normal)")
        else:
            print(f"⚠️ Code inattendu: {response.status_code}")

    print("⚠️ Rate limiting n'a pas bloqué après 6 tentatives")
    return False


def main():
    """Exécuter tous les tests"""
    print("=" * 60)
    print("🧪 Tests du système de partage d'albums")
    print("=" * 60)

    # 1. Connexion utilisateur
    user_token = login()
    if not user_token:
        print("\n❌ Impossible de continuer sans token utilisateur")
        return

    # 2. Créer un lien de partage avec PIN automatique
    share_data = create_share_token(user_token, ALBUM_ID, expiration_hours=48)
    if not share_data:
        print("\n❌ Impossible de créer le lien de partage")
        return

    share_token = share_data["share_token"]
    pin = share_data["pin"]

    # 3. Accéder à l'album avec le bon PIN
    access_shared_album(share_token, pin)

    # 4. Tester avec un mauvais PIN
    test_wrong_pin(share_token)

    # 5. Test du rate limiting
    print("\n" + "=" * 60)
    print("🧪 Test du rate limiting")
    print("=" * 60)

    # Créer un nouveau token pour tester le rate limiting
    rate_limit_share = create_share_token(user_token, ALBUM_ID, expiration_hours=1, pin="RATE99")
    if rate_limit_share:
        test_rate_limiting(rate_limit_share["share_token"])

    # 6. Test avec PIN personnalisé
    print("\n" + "=" * 60)
    print("🧪 Test avec PIN personnalisé")
    print("=" * 60)

    custom_share = create_share_token(user_token, ALBUM_ID, expiration_hours=1, pin="TEST99")

    if custom_share:
        access_shared_album(custom_share["share_token"], "TEST99")

    print("\n" + "=" * 60)
    print("✅ Tests terminés !")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback

        traceback.print_exc()
