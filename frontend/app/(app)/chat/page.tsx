"use client";

import { FormEvent, useMemo, useState } from "react";

import { apiFetch } from "../../../lib/api";
import { useAuthGuard } from "../../hooks/useAuthGuard";
import { useToast } from "../../components/ToastProvider";
import EvidencePanel, { EvidenceSource } from "../../components/EvidencePanel";
import ChatComposer from "../../components/chat/ChatComposer";
import MessageList from "../../components/chat/MessageList";
import PageHeader from "../../components/PageHeader";
import ErrorState from "../../components/ErrorState";
import EmptyState from "../../components/EmptyState";
import styles from "./page.module.css";

type Answer = {
  query_id: number;
  version_id: number;
  version_no: number;
  answer: string;
  sources: EvidenceSource[];
  created_at?: string;
};

export default function ChatPage() {
  const { ready } = useAuthGuard();
  const { pushToast } = useToast();
  const [question, setQuestion] = useState("");
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeSourceNo, setActiveSourceNo] = useState<number | null>(null);
  const [activeAnswerId, setActiveAnswerId] = useState<number | null>(null);

  const currentQueryId = answers[answers.length - 1]?.query_id;
  const activeAnswer =
    answers.find((answer) => answer.version_id === activeAnswerId) ??
    answers[answers.length - 1];

  const handleAsk = async (event?: FormEvent) => {
    event?.preventDefault();
    if (!question.trim()) {
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const response = await apiFetch("/rag/ask", {
        method: "POST",
        body: JSON.stringify({ question }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setError(data?.detail ?? "Не удалось получить ответ");
        setLoading(false);
        return;
      }
      const data = (await response.json()) as Answer;
      setAnswers([data]);
      setActiveSourceNo(data.sources[0]?.source_no ?? null);
      setActiveAnswerId(data.version_id);
      setQuestion("");
    } catch {
      setError("Не удалось получить ответ");
    } finally {
      setLoading(false);
    }
  };

  const handleRerun = async () => {
    if (!currentQueryId) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch(`/rag/rerun?query_id=${currentQueryId}`, { method: "POST" });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setError(data?.detail ?? "Не удалось пересчитать ответ");
        setLoading(false);
        return;
      }
      const data = (await response.json()) as Answer;
      setAnswers((prev) => [...prev, data]);
      setActiveSourceNo(data.sources[0]?.source_no ?? null);
      setActiveAnswerId(data.version_id);
      pushToast("Создана новая версия ответа", "success");
    } catch {
      setError("Не удалось пересчитать ответ");
    } finally {
      setLoading(false);
    }
  };

  const onCitationClick = (sourceNo: number, versionId: number) => {
    setActiveAnswerId(versionId);
    setActiveSourceNo(sourceNo);
  };

  const sources = useMemo(() => activeAnswer?.sources ?? [], [activeAnswer]);

  if (!ready) {
    return null;
  }

  return (
    <div className={styles.layout}>
      <section className="page">
        <PageHeader
          title="Чат по документам лицея"
          subtitle="Ответы формируются только на основе документов и содержат ссылки на источники."
        />
        <ChatComposer
          question={question}
          onQuestionChange={setQuestion}
          onSubmit={handleAsk}
          onRerun={handleRerun}
          isSending={loading}
          canRerun={Boolean(currentQueryId)}
        />
        {error && (
          <ErrorState
            title="Ответ не получен"
            description={error}
            action={
              <button type="button" className="button secondary" onClick={() => handleAsk()}>
                Повторить запрос
              </button>
            }
          />
        )}
        {answers.length === 0 && !error && (
          <EmptyState
            title="Запросов пока нет"
            description="Сформулируйте вопрос — ответ появится в ленте и справа отобразятся источники."
          />
        )}
        {answers.length > 0 && (
          <MessageList
            answers={answers}
            activeAnswerId={activeAnswerId}
            onSelectAnswer={(versionId) => {
              setActiveAnswerId(versionId);
              const target = answers.find((answer) => answer.version_id === versionId);
              setActiveSourceNo(target?.sources[0]?.source_no ?? null);
            }}
            onCitationClick={onCitationClick}
          />
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
