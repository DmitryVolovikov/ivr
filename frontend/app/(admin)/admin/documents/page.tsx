"use client";

import { FormEvent, useEffect, useState } from "react";

import { apiFetch } from "../../../../lib/api";
import { useAdminGuard } from "../../../hooks/useAdminGuard";
import PageHeader from "../../../components/PageHeader";
import Dialog from "../../../components/Dialog";
import ErrorState from "../../../components/ErrorState";
import EmptyState from "../../../components/EmptyState";
import LoadingSkeleton from "../../../components/LoadingSkeleton";
import { useToast } from "../../../components/ToastProvider";
import styles from "./page.module.css";

type Document = {
  id: number;
  original_name: string;
  mime_type: string;
  title: string | null;
  status: string;
  error_reason: string | null;
  reject_reason: string | null;
  created_at: string;
  updated_at: string;
};

export default function AdminDocumentsPage() {
  const { ready, isAdmin } = useAdminGuard();
  const { pushToast } = useToast();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Document | null>(null);

  const loadDocuments = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch("/admin/documents");
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

  const handleUpload = async (event: FormEvent) => {
    event.preventDefault();
    if (!file) {
      setError("Выберите файл");
      return;
    }
    setError(null);
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    if (title) {
      formData.append("title", title);
    }
    try {
      const response = await apiFetch("/admin/documents/upload", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setError(data?.detail ?? "Ошибка загрузки");
        setUploading(false);
        return;
      }
      setFile(null);
      setTitle("");
      pushToast("Документ загружен", "success");
      await loadDocuments();
    } catch {
      setError("Ошибка загрузки");
    } finally {
      setUploading(false);
    }
  };

  const handleReindex = async (docId: number) => {
    try {
      const response = await apiFetch(`/admin/documents/${docId}/reindex`, { method: "POST" });
      if (!response.ok) {
        pushToast("Не удалось переиндексировать документ", "error");
        return;
      }
      pushToast("Переиндексация запущена", "success");
      await loadDocuments();
    } catch {
      pushToast("Не удалось переиндексировать документ", "error");
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) {
      return;
    }
    try {
      const response = await apiFetch(`/admin/documents/${deleteTarget.id}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        pushToast("Не удалось удалить документ", "error");
        return;
      }
      pushToast("Документ удалён", "success");
      await loadDocuments();
    } catch {
      pushToast("Не удалось удалить документ", "error");
    } finally {
      setDeleteTarget(null);
    }
  };

  if (!ready || !isAdmin) {
    return null;
  }

  return (
    <div className="page">
      <PageHeader
        title="Документы"
        subtitle="Контроль загрузок, индексов и статусов документов."
      />
      <section className={styles.uploadCard}>
        <h2>Загрузка документа</h2>
        <form onSubmit={handleUpload} className="stack">
          <label className="stack">
            <span>Файл</span>
            <input
              type="file"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              required
            />
          </label>
          <label className="stack">
            <span>Заголовок (опционально)</span>
            <input
              type="text"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              className="input"
            />
          </label>
          <button type="submit" className="button" disabled={uploading}>
            {uploading ? "Загружаем..." : "Загрузить"}
          </button>
        </form>
      </section>
      {error && <ErrorState title="Действие не выполнено" description={error} />}
      {loading && <LoadingSkeleton lines={4} />}
      {!loading && !error && documents.length === 0 && (
        <EmptyState
          title="Документы не найдены"
          description="Добавьте первый документ, чтобы запустить индексирование."
        />
      )}
      {documents.length > 0 && (
        <section className={styles.tableCard}>
          <h2>Реестр документов</h2>
          <div className={styles.table}>
            <div className={styles.tableHeader}>
              <span>ИД</span>
              <span>Название</span>
              <span>Статус</span>
              <span>Причина</span>
              <span>Действия</span>
            </div>
            {documents.map((doc) => (
              <div key={doc.id} className={styles.tableRow}>
                <span>{doc.id}</span>
                <span>{doc.title ?? doc.original_name}</span>
                <span className={styles.status}>{doc.status}</span>
                <span className={styles.reason}>{doc.error_reason ?? doc.reject_reason ?? "—"}</span>
                <div className={styles.actions}>
                  <button
                    type="button"
                    className="button secondary"
                    onClick={() => handleReindex(doc.id)}
                  >
                    Реиндексация
                  </button>
                  <button
                    type="button"
                    className="button danger"
                    onClick={() => setDeleteTarget(doc)}
                  >
                    Удалить
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
      <Dialog
        open={Boolean(deleteTarget)}
        title="Удалить документ"
        description="Документ и связанные фрагменты будут удалены без возможности восстановления."
        onClose={() => setDeleteTarget(null)}
        actions={
          <>
            <button type="button" className="button secondary" onClick={() => setDeleteTarget(null)}>
              Отмена
            </button>
            <button type="button" className="button danger" onClick={handleDelete}>
              Удалить
            </button>
          </>
        }
      />
    </div>
  );
}
