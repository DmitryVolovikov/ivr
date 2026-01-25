"use client";

import styles from "./CitationText.module.css";

type CitationTextProps = {
  text: string;
  onCitationClick: (sourceNo: number) => void;
};

export default function CitationText({ text, onCitationClick }: CitationTextProps) {
  const parts = text.split(/(\[S\d+\])/g);

  return (
    <span className={styles.text}>
      {parts.map((part, index) => {
        const match = part.match(/\[S(\d+)\]/);
        if (!match) {
          return <span key={`text-${index}`}>{part}</span>;
        }
        const sourceNo = Number(match[1]);
        return (
          <button
            key={`cite-${index}-${sourceNo}`}
            type="button"
            className={styles.citation}
            onClick={(event) => {
              event.stopPropagation();
              onCitationClick(sourceNo);
            }}
          >
            {part}
          </button>
        );
      })}
    </span>
  );
}
