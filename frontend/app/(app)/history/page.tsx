"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { apiFetch } from "../../../lib/api";
import { useAuthGuard } from "../../hooks/useAuthGuard";
import PageHeader from "../../components/PageHeader";
import EmptyState from "../../components/EmptyState";
import ErrorState from "../../components/ErrorState";
import LoadingSkeleton from "../../components/LoadingSkeleton";
import styles from "./page.module.css";

type HistoryItem = {
  query_id: number;
  question: string;
  created_at: string;
  latest_version_no: number;
};

export default function HistoryPage() {
  const { ready } = useAuthGuard();
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready) {
      return;
    }
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await apiFetch("/history?limit=20");
        if (!response.ok) {
          const data = await response.json().catch(() => null);
          setError(data?.detail ?? "Не удалось загрузить историю");
          setLoading(false);
          return;
        }
        const data = (await response.json()) as HistoryItem[];
        setItems(data);
      } catch {
        setError("Не удалось загрузить историю");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [ready]);

  if (!ready) {
    return null;
  }

  return (
    <div className="page">
      <PageHeader
        title="История запросов"
        subtitle="Просматривайте предыдущие ответы и версии генераций."
      />
      {loading && <LoadingSkeleton lines={4} />}
      {error && <ErrorState title="История недоступна" description={error} />}
      {!loading && !error && items.length === 0 && (
        <EmptyState
          title="История пока пустая"
          description="Сделайте запрос в чате — записи появятся здесь автоматически."
        />
      )}
      {items.length > 0 && (
        <div className={styles.list}>
          {items.map((item) => (
            <article key={item.query_id} className={styles.card}>
              <div className={styles.cardHeader}>
                <h3>{item.question}</h3>
                <span className={styles.version}>вер. {item.latest_version_no}</span>
              </div>
              <p className={styles.meta}>{new Date(item.created_at).toLocaleString()}</p>
              <Link href={`/history/${item.query_id}`} className={styles.link}>
                Открыть детали
              </Link>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
