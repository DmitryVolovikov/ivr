import type { ReactNode } from "react";

import styles from "./ErrorState.module.css";

type ErrorStateProps = {
  title: string;
  description?: string;
  action?: ReactNode;
};

export default function ErrorState({ title, description, action }: ErrorStateProps) {
  return (
    <div className={styles.error}>
      <div>
        <h3>{title}</h3>
        {description && <p>{description}</p>}
      </div>
      {action && <div className={styles.action}>{action}</div>}
    </div>
  );
}
