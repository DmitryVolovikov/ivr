"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetch, getMustChangePassword, setMustChangePassword } from "../../../lib/api";
import { useAuthGuard } from "../../hooks/useAuthGuard";
import { useAuth } from "../../providers/AuthProvider";
import PageHeader from "../../components/PageHeader";
import ErrorState from "../../components/ErrorState";
import EmptyState from "../../components/EmptyState";
import { useToast } from "../../components/ToastProvider";
import styles from "./page.module.css";

export default function ProfilePage() {
  const router = useRouter();
  const { ready, mustChange } = useAuthGuard({ allowMustChange: true });
  const { me, refreshMe } = useAuth();
  const { pushToast } = useToast();
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) {
      return;
    }
    refreshMe();
  }, [ready, refreshMe]);

  const handleChangePassword = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      const response = await apiFetch("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword,
          confirm_password: confirmPassword,
        }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setError(data?.detail ?? "Не удалось сменить пароль");
        return;
      }
      setMustChangePassword(false);
      await refreshMe();
      pushToast("Пароль обновлён", "success");
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
      router.push("/chat");
    } catch {
      setError("Не удалось сменить пароль");
    }
  };

  if (!ready) {
    return null;
  }

  return (
    <div className="page">
      <PageHeader
        title="Профиль"
        subtitle="Управляйте данными и сменой пароля."
      />
      {(getMustChangePassword() || mustChange) && (
        <ErrorState
          title="Нужно сменить пароль"
          description="Для продолжения работы обновите пароль и войдите заново."
        />
      )}
      {!me && (
        <EmptyState
          title="Профиль недоступен"
          description="Не удалось загрузить данные пользователя."
        />
      )}
      {me && (
        <section className={styles.profileCard}>
          <div>
            <div className={styles.label}>Почта</div>
            <div className={styles.value}>{me.email}</div>
          </div>
          <div>
            <div className={styles.label}>Имя</div>
            <div className={styles.value}>{me.display_name}</div>
          </div>
        </section>
      )}
      <section className={styles.formCard}>
        <h2>Сменить пароль</h2>
        <form onSubmit={handleChangePassword} className="stack">
          <label className="stack">
            <span>Старый пароль</span>
            <input
              type="password"
              value={oldPassword}
              onChange={(event) => setOldPassword(event.target.value)}
              required
              className="input"
            />
          </label>
          <label className="stack">
            <span>Новый пароль</span>
            <input
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              required
              className="input"
            />
          </label>
          <label className="stack">
            <span>Подтвердите новый пароль</span>
            <input
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
              className="input"
            />
          </label>
          <button type="submit" className="button">
            Сменить пароль
          </button>
        </form>
        {error && <p className="error-text">{error}</p>}
      </section>
    </div>
  );
}
