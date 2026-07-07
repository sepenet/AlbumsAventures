# Gestion des formats

Il y a un endpoint dédié : `bakend/routers/be_formatter/*`  
Les conversions entre les différents formats sont faites par l'endpoint de formatage.  
Il existe plusieurs formats selon le contexte d'utilisation : web, DB, nom de répertoire, formulaire de saisie.

## Format pour le titre

- **web** : on suit les règles d'orthographe de la langue française ex : "Vacances d'été à Nîmes"
- **DB** : le même que pour l'affichage web
- **Nom des répertoires d'albums** : on remplace du format web les espaces et apostrophe par des tirets. Ex : "Vacances-d-été-à-Nîmes"
- **Formulaire de saisie** : pas de règle particulière.

## Format pour la description

- **web** : on suit les règles d'orthographe de la langue française ex : "Vacances d'été à Nîmes"
- **DB** : le même que pour l'affichage web
- **Nom des répertoires d'albums** : Pas utilisé dans le nom du répertoire.
- **Formulaire de saisie** : pas de règle particulière.

## Format pour les catégories

- **web** : on suit les règles d'orthographe de la langue française ex : "Vacances d'été à Nîmes"
- **DB** : le même que pour l'affichage web
- **Nom des répertoires de catégories** : on remplace du format web les espaces et apostrophe par des tirets. Ex : "Ski-d-alpinisme"
- **Formulaire de saisie** : liste déroulante.

## Format pour la date

- **web** : <Jour> <Mois en lettre> <année>, ex : 09 Septembre 2025.
Le jour est caché mais sert pour le tri des modal par ordre décroissant de la date la plus récente en haut à gauche à la plus lointaine en bas à droite.
- **DB** : enregistrement au format date
- **Nom des répertoires d'albums** : Année-Mois-Jour ex : 2025-01-09
- **Formulaire de saisie** : Date picker.

## Format pour les participants

- **web** : Prénom avec majuscule, séparés par des virgules. Les prénoms composés avec tirets (orthographe française). ex: "Sabina, Margaux, Eléna, Jean-Pierre"
- **DB** : Prénom avec majuscule, séparés par des "|", les prénoms composés avec tirets. ex : "Sabina|Margaux|Eléna|Jean-Pierre"
- **Nom des répertoires d'albums** : Prénom avec majuscule, séparés par des tirets, sans espaces, les tirets des prénoms composés sont supprimés (CamelCase). Ex : "Sabina-Margaux-Eléna-JeanPierre"
- **Formulaire de saisie** : Prénom avec majuscule, séparés par des virgules ou espaces. Les prénoms composés avec tirets (orthographe française). ex: "Sabina, Margaux Eléna, Jean-Pierre"

## Format pour les lieux

- **web** : on suit les règles d'orthographe de la langue française ex : ""
- **DB** : le même que pour l'affichage web
- **Nom des répertoires** : Pas utilisé dans le nom du répertoire.
- **Formulaire de saisie** : séparateur espace ou virgule.

## Format pour les tags

- **web** : liste de tags séparés par des virgules. Tout en minuscule.
- **DB** : liste de tags séparés par "|".
- **Nom des répertoires** : Pas utilisé dans le nom du répertoire.
- **Formulaire de saisie** : séparateur espace ou virgule.

## Format pour le chemin d'accès à l'image de couverture album

- **web** : nom du fichier de l'image incluant son extension, ex : chamonix-zermatt-001.jpg
- **DB** : le même que pour l'affichage web
- **Nom des répertoires** : Pas utilisé dans le nom du répertoire.
- **Formulaire de saisie** : nom d'un fichier avec son extension.
