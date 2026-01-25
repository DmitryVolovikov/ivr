"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "../providers/AuthProvider";
import styles from "./AppShell.module.css";

const links = [
  { href: "/chat", label: "Чат" },
  { href: "/search", label: "Поиск" },
  { href: "/history", label: "История" },
  { href: "/profile", label: "Профиль" },
];

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { me, logout } = useAuth();

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <span className={styles.brandMark}>Л</span>
          <div>
            <div className={styles.brandTitle}>База знаний лицея</div>
            <div className={styles.brandSubtitle}>Поиск и чат по документам</div>
          </div>
        </div>
        <nav className={styles.nav}>
          {links.map((link) => (
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
          {me?.is_admin && (
            <Link
              href="/admin"
              className={`${styles.navLink} ${pathname.startsWith("/admin") ? styles.active : ""}`}
            >
              Администрирование
            </Link>
          )}
        </nav>
        <div className={styles.sidebarFooter}>
          <div className={styles.userMeta}>
            <div className={styles.userName}>{me?.display_name ?? "Пользователь"}</div>
            <div className={styles.userEmail}>{me?.email ?? ""}</div>
          </div>
          <button type="button" className="button secondary" onClick={logout}>
            Выйти
          </button>
        </div>
      </aside>
      <div className={styles.main}>
        <header className={styles.header}>
          <div>
            <div className={styles.headerLabel}>База знаний</div>
            <div className={styles.headerTitle}>База знаний лицея</div>
          </div>
        </header>
        <main className={styles.content}>{children}</main>
      </div>
    </div>
  );
}
