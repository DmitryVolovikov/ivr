"use client";

import Link from "next/link";

import { useAdminGuard } from "../../hooks/useAdminGuard";
import PageHeader from "../../components/PageHeader";
import styles from "./page.module.css";

const adminSections = [
  {
    title: "Документы",
    description: "Загрузка, переиндексация и контроль статусов документов.",
    href: "/admin/documents",
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M7 3h7l5 5v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
        />
        <path d="M14 3v5h5" fill="none" stroke="currentColor" strokeWidth="1.6" />
      </svg>
    ),
  },
  {
    title: "Модерация",
    description: "Проверка документов перед публикацией в базе знаний.",
    href: "/admin/moderation",
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M4 7h16M4 12h10M4 17h7"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
        <circle cx="18" cy="12" r="3" fill="none" stroke="currentColor" strokeWidth="1.6" />
      </svg>
    ),
  },
  {
    title: "Пользователи",
    description: "Роли, блокировки и выдача временных паролей.",
    href: "/admin/users",
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
        />
        <path
          d="M4 21a6 6 0 0 1 16 0"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
      </svg>
    ),
  },
];

export default function AdminOverviewPage() {
  const { ready, isAdmin } = useAdminGuard();

  if (!ready || !isAdmin) {
    return null;
  }

  return (
    <div className="page">
      <PageHeader
        title="Администрирование"
        subtitle="Разделы для сопровождения базы знаний лицея."
      />
      <div className={styles.list}>
        {adminSections.map((section) => (
          <Link key={section.href} href={section.href} className={styles.row}>
            <span className={styles.icon}>{section.icon}</span>
            <div className={styles.content}>
              <h3>{section.title}</h3>
              <p>{section.description}</p>
            </div>
            <span className={styles.link}>Открыть</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
