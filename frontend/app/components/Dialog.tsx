"use client";

import { ReactNode, useEffect } from "react";

import styles from "./Dialog.module.css";

type DialogProps = {
  open: boolean;
  title: string;
  description?: string;
  children?: ReactNode;
  actions?: ReactNode;
  onClose: () => void;
};

export default function Dialog({ open, title, description, children, actions, onClose }: DialogProps) {
  useEffect(() => {
    if (!open) {
      return;
    }
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div
      className={styles.backdrop}
      role="dialog"
      aria-modal="true"
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div className={styles.dialog}>
        <div className={styles.header}>
          <h2>{title}</h2>
          {description && <p className={styles.description}>{description}</p>}
        </div>
        {children && <div className={styles.body}>{children}</div>}
        {actions && <div className={styles.actions}>{actions}</div>}
      </div>
    </div>
  );
}
