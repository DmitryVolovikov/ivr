import type { ReactNode } from "react";

import styles from "./public-layout.module.css";

export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <div className={styles.wrapper}>
      <div className={styles.card}>{children}</div>
    </div>
  );
}
