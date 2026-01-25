"use client";

import { ReactNode } from "react";

import { AuthProvider } from "./AuthProvider";
import { ToastProvider } from "../components/ToastProvider";

export default function AppProviders({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <ToastProvider>{children}</ToastProvider>
    </AuthProvider>
  );
}
