export default function BlockedPage() {
  return (
    <main className="page">
      <div className="stack">
        <span className="badge">Доступ ограничен</span>
        <h1>Аккаунт заблокирован</h1>
        <p className="muted">
          Обратитесь к администратору, чтобы восстановить доступ к системе.
        </p>
      </div>
    </main>
  );
}
