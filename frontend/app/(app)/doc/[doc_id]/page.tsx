"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";

import { apiFetch } from "../../../../lib/api";
import { useAuthGuard } from "../../../hooks/useAuthGuard";
import PageHeader from "../../../components/PageHeader";
import LoadingSkeleton from "../../../components/LoadingSkeleton";
import ErrorState from "../../../components/ErrorState";
import { useToast } from "../../../components/ToastProvider";
import styles from "./page.module.css";

type ChunkPreview = {
  chunk_id: number;
  chunk_index: number;
  snippet: string;
};

type DocumentView = {
  doc_id: number;
  title: string | null;
  original_name: string;
  mime_type: string;
  status: string;
  created_at: string;
  chunks_preview: ChunkPreview[];
};

type ChunkNeighbor = {
  chunk_id: number;
  chunk_index: number;
  snippet: string;
};

type ChunkDetail = {
  doc_id: number;
  chunk_id: number;
  chunk_index: number;
  text: string;
  snippet: string;
  neighbors: ChunkNeighbor[];
};

export default function DocPage() {
  const { ready } = useAuthGuard();
  const { pushToast } = useToast();
  const params = useParams<{ doc_id: string }>();
  const searchParams = useSearchParams();
  const [doc, setDoc] = useState<DocumentView | null>(null);
  const [chunk, setChunk] = useState<ChunkDetail | null>(null);
  const [loadingDoc, setLoadingDoc] = useState(true);
  const [loadingChunk, setLoadingChunk] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const chunkId = searchParams.get("chunk");

  useEffect(() => {
    if (!ready) {
      return;
    }
    const loadDoc = async () => {
      setLoadingDoc(true);
      setError(null);
      try {
        const response = await apiFetch(`/docs/${params.doc_id}`);
        if (!response.ok) {
          const data = await response.json().catch(() => null);
          setError(data?.detail ?? "Не удалось загрузить документ");
          setLoadingDoc(false);
          return;
        }
        const data = (await response.json()) as DocumentView;
        setDoc(data);
      } catch {
        setError("Не удалось загрузить документ");
      } finally {
        setLoadingDoc(false);
      }
    };
    loadDoc();
  }, [ready, params.doc_id]);

  useEffect(() => {
    if (!ready || !chunkId) {
      setChunk(null);
      return;
    }
    const loadChunk = async () => {
      setLoadingChunk(true);
      try {
        const response = await apiFetch(`/docs/${params.doc_id}/chunk/${chunkId}`);
        if (!response.ok) {
          setLoadingChunk(false);
          return;
        }
        const data = (await response.json()) as ChunkDetail;
        setChunk(data);
      } catch {
        pushToast("Не удалось загрузить фрагмент", "error");
      } finally {
        setLoadingChunk(false);
      }
    };
    loadChunk();
  }, [ready, params.doc_id, chunkId, pushToast]);

  const handleDownload = async () => {
    if (!doc) {
      return;
    }
    try {
      const response = await apiFetch(`/docs/${doc.doc_id}/download`);
      if (!response.ok) {
        pushToast("Не удалось открыть оригинал", "error");
        return;
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      window.open(url, "_blank");
      setTimeout(() => window.URL.revokeObjectURL(url), 10000);
    } catch {
      pushToast("Не удалось открыть оригинал", "error");
    }
  };

  if (!ready) {
    return null;
  }

  return (
    <div className="page">
      <PageHeader
        title="Просмотр документа"
        subtitle="Просматривайте метаданные и переходите между фрагментами."
        actions={
          <button type="button" className="button secondary" onClick={handleDownload}>
            Открыть оригинал
          </button>
        }
      />
      {loadingDoc && <LoadingSkeleton lines={4} />}
      {error && <ErrorState title="Документ недоступен" description={error} />}
      {doc && (
        <section className={styles.docMeta}>
          <div>
            <div className={styles.label}>Название</div>
            <div className={styles.value}>{doc.title ?? doc.original_name}</div>
          </div>
          <div>
            <div className={styles.label}>Статус</div>
            <div className={styles.value}>{doc.status}</div>
          </div>
          <div>
            <div className={styles.label}>Дата загрузки</div>
            <div className={styles.value}>{new Date(doc.created_at).toLocaleString()}</div>
          </div>
        </section>
      )}
      {chunk && (
        <section className={styles.chunkCard}>
          <header className={styles.chunkHeader}>
            <h2>Фрагмент #{chunk.chunk_index}</h2>
            <span className={styles.chunkMeta}>ИД {chunk.chunk_id}</span>
          </header>
          {loadingChunk ? (
            <LoadingSkeleton lines={6} />
          ) : (
            <pre className={styles.chunkText}>{chunk.text}</pre>
          )}
          {chunk.neighbors.length > 0 && (
            <div className={styles.neighbors}>
              <h3 className={styles.subTitle}>Соседние фрагменты</h3>
              <div className={styles.neighborList}>
                {chunk.neighbors.map((neighbor) => (
                  <Link
                    key={neighbor.chunk_id}
                    href={`/doc/${params.doc_id}?chunk=${neighbor.chunk_id}`}
                    className={styles.neighborCard}
                  >
                    <div className={styles.neighborTitle}>Фрагмент #{neighbor.chunk_index}</div>
                    <p className={styles.neighborSnippet}>{neighbor.snippet}</p>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </section>
      )}
      {doc && (
        <section className={styles.previewSection}>
          <h3 className={styles.subTitle}>Превью фрагментов</h3>
          <div className={styles.previewList}>
            {doc.chunks_preview.map((preview) => (
              <Link
                key={preview.chunk_id}
                href={`/doc/${params.doc_id}?chunk=${preview.chunk_id}`}
                className={styles.previewCard}
              >
                <div className={styles.neighborTitle}>Фрагмент #{preview.chunk_index}</div>
                <p className={styles.neighborSnippet}>{preview.snippet}</p>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
