"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { API_URL, setMustChangePassword } from "../../../lib/api";
import { useAuth } from "../../providers/AuthProvider";
import { useToast } from "../../components/ToastProvider";

export default function LoginPage() {
  const router = useRouter();
  const { updateToken, refreshMe } = useAuth();
  const { pushToast } = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setError(data?.detail ?? "Ошибка входа");
        setLoading(false);
        return;
      }
      const data = (await response.json()) as {
        access_token: string;
        must_change_password: boolean;
      };
      updateToken(data.access_token);
      setMustChangePassword(data.must_change_password);
      await refreshMe();
      if (data.must_change_password) {
        pushToast("Необходимо сменить пароль", "info");
        router.push("/profile");
      } else {
        router.push("/chat");
      }
    } catch {
      setError("Не удалось выполнить вход");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="page">
      <div className="stack">
        <span className="badge">Вход в систему</span>
        <h1>Добро пожаловать обратно</h1>
        <p className="muted">Используйте корпоративный доступ для входа.</p>
      </div>
      <form onSubmit={handleSubmit} className="stack">
        <label className="stack">
          <span>Электронная почта</span>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            className="input"
          />
        </label>
        <label className="stack">
          <span>Пароль</span>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            className="input"
          />
        </label>
        <button type="submit" className="button" disabled={loading}>
          {loading ? "Входим..." : "Войти"}
        </button>
      </form>
      <p className="muted">
        Нет доступа или забыли пароль? Обратитесь к администратору.
      </p>
      {error && <p className="error-text">{error}</p>}
    </main>
  );
}
