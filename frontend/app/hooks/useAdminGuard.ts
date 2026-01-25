"use client";

import { useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";

import { useAuthGuard } from "./useAuthGuard";

export function useAdminGuard() {
  const router = useRouter();
  const guard = useAuthGuard();

  useEffect(() => {
    if (!guard.ready || !guard.me) {
      return;
    }
    if (!guard.me.is_admin) {
      router.push("/chat");
    }
  }, [guard.ready, guard.me, router]);

  const isAdmin = useMemo(() => Boolean(guard.me?.is_admin), [guard.me]);

  return {
    ...guard,
    isAdmin,
  };
}
