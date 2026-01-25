"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { apiFetch } from "../../../../lib/api";
import { useAuthGuard } from "../../../hooks/useAuthGuard";
import PageHeader from "../../../components/PageHeader";
import EvidencePanel, { EvidenceSource } from "../../../components/EvidencePanel";
import CitationText from "../../../components/CitationText";
import LoadingSkeleton from "../../../components/LoadingSkeleton";
import ErrorState from "../../../components/ErrorState";
import EmptyState from "../../../components/EmptyState";
import { useToast } from "../../../components/ToastProvider";
import styles from "./page.module.css";

type Version = {
  version_id: number;
  version_no: number;
  answer: string;
  created_at: string;
  sources: EvidenceSource[];
};

type RerunResponse = {
  version_id: number;
  version_no: number;
  answer: string;
  sources: EvidenceSource[];
};

type HistoryDetail = {
  query_id: number;
  question: string;
  versions: Version[];
};

export default function HistoryDetailPage() {
  const { ready } = useAuthGuard();
  const { pushToast } = useToast();
  const params = useParams<{ query_id: string }>();
  const [detail, setDetail] = useState<HistoryDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rerunLoading, setRerunLoading] = useState(false);
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);
  const [activeSourceNo, setActiveSourceNo] = useState<number | null>(null);

  const loadDetail = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch(`/history/${params.query_id}`);
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setError(data?.detail ?? "Не удалось загрузить историю");
        setLoading(false);
        return;
      }
      const data = (await response.json()) as HistoryDetail;
      setDetail(data);
      if (data.versions.length > 0) {
        const latest = data.versions[data.versions.length - 1];
        setSelectedVersionId(latest.version_id);
        setActiveSourceNo(latest.sources[0]?.source_no ?? null);
      }
    } catch {
      setError("Не удалось загрузить историю");
    } finally {
      setLoading(false);
    }
  }, [params.query_id]);

  useEffect(() => {
    if (!ready) {
      return;
    }
    loadDetail();
  }, [ready, loadDetail]);

  const handleRerun = async () => {
    if (!detail) {
      return;
    }
    setRerunLoading(true);
    try {
      const response = await apiFetch(`/rag/rerun?query_id=${detail.query_id}`, { method: "POST" });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        pushToast(data?.detail ?? "Не удалось пересчитать ответ", "error");
        setRerunLoading(false);
        return;
      }
      const data = (await response.json()) as RerunResponse;
      await loadDetail();
      setSelectedVersionId(data.version_id);
      setActiveSourceNo(data.sources[0]?.source_no ?? null);
      pushToast("Создана новая версия ответа", "success");
    } catch {
      pushToast("Не удалось пересчитать ответ", "error");
    } finally {
      setRerunLoading(false);
    }
  };

  const handleExport = async (versionId: number) => {
    try {
      const response = await apiFetch(`/export/${versionId}.pdf`);
      if (!response.ok) {
        pushToast("Не удалось экспортировать PDF", "error");
        return;
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      window.open(url, "_blank");
      setTimeout(() => window.URL.revokeObjectURL(url), 10000);
    } catch {
      pushToast("Не удалось экспортировать PDF", "error");
    }
  };

  const selectedVersion = useMemo(() => {
    if (!detail?.versions.length) {
      return null;
    }
    return detail.versions.find((version) => version.version_id === selectedVersionId) ??
      detail.versions[detail.versions.length - 1];
  }, [detail, selectedVersionId]);

  const sources = selectedVersion?.sources ?? [];

  if (!ready) {
    return null;
  }

  return (
    <div className={styles.layout}>
      <section className="page">
        <PageHeader
          title="История запроса"
          subtitle="Сравните версии ответа и выгрузите результат в PDF."
          actions={
            <button type="button" className="button" onClick={handleRerun} disabled={rerunLoading}>
              {rerunLoading ? "Пересчитываем..." : "Пересчитать ответ"}
            </button>
          }
        />
        {loading && <LoadingSkeleton lines={4} />}
        {error && <ErrorState title="История недоступна" description={error} />}
        {!loading && !error && !detail && (
          <EmptyState title="Запрос не найден" description="Проверьте корректность ссылки." />
        )}
        {detail && (
          <div className={styles.detail}>
            <div className={styles.questionCard}>
              <span className="badge">Запрос</span>
              <h2>{detail.question}</h2>
            </div>
            <div className={styles.versions}>
              {detail.versions.map((version) => (
                <article
                  key={version.version_id}
                  className={`${styles.versionCard} ${
                    selectedVersion?.version_id === version.version_id ? styles.active : ""
                  }`}
                  onClick={() => {
                    setSelectedVersionId(version.version_id);
                    setActiveSourceNo(version.sources[0]?.source_no ?? null);
                  }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      setSelectedVersionId(version.version_id);
                      setActiveSourceNo(version.sources[0]?.source_no ?? null);
                    }
                  }}
                >
                  <header className={styles.versionHeader}>
                    <div>
                      <h3>Версия {version.version_no}</h3>
                      <span className={styles.versionMeta}>
                        {new Date(version.created_at).toLocaleString()}
                      </span>
                    </div>
                    <button
                      type="button"
                      className="button secondary"
                      onClick={(event) => {
                        event.stopPropagation();
                        handleExport(version.version_id);
                      }}
                    >
                      Экспорт PDF
                    </button>
                  </header>
                  <CitationText text={version.answer} onCitationClick={setActiveSourceNo} />
                </article>
              ))}
            </div>
          </div>
        )}
      </section>
      <EvidencePanel
        sources={sources}
        activeSourceNo={activeSourceNo}
        onSelect={setActiveSourceNo}
      />
    </div>
  );
}
