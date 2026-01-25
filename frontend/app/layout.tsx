import type { ReactNode } from "react";

import "./globals.css";
import AppProviders from "./providers/AppProviders";

export const metadata = {
  title: "База знаний лицея",
  description: "Поиск и чат по документам лицея",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <body>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
