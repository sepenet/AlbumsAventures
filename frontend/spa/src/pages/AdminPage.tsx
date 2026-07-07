import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useSession } from "../auth/useSession";
import {
  adminUsersQuery,
  deleteGroupConfirmMessage,
  displayName,
  isSelfDemotion,
  pendingCount,
  promoteConfirmMessage,
  type UserFilter,
} from "../lib/admin";
import { ApiError, api } from "../lib/apiClient";
import type {
  AdminUser,
  Group,
  GroupDetails,
  SessionUser,
  SimpleAlbum,
  SimpleUser,
  UserRightsUpdate,
} from "../types/api";

const cardClass =
  "rounded-xl border border-gray-200 bg-white shadow-lg dark:border-gray-700 dark:bg-gray-800";
const inputClass =
  "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100";
const labelClass = "mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300";
const primaryBtn =
  "inline-flex items-center rounded-lg bg-sky-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-sky-700 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 disabled:bg-sky-400";
const secondaryBtn =
  "inline-flex items-center rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-100 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700";
const dangerBtn =
  "inline-flex items-center rounded-lg border border-red-300 bg-white px-3 py-2 text-sm text-red-700 transition-colors hover:bg-red-50 disabled:opacity-50 dark:border-red-800 dark:bg-gray-800 dark:text-red-400 dark:hover:bg-red-900/20";

function errorText(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <p
      role="alert"
      className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300"
    >
      {message}
    </p>
  );
}

function SuccessBanner({ message }: { message: string }) {
  return (
    <p
      role="status"
      className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-300"
    >
      {message}
    </p>
  );
}

// --------------------------------------------------------------------------
// Users panel — pending activation + promote-to-admin (be_auth admin endpoints,
// all superuser-gated server-side).
// --------------------------------------------------------------------------

