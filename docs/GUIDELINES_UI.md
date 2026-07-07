# Guidelines de style UI

Toutes les pages héritent de `base.html` qui fournit le style de base. Voici les conventions Tailwind à suivre pour garantir la cohérence visuelle.

## Structure de page

| Élément | Classes Tailwind |
|---------|-----------------|
| Conteneur page | `py-6` ou `py-8` |
| Titre page | `text-3xl font-bold bg-gradient-to-r from-sky-500 to-blue-600 bg-clip-text text-transparent mb-2` |
| Sous-titre/description | `text-gray-600 dark:text-gray-400` |

## Composants

| Élément | Classes Tailwind |
|---------|-----------------|
| Cartes | `bg-white dark:bg-gray-800 rounded-lg shadow-md` |
| Cartes avec bordure | `bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700` |
| Boutons primaires | `bg-sky-600 hover:bg-sky-700 text-white px-4 py-2 rounded-lg transition-colors` |
| Boutons secondaires | `bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700` |
| Boutons danger | `text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700` |
| Inputs/Recherche | `bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:ring-2 focus:ring-sky-500 focus:border-transparent` |

## Grilles responsives

| Type | Classes Tailwind |
|------|-----------------|
| Albums (4 cols) | `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4` |
| Formulaires (2 cols) | `grid grid-cols-1 md:grid-cols-2 gap-4` |

## Tableaux (mobile-friendly)

| Élément | Classes Tailwind |
|---------|-----------------|
| Conteneur scroll | `overflow-x-auto` (permet le scroll horizontal sur mobile) |
| Table | `min-w-full divide-y divide-gray-200 dark:divide-gray-700` |
| Header | `bg-gray-50 dark:bg-gray-900` |
| Cells | `px-6 py-4 whitespace-nowrap` |

## Badges/Tags

| Type | Classes Tailwind |
|------|-----------------|
| Succès | `bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300` |
| Attente | `bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-300` |
| Admin | `bg-purple-100 text-purple-800 dark:bg-purple-900/50 dark:text-purple-300` |

## Icônes d'action

| Action | Couleur hover |
|--------|--------------|
| Télécharger | `hover:text-sky-600 dark:hover:text-sky-400` |
| Uploader/Ajouter | `hover:text-green-600 dark:hover:text-green-400` |
| Éditer | `hover:text-blue-600 dark:hover:text-blue-400` |
| Partager | `hover:text-green-600 dark:hover:text-green-400` |
| Vignettes | `hover:text-purple-600 dark:hover:text-purple-400` |
| Supprimer | `hover:text-red-600 dark:hover:text-red-400` |
