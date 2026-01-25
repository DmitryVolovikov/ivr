"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";

import { apiFetch } from "../../../lib/api";
import { useAuthGuard } from "../../hooks/useAuthGuard";
import PageHeader from "../../components/PageHeader";
import ErrorState from "../../components/ErrorState";
import EmptyState from "../../components/EmptyState";
import LoadingSkeleton from "../../components/LoadingSkeleton";
import styles from "./page.module.css";

type Result = {
  doc_id: number;
  title: string | null;
  chunk_id: number;
  snippet: string;
  score: number;
};

export default function SearchPage() {
  const { ready } = useAuthGuard();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Result[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (event: FormEvent) => {
    event.preventDefault();
    if (!query.trim()) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch(`/search?q=${encodeURIComponent(query)}&limit=20`);
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setError(data?.detail ?? "Ошибка поиска");
        setLoading(false);
        return;
      }
      const data = (await response.json()) as Result[];
      setResults(data);
    } catch {
      setError("Не удалось выполнить поиск");
    } finally {
      setLoading(false);
    }
  };

  if (!ready) {
    return null;
  }

  return (
    <div className="page">
      <PageHeader
        title="Поиск по документам"
        subtitle="Введите запрос — система подберёт релевантные фрагменты."
      />
      <form onSubmit={handleSearch} className={styles.form}>
        <input
          type="text"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Введите запрос"
          className="input"
        />
        <button type="submit" className="button" disabled={loading}>
          {loading ? "Поиск..." : "Найти"}
        </button>
      </form>
      {loading && <LoadingSkeleton lines={4} />}
      {error && <ErrorState title="Поиск недоступен" description={error} />}
      {!loading && !error && results.length === 0 && (
        <EmptyState
          title="Совпадений нет"
          description="Уточните формулировку или используйте ключевые слова из документа."
        />
      )}
      {results.length > 0 && (
        <div className={styles.results}>
          {results.map((result) => (
            <article key={`${result.doc_id}-${result.chunk_id}`} className={styles.card}>
              <div className={styles.cardHeader}>
                <h3>{result.title ?? `Документ ${result.doc_id}`}</h3>
                <span className={styles.score}>Релевантность {result.score.toFixed(3)}</span>
              </div>
              <p className={styles.snippet}>{result.snippet}</p>
              <Link href={`/doc/${result.doc_id}?chunk=${result.chunk_id}`} className={styles.link}>
                Открыть фрагмент
              </Link>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
