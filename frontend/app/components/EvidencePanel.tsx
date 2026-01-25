"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { useToast } from "./ToastProvider";
import styles from "./EvidencePanel.module.css";

export type EvidenceSource = {
  source_no: number;
  doc_id: number;
  title: string | null;
  chunk_id: number;
  snippet: string;
};

type EvidencePanelProps = {
  sources: EvidenceSource[];
  activeSourceNo: number | null;
  onSelect: (sourceNo: number) => void;
};

export default function EvidencePanel({ sources, activeSourceNo, onSelect }: EvidencePanelProps) {
  const { pushToast } = useToast();
  const cardRefs = useRef(new Map<number, HTMLDivElement>());
  const [filter, setFilter] = useState<"all" | "selected">("all");

  useEffect(() => {
    if (!activeSourceNo) {
      return;
    }
    const element = cardRefs.current.get(activeSourceNo);
    element?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [activeSourceNo]);

  const handleCopy = async (docId: number, chunkId: number) => {
    const url = `${window.location.origin}/doc/${docId}?chunk=${chunkId}`;
    try {
      await navigator.clipboard.writeText(url);
      pushToast("Ссылка скопирована", "success");
    } catch {
      pushToast("Не удалось скопировать ссылку", "error");
    }
  };

  const sourceList = useMemo(() => sources ?? [], [sources]);
  const filteredSources = useMemo(() => {
    if (filter === "selected") {
      return activeSourceNo ? sourceList.filter((source) => source.source_no === activeSourceNo) : [];
    }
    return sourceList;
  }, [filter, sourceList, activeSourceNo]);

  return (
    <aside className={styles.panel}>
      <div className={styles.panelHeader}>
        <h2 className={styles.title}>Источники</h2>
        <span className={styles.count}>{sourceList.length}</span>
      </div>
      <p className={styles.status}>
        {sourceList.length === 0
          ? "После ответа здесь появятся фрагменты с ссылками."
          : "Нажмите [S#], чтобы подсветить фрагмент."}
      </p>
      {sourceList.length > 0 && (
        <div className={styles.filters}>
          <button
            type="button"
            className={`${styles.filterButton} ${filter === "all" ? styles.filterActive : ""}`}
            onClick={() => setFilter("all")}
          >
            Все
          </button>
          <button
            type="button"
            className={`${styles.filterButton} ${filter === "selected" ? styles.filterActive : ""}`}
            onClick={() => setFilter("selected")}
          >
            Выбранный
          </button>
        </div>
      )}
      {sourceList.length === 0 ? (
        <div className={styles.empty}>Фрагменты появятся после первого ответа.</div>
      ) : filteredSources.length === 0 ? (
        <div className={styles.empty}>Выберите фрагмент в ответе, чтобы показать его здесь.</div>
      ) : (
        <div className={styles.list}>
          {filteredSources.map((source) => (
            <div
              key={source.source_no}
              ref={(node) => {
                if (node) {
                  cardRefs.current.set(source.source_no, node);
                }
              }}
              className={`${styles.card} ${
                activeSourceNo === source.source_no ? styles.active : ""
              }`}
              onClick={() => onSelect(source.source_no)}
              role="button"
              tabIndex={0}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  onSelect(source.source_no);
                }
              }}
            >
              <div className={styles.cardHeader}>
                <span className={styles.sourceIndex}>S{source.source_no}</span>
                <div>
                  <div className={styles.cardTitle}>
                    {source.title ?? `Документ ${source.doc_id}`}
                  </div>
                  <div className={styles.metaLine}>
                    Документ #{source.doc_id} • Фрагмент {source.chunk_id}
                  </div>
                </div>
              </div>
              <p className={styles.snippet}>{source.snippet}</p>
              <div className={styles.cardActions}>
                <Link
                  href={`/doc/${source.doc_id}?chunk=${source.chunk_id}`}
                  className={styles.cardLink}
                >
                  Открыть фрагмент
                </Link>
                <button
                  type="button"
                  className={styles.cardButton}
                  onClick={(event) => {
                    event.stopPropagation();
                    handleCopy(source.doc_id, source.chunk_id);
                  }}
                >
                  Копировать ссылку
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </aside>
  );
}
