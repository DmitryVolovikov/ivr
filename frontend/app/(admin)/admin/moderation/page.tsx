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

type Document = {
  id: number;
  original_name: string;
  title: string | null;
  status: string;
  created_at: string;
};

export default function AdminModerationPage() {
  const { ready, isAdmin } = useAdminGuard();
  const { pushToast } = useToast();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rejectTarget, setRejectTarget] = useState<Document | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const loadDocuments = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch("/admin/documents?status=review");
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setError(data?.detail ?? "Не удалось загрузить документы");
        setLoading(false);
        return;
      }
      const data = (await response.json()) as Document[];
      setDocuments(data);
    } catch {
      setError("Не удалось загрузить документы");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!ready || !isAdmin) {
      return;
    }
    loadDocuments();
  }, [ready, isAdmin]);

  const handlePublish = async (docId: number) => {
    try {
      const response = await apiFetch(`/admin/documents/${docId}/publish`, { method: "POST" });
      if (!response.ok) {
        pushToast("Не удалось опубликовать документ", "error");
        return;
      }
      pushToast("Документ опубликован", "success");
      await loadDocuments();
    } catch {
      pushToast("Не удалось опубликовать документ", "error");
    }
  };

  const handleReject = async () => {
    if (!rejectTarget || !rejectReason.trim()) {
      return;
    }
    try {
      const response = await apiFetch(`/admin/documents/${rejectTarget.id}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason: rejectReason }),
      });
      if (!response.ok) {
        pushToast("Не удалось отклонить документ", "error");
        return;
      }
      pushToast("Документ отклонён", "success");
      await loadDocuments();
    } catch {
      pushToast("Не удалось отклонить документ", "error");
    } finally {
      setRejectTarget(null);
      setRejectReason("");
    }
  };

  if (!ready || !isAdmin) {
    return null;
  }

  return (
    <div className="page">
      <PageHeader
        title="Модерация"
        subtitle="Проверьте документы перед публикацией в базе знаний."
      />
      {loading && <LoadingSkeleton lines={3} />}
      {error && <ErrorState title="Раздел недоступен" description={error} />}
      {!loading && !error && documents.length === 0 && (
        <EmptyState
          title="Нет документов на модерации"
          description="Новые документы для проверки пока не поступали."
        />
      )}
      {documents.length > 0 && (
        <div className={styles.list}>
          {documents.map((doc) => (
            <article key={doc.id} className={styles.card}>
              <div>
                <h3>{doc.title ?? doc.original_name}</h3>
                <p className={styles.meta}>ИД {doc.id} • {doc.status}</p>
              </div>
              <div className={styles.actions}>
                <button type="button" className="button" onClick={() => handlePublish(doc.id)}>
                  Опубликовать
                </button>
                <button
                  type="button"
                  className="button secondary"
                  onClick={() => {
                    setRejectTarget(doc);
                    setRejectReason("");
                  }}
                >
                  Отклонить
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
      <Dialog
        open={Boolean(rejectTarget)}
        title="Отклонить документ"
        description={rejectTarget ? `Документ: ${rejectTarget.title ?? rejectTarget.original_name}` : undefined}
        onClose={() => setRejectTarget(null)}
        actions={
          <>
            <button type="button" className="button secondary" onClick={() => setRejectTarget(null)}>
              Отмена
            </button>
            <button type="button" className="button danger" onClick={handleReject}>
              Отклонить
            </button>
          </>
        }
      >
        <label className="stack">
          <span>Причина отклонения</span>
          <textarea
            className="textarea"
            value={rejectReason}
            onChange={(event) => setRejectReason(event.target.value)}
            placeholder="Опишите причину отказа"
            required
          />
        </label>
      </Dialog>
    </div>
  );
}
