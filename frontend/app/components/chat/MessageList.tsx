import MessageBubble from "./MessageBubble";
import styles from "./MessageList.module.css";
import { EvidenceSource } from "../EvidencePanel";

type Answer = {
  version_id: number;
  version_no: number;
  answer: string;
  created_at?: string;
  sources: EvidenceSource[];
};

type MessageListProps = {
  answers: Answer[];
  activeAnswerId: number | null;
  onSelectAnswer: (versionId: number) => void;
  onCitationClick: (sourceNo: number, versionId: number) => void;
};

export default function MessageList({
  answers,
  activeAnswerId,
  onSelectAnswer,
  onCitationClick,
}: MessageListProps) {
  return (
    <div className={styles.list}>
      {answers.map((answer) => (
        <MessageBubble
          key={answer.version_id}
          title={`Версия ответа ${answer.version_no}`}
          createdAt={answer.created_at}
          answer={answer.answer}
          sources={answer.sources}
          onCitationClick={(sourceNo) => onCitationClick(sourceNo, answer.version_id)}
          onSelect={() => onSelectAnswer(answer.version_id)}
          isActive={activeAnswerId === answer.version_id}
        />
      ))}
    </div>
  );
}
