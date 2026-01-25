"use client";

import { useEffect, useState } from "react";

import { apiFetch } from "../../../../lib/api";
import { useAdminGuard } from "../../../hooks/useAdminGuard";
import PageHeader from "../../../components/PageHeader";
import Dialog from "../../../components/Dialog";
import LoadingSkeleton from "../../../components/LoadingSkeleton";
import EmptyState from "../../../components/EmptyState";
import ErrorState from "../../../components/ErrorState";
import { useToast } from "../../../components/ToastProvider";
import styles from "./page.module.css";

type User = {
  id: number;
  email: string;
  display_name: string;
  is_admin: boolean;
  is_blocked: boolean;
  must_change_password: boolean;
};

export default function AdminUsersPage() {
  const { ready, isAdmin } = useAdminGuard();
  const { pushToast } = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tempPassword, setTempPassword] = useState<string | null>(null);
  const [resetTarget, setResetTarget] = useState<User | null>(null);

  const loadUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch("/admin/users");
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setError(data?.detail ?? "Не удалось загрузить пользователей");
        setLoading(false);
        return;
      }
      const data = (await response.json()) as User[];
      setUsers(data);
    } catch {
      setError("Не удалось загрузить пользователей");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!ready || !isAdmin) {
      return;
    }
    loadUsers();
  }, [ready, isAdmin]);

  const updateRole = async (userId: number, isAdminRole: boolean) => {
    try {
      const response = await apiFetch(`/admin/users/${userId}`, {
        method: "PATCH",
        body: JSON.stringify({ is_admin: isAdminRole }),
      });
      if (!response.ok) {
        pushToast("Не удалось обновить роль", "error");
        return;
      }
      pushToast("Роль обновлена", "success");
      await loadUsers();
    } catch {
      pushToast("Не удалось обновить роль", "error");
    }
  };

  const toggleBlock = async (user: User) => {
    const endpoint = user.is_blocked ? "unblock" : "block";
    try {
      const response = await apiFetch(`/admin/users/${user.id}/${endpoint}`, { method: "POST" });
      if (!response.ok) {
        pushToast("Не удалось обновить статус", "error");
        return;
      }
      pushToast(user.is_blocked ? "Пользователь разблокирован" : "Пользователь заблокирован", "success");
      await loadUsers();
    } catch {
      pushToast("Не удалось обновить статус", "error");
    }
  };

  const resetPassword = async () => {
    if (!resetTarget) {
      return;
    }
    try {
      const response = await apiFetch(`/admin/users/${resetTarget.id}/reset-password`, {
        method: "POST",
      });
      if (!response.ok) {
        pushToast("Не удалось сбросить пароль", "error");
        return;
      }
      const data = (await response.json()) as { temporary_password: string };
      setTempPassword(data.temporary_password);
      pushToast("Временный пароль создан", "success");
      await loadUsers();
    } catch {
      pushToast("Не удалось сбросить пароль", "error");
    }
  };

  const handleCopyPassword = async () => {
    if (!tempPassword) {
      return;
    }
    try {
      await navigator.clipboard.writeText(tempPassword);
      pushToast("Пароль скопирован", "success");
    } catch {
      pushToast("Не удалось скопировать пароль", "error");
    }
  };

  if (!ready || !isAdmin) {
    return null;
  }

  return (
    <div className="page">
      <PageHeader
        title="Пользователи"
        subtitle="Управляйте ролями, блокировками и временными паролями."
      />
      {loading && <LoadingSkeleton lines={3} />}
      {error && <ErrorState title="Раздел недоступен" description={error} />}
      {!loading && !error && users.length === 0 && (
        <EmptyState
          title="Пользователи не найдены"
          description="Список пользователей пока пуст."
        />
      )}
      {users.length > 0 && (
        <section className={styles.tableCard}>
          <div className={styles.tableHeader}>
            <span>Почта</span>
            <span>Имя</span>
            <span>Роль</span>
            <span>Статус</span>
            <span>Действия</span>
          </div>
          {users.map((user) => (
            <div key={user.id} className={styles.tableRow}>
              <span>{user.email}</span>
              <span>{user.display_name}</span>
              <select
                className="select"
                value={user.is_admin ? "admin" : "user"}
                onChange={(event) => updateRole(user.id, event.target.value === "admin")}
              >
                <option value="user">Пользователь</option>
                <option value="admin">Администратор</option>
              </select>
              <span className={styles.status}>
                {user.is_blocked ? "Заблокирован" : "Активен"}
              </span>
              <div className={styles.actions}>
                <button type="button" className="button secondary" onClick={() => toggleBlock(user)}>
                  {user.is_blocked ? "Разблокировать" : "Блокировать"}
                </button>
                <button
                  type="button"
                  className="button"
                  onClick={() => {
                    setTempPassword(null);
                    setResetTarget(user);
                  }}
                >
                  Сбросить пароль
                </button>
              </div>
            </div>
          ))}
        </section>
      )}
      <Dialog
        open={Boolean(resetTarget)}
        title="Сброс пароля"
        description={resetTarget ? `Пользователь: ${resetTarget.email}` : undefined}
        onClose={() => {
          setResetTarget(null);
          setTempPassword(null);
        }}
        actions={
          <>
            <button
              type="button"
              className="button secondary"
              onClick={() => {
                setResetTarget(null);
                setTempPassword(null);
              }}
            >
              Закрыть
            </button>
            <button type="button" className="button" onClick={resetPassword}>
              Создать пароль
            </button>
          </>
        }
      >
        {tempPassword ? (
          <div className={styles.passwordBox}>
            <div>
              <div className={styles.passwordLabel}>Временный пароль</div>
              <div className={styles.passwordValue}>{tempPassword}</div>
            </div>
            <button type="button" className="button secondary" onClick={handleCopyPassword}>
              Копировать
            </button>
          </div>
        ) : (
          <p className="muted">
            Система создаст временный пароль. Сообщите его пользователю безопасным способом.
          </p>
        )}
      </Dialog>
    </div>
  );
}
