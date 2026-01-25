import styles from "./ChatComposer.module.css";

type ChatComposerProps = {
  question: string;
  onQuestionChange: (value: string) => void;
  onSubmit: () => void;
  onRerun: () => void;
  isSending: boolean;
  canRerun: boolean;
};

export default function ChatComposer({
  question,
  onQuestionChange,
  onSubmit,
  onRerun,
  isSending,
  canRerun,
}: ChatComposerProps) {
  return (
    <div className={styles.composer}>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="question">
          Вопрос
        </label>
        <textarea
          id="question"
          className="textarea"
          value={question}
          onChange={(event) => onQuestionChange(event.target.value)}
          placeholder="Например: какие документы нужны для допуска?"
        />
      </div>
      <div className={styles.actions}>
        <button type="button" className="button" onClick={onSubmit} disabled={isSending}>
          {isSending ? "Отправляем..." : "Спросить"}
        </button>
        <button
          type="button"
          className="button secondary"
          onClick={onRerun}
          disabled={isSending || !canRerun}
        >
          Пересчитать ответ
        </button>
      </div>
    </div>
  );
}