function UsersPanel({ current }: { current: SessionUser }) {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<UserFilter>("all");

  const usersQuery = useQuery<AdminUser[]>({
    queryKey: ["admin-users", filter],
    queryFn: () => api.get<AdminUser[]>(`/be_auth/admin/users${adminUsersQuery(filter)}`),
  });

  const rightsMutation = useMutation({
    mutationFn: ({ userId, rights }: { userId: number; rights: UserRightsUpdate }) =>
      api.put<AdminUser>(`/be_auth/admin/users/${userId}/rights`, rights),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const users = usersQuery.data ?? [];
  const pending = pendingCount(users);

  function toggleActive(user: AdminUser) {
    rightsMutation.reset();
    rightsMutation.mutate({ userId: user.id, rights: { is_active: !user.is_active } });
  }

  function toggleAdmin(user: AdminUser) {
    const next = !user.is_superuser;
    if (isSelfDemotion(current, user, next)) {
      window.alert("Vous ne pouvez pas retirer vos propres droits administrateur.");
      return;
    }
    if (!window.confirm(promoteConfirmMessage(user))) return;
    rightsMutation.reset();
    rightsMutation.mutate({ userId: user.id, rights: { is_superuser: next } });
  }

  const filters: { id: UserFilter; label: string }[] = [
    { id: "all", label: "Tous" },
    { id: "pending", label: `En attente${pending ? ` (${pending})` : ""}` },
    { id: "active", label: "Actifs" },
  ];

  return (
    <section className={cardClass}>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 px-6 py-4 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Utilisateurs</h2>
        <div className="flex gap-2">
          {filters.map((option) => (
            <button
              key={option.id}
              type="button"
              onClick={() => setFilter(option.id)}
              className={filter === option.id ? primaryBtn : secondaryBtn}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>
      <div className="space-y-4 p-6">
        {rightsMutation.isError ? (
          <ErrorBanner message={errorText(rightsMutation.error, "Erreur lors de la mise à jour des droits")} />
        ) : null}
        {rightsMutation.isSuccess ? <SuccessBanner message="Droits mis à jour" /> : null}

        {usersQuery.isPending ? (
          <p className="py-8 text-center text-gray-500 dark:text-gray-400">Chargement des utilisateurs…</p>
        ) : usersQuery.isError ? (
          <ErrorBanner message={errorText(usersQuery.error, "Impossible de charger les utilisateurs")} />
        ) : users.length === 0 ? (
          <p className="py-8 text-center text-gray-500 dark:text-gray-400">Aucun utilisateur.</p>
        ) : (
          <ul className="divide-y divide-gray-200 dark:divide-gray-700">
            {users.map((user) => (
              <li key={user.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <p className="truncate font-medium text-gray-900 dark:text-gray-100">
                    {displayName(user)}
                  </p>
                  <p className="truncate text-sm text-gray-500 dark:text-gray-400">{user.email}</p>
                  <div className="mt-1 flex gap-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        user.is_active
                          ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300"
                          : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
                      }`}
                    >
                      {user.is_active ? "Actif" : "En attente"}
                    </span>
                    {user.is_superuser ? (
                      <span className="rounded-full bg-sky-100 px-2 py-0.5 text-xs text-sky-700 dark:bg-sky-900/30 dark:text-sky-300">
                        Admin
                      </span>
                    ) : null}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => toggleActive(user)}
                    disabled={rightsMutation.isPending}
                    className={secondaryBtn}
                  >
                    {user.is_active ? "Désactiver" : "Activer"}
                  </button>
                  <button
                    type="button"
                    onClick={() => toggleAdmin(user)}
                    disabled={rightsMutation.isPending}
                    className={secondaryBtn}
                  >
                    {user.is_superuser ? "Retirer admin" : "Promouvoir admin"}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

// --------------------------------------------------------------------------
// Groups panel — create / edit / delete groups and manage their members and
// albums (be_group endpoints).
// --------------------------------------------------------------------------

function GroupsPanel() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [newGroup, setNewGroup] = useState({ name: "", description: "" });
  const [addUserId, setAddUserId] = useState("");
  const [addAlbumId, setAddAlbumId] = useState("");

  const groupsQuery = useQuery<Group[]>({
    queryKey: ["admin-groups"],
    queryFn: () => api.get<Group[]>("/be_group/get_all_groups/"),
  });

  const detailsQuery = useQuery<GroupDetails>({
    queryKey: ["admin-group-details", selectedId],
    queryFn: () => api.get<GroupDetails>(`/be_group/get_group_details/${selectedId}`),
    enabled: selectedId !== null,
  });

  const usersQuery = useQuery<SimpleUser[]>({
    queryKey: ["admin-simple-users"],
    queryFn: () => api.get<SimpleUser[]>("/be_group/get_all_users_simple/"),
  });

  const albumsQuery = useQuery<SimpleAlbum[]>({
    queryKey: ["admin-simple-albums"],
    queryFn: () => api.get<SimpleAlbum[]>("/be_group/get_all_albums_simple/"),
  });

  function invalidateGroups() {
    queryClient.invalidateQueries({ queryKey: ["admin-groups"] });
    queryClient.invalidateQueries({ queryKey: ["admin-group-details"] });
  }

  const createGroup = useMutation({
    mutationFn: (body: { name: string; description: string }) =>
      api.post<Group>("/be_group/create_group/", body),
    onSuccess: () => {
      setNewGroup({ name: "", description: "" });
      invalidateGroups();
    },
  });

  const deleteGroup = useMutation({
    mutationFn: (groupId: number) => api.del<{ message: string }>(`/be_group/delete_group/${groupId}`),
    onSuccess: () => {
      setSelectedId(null);
      invalidateGroups();
    },
  });

  const addUser = useMutation({
    mutationFn: ({ groupId, userId }: { groupId: number; userId: number }) =>
      api.post("/be_group/create_users_group_bulk/", { group_id: groupId, user_ids: [userId] }),
    onSuccess: () => {
      setAddUserId("");
      invalidateGroups();
    },
  });

  const removeUser = useMutation({
    mutationFn: ({ groupId, userId }: { groupId: number; userId: number }) =>
      api.del(`/be_group/delete_user_group/${userId}/${groupId}`),
    onSuccess: () => invalidateGroups(),
  });

  const addAlbum = useMutation({
    mutationFn: ({ groupId, albumId }: { groupId: number; albumId: number }) =>
      api.post("/be_group/create_albums_group_bulk/", { group_id: groupId, album_ids: [albumId] }),
    onSuccess: () => {
      setAddAlbumId("");
      invalidateGroups();
    },
  });

  const removeAlbum = useMutation({
    mutationFn: ({ groupId, albumId }: { groupId: number; albumId: number }) =>
      api.del(`/be_group/delete_album_group/${albumId}/${groupId}`),
    onSuccess: () => invalidateGroups(),
  });

  const groups = groupsQuery.data ?? [];
  const details = detailsQuery.data;

  const mutationError = [createGroup, deleteGroup, addUser, removeUser, addAlbum, removeAlbum].find(
    (mutation) => mutation.isError,
  );

  const availableUsers = useMemo(() => usersQuery.data ?? [], [usersQuery.data]);
  const availableAlbums = useMemo(() => albumsQuery.data ?? [], [albumsQuery.data]);

  function submitCreate(event: React.FormEvent) {
    event.preventDefault();
    if (!newGroup.name.trim()) return;
    createGroup.reset();
    createGroup.mutate({ name: newGroup.name.trim(), description: newGroup.description.trim() });
  }

  function confirmDelete(group: Group) {
    if (!window.confirm(deleteGroupConfirmMessage(group.name))) return;
    deleteGroup.reset();
    deleteGroup.mutate(group.id);
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {/* Group list + create */}
      <section className={cardClass}>
        <div className="border-b border-gray-200 px-6 py-4 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Groupes</h2>
        </div>
        <div className="space-y-4 p-6">
          {mutationError ? (
            <ErrorBanner message={errorText(mutationError.error, "Erreur lors de l'opération sur le groupe")} />
          ) : null}

          {groupsQuery.isPending ? (
            <p className="py-4 text-center text-gray-500 dark:text-gray-400">Chargement des groupes…</p>
          ) : groupsQuery.isError ? (
            <ErrorBanner message={errorText(groupsQuery.error, "Impossible de charger les groupes")} />
          ) : groups.length === 0 ? (
            <p className="py-4 text-center text-gray-500 dark:text-gray-400">Aucun groupe.</p>
          ) : (
            <ul className="divide-y divide-gray-200 dark:divide-gray-700">
              {groups.map((group) => (
                <li key={group.id} className="flex items-center justify-between gap-3 py-2">
                  <button
                    type="button"
                    onClick={() => setSelectedId(group.id)}
                    className={`min-w-0 flex-1 text-left ${
                      selectedId === group.id ? "font-semibold text-sky-600 dark:text-sky-400" : ""
                    }`}
                  >
                    <span className="truncate text-gray-900 dark:text-gray-100">{group.name}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => confirmDelete(group)}
                    disabled={deleteGroup.isPending}
                    className={dangerBtn}
                  >
                    Supprimer
                  </button>
                </li>
              ))}
            </ul>
          )}

          <form onSubmit={submitCreate} className="space-y-3 border-t border-gray-200 pt-4 dark:border-gray-700">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Nouveau groupe</h3>
            <div>
              <label htmlFor="group-name" className={labelClass}>
                Nom
              </label>
              <input
                id="group-name"
                type="text"
                value={newGroup.name}
                onChange={(event) => setNewGroup((form) => ({ ...form, name: event.target.value }))}
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="group-description" className={labelClass}>
                Description
              </label>
              <input
                id="group-description"
                type="text"
                value={newGroup.description}
                onChange={(event) => setNewGroup((form) => ({ ...form, description: event.target.value }))}
                className={inputClass}
              />
            </div>
            <button type="submit" disabled={createGroup.isPending} className={primaryBtn}>
              {createGroup.isPending ? "Création…" : "Créer le groupe"}
            </button>
          </form>
        </div>
      </section>

      {/* Selected group details */}
      <section className={cardClass}>
        <div className="border-b border-gray-200 px-6 py-4 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {details ? `Accès — ${details.group.name}` : "Détails du groupe"}
          </h2>
        </div>
        <div className="space-y-5 p-6">
          {selectedId === null ? (
            <p className="py-4 text-center text-gray-500 dark:text-gray-400">
              Sélectionnez un groupe pour gérer ses membres et albums.
            </p>
          ) : detailsQuery.isPending ? (
            <p className="py-4 text-center text-gray-500 dark:text-gray-400">Chargement…</p>
          ) : detailsQuery.isError ? (
            <ErrorBanner message={errorText(detailsQuery.error, "Impossible de charger le groupe")} />
          ) : details ? (
            <>
              {/* Members */}
              <div className="space-y-2">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Membres</h3>
                {details.users.length === 0 ? (
                  <p className="text-sm text-gray-500 dark:text-gray-400">Aucun membre.</p>
                ) : (
                  <ul className="space-y-1">
                    {details.users.map((user) => (
                      <li key={user.id} className="flex items-center justify-between gap-2 text-sm">
                        <span className="truncate text-gray-800 dark:text-gray-200">{displayName(user)}</span>
                        <button
                          type="button"
                          onClick={() => removeUser.mutate({ groupId: details.group.id, userId: user.id })}
                          disabled={removeUser.isPending}
                          className={dangerBtn}
                        >
                          Retirer
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
                <div className="flex gap-2">
                  <select
                    aria-label="Ajouter un utilisateur"
                    value={addUserId}
                    onChange={(event) => setAddUserId(event.target.value)}
                    className={inputClass}
                  >
                    <option value="">Ajouter un utilisateur…</option>
                    {availableUsers.map((user) => (
                      <option key={user.id} value={user.id}>
                        {displayName(user)}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    disabled={!addUserId || addUser.isPending}
                    onClick={() => addUser.mutate({ groupId: details.group.id, userId: Number(addUserId) })}
                    className={primaryBtn}
                  >
                    Ajouter
                  </button>
                </div>
              </div>

              {/* Albums */}
              <div className="space-y-2 border-t border-gray-200 pt-4 dark:border-gray-700">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Albums</h3>
                {details.albums.length === 0 ? (
                  <p className="text-sm text-gray-500 dark:text-gray-400">Aucun album.</p>
                ) : (
                  <ul className="space-y-1">
                    {details.albums.map((album) => (
                      <li key={album.id} className="flex items-center justify-between gap-2 text-sm">
                        <span className="truncate text-gray-800 dark:text-gray-200">{album.title}</span>
                        <button
                          type="button"
                          onClick={() => removeAlbum.mutate({ groupId: details.group.id, albumId: album.id })}
                          disabled={removeAlbum.isPending}
                          className={dangerBtn}
                        >
                          Retirer
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
                <div className="flex gap-2">
                  <select
                    aria-label="Ajouter un album"
                    value={addAlbumId}
                    onChange={(event) => setAddAlbumId(event.target.value)}
                    className={inputClass}
                  >
                    <option value="">Ajouter un album…</option>
                    {availableAlbums.map((album) => (
                      <option key={album.id} value={album.id}>
                        {album.title}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    disabled={!addAlbumId || addAlbum.isPending}
                    onClick={() => addAlbum.mutate({ groupId: details.group.id, albumId: Number(addAlbumId) })}
                    className={primaryBtn}
                  >
                    Ajouter
                  </button>
                </div>
              </div>
            </>
          ) : null}
        </div>
      </section>
    </div>
  );
}

// --------------------------------------------------------------------------
// Admin page shell with a tab toggle between the users and groups panels.
// --------------------------------------------------------------------------

type AdminTab = "users" | "groups";

/**
 * React admin page (Phase 3.6 strangler variant of admin_users.html +
 * admin_groups.html). Reached at `/app/admin`, behind `RequireSuperuser`.
 *
 * All mutating actions go through the shared apiClient (cookie-only auth; CSRF
 * double-submit header on POST/PUT/DELETE). The server remains the authority:
 * the be_auth admin endpoints re-check `is_superuser` (#485). Loading, error and
 * success states are surfaced; destructive actions (promote/demote, delete
 * group, remove member/album) prompt for confirmation. The Jinja admin pages
 * stay live during the migration.
 */
export function AdminPage() {
  const { data: user } = useSession();
  const [tab, setTab] = useState<AdminTab>("users");

  // RequireSuperuser guarantees a superuser session before this renders.
  if (!user) return null;

  return (
    <div className="mx-auto max-w-4xl py-8">
      <div className="mb-6">
        <h1 className="mb-2 bg-gradient-to-r from-sky-500 to-blue-600 bg-clip-text text-3xl font-bold text-transparent">
          Administration
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Gérez les utilisateurs, les activations et les groupes d&apos;accès
        </p>
      </div>

      <div className="mb-6 flex gap-2">
        <button
          type="button"
          onClick={() => setTab("users")}
          className={tab === "users" ? primaryBtn : secondaryBtn}
        >
          Utilisateurs
        </button>
        <button
          type="button"
          onClick={() => setTab("groups")}
          className={tab === "groups" ? primaryBtn : secondaryBtn}
        >
          Groupes
        </button>
      </div>

      {tab === "users" ? <UsersPanel current={user} /> : <GroupsPanel />}
    </div>
  );
}
