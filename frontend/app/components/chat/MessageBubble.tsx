import CitationText from "../CitationText";
import styles from "./MessageBubble.module.css";
import { EvidenceSource } from "../EvidencePanel";

type MessageBubbleProps = {
  title: string;
  answer: string;
  createdAt?: string;
  sources: EvidenceSource[];
  onCitationClick: (sourceNo: number) => void;
  onSelect: () => void;
  isActive: boolean;
};

export default function MessageBubble({
  title,
  answer,
  createdAt,
  sources,
  onCitationClick,
  onSelect,
  isActive,
}: MessageBubbleProps) {
  return (
    <article
      className={`${styles.bubble} ${isActive ? styles.active : ""}`}
      onClick={onSelect}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === "Enter") {
          onSelect();
        }
      }}
    >
      <header className={styles.header}>
        <div>
          <h3>{title}</h3>
          {createdAt && <span className={styles.timestamp}>{createdAt}</span>}
        </div>
        <span className={styles.sourceCount}>Источники: {sources.length}</span>
      </header>
      <div className={styles.body}>
        <CitationText text={answer} onCitationClick={onCitationClick} />
      </div>
    </article>
  );
}
