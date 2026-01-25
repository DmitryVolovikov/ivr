"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { API_URL } from "../../../lib/api";
import { useToast } from "../../components/ToastProvider";

export default function RegisterPage() {
  const router = useRouter();
  const { pushToast } = useToast();
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          display_name: displayName,
          password,
          confirm_password: confirmPassword,
        }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setError(data?.detail ?? "Ошибка регистрации");
        setLoading(false);
        return;
      }
      pushToast("Регистрация успешна", "success");
      router.push("/login");
    } catch {
      setError("Не удалось завершить регистрацию");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="page">
      <div className="stack">
        <span className="badge">Регистрация</span>
        <h1>Создайте аккаунт</h1>
        <p className="muted">Заполните данные, чтобы получить доступ.</p>
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
          <span>Имя</span>
          <input
            type="text"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
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
        <label className="stack">
          <span>Подтвердите пароль</span>
          <input
            type="password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            required
            className="input"
          />
        </label>
        <button type="submit" className="button" disabled={loading}>
          {loading ? "Создаём..." : "Зарегистрироваться"}
        </button>
      </form>
      {error && <p className="error-text">{error}</p>}
    </main>
  );
}
