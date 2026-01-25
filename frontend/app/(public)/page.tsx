import Link from "next/link";

export default function HomePage() {
  return (
    <main className="page">
      <div className="stack">
        <span className="badge">База знаний лицея</span>
        <h1>Справочная система лицея</h1>
        <p className="muted">
          Войдите, чтобы задавать вопросы, искать документы и работать с историей запросов.
        </p>
      </div>
      <div className="grid-2">
        <Link href="/login" className="button">
          Войти
        </Link>
        <Link href="/register" className="button secondary">
          Регистрация
        </Link>
      </div>
    </main>
  );
}
