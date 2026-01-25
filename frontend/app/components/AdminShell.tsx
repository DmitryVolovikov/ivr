"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "../providers/AuthProvider";
import styles from "./AdminShell.module.css";

const adminLinks = [
  { href: "/admin", label: "Обзор" },
  { href: "/admin/documents", label: "Документы" },
  { href: "/admin/moderation", label: "Модерация" },
  { href: "/admin/users", label: "Пользователи" },
];

export default function AdminShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { logout } = useAuth();

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <div>
            <div className={styles.brandTitle}>Администрирование</div>
            <div className={styles.brandSubtitle}>База знаний лицея</div>
          </div>
        </div>
        <nav className={styles.nav}>
          {adminLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`${styles.navLink} ${
                pathname === link.href || pathname.startsWith(`${link.href}/`) ? styles.active : ""
              }`}
            >
              {link.label}
            </Link>
          ))}
          <Link href="/chat" className={styles.navLink}>
            Вернуться в чат
          </Link>
        </nav>
        <button type="button" className="button secondary" onClick={logout}>
          Выйти
        </button>
      </aside>
      <main className={styles.content}>{children}</main>
    </div>
  );
}
