"use client";

import { useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";

import { getMustChangePassword } from "../../lib/api";
import { useAuth } from "../providers/AuthProvider";

export type AuthGuardOptions = {
  allowMustChange?: boolean;
};

export function useAuthGuard(options: AuthGuardOptions = {}) {
  const router = useRouter();
  const { me, token, ready } = useAuth();
  const mustChange = Boolean(getMustChangePassword() || me?.must_change_password);

  useEffect(() => {
    if (!ready) {
      return;
    }
    if (!token) {
      router.push("/login");
      return;
    }
    if (me?.is_blocked) {
      router.push("/blocked");
      return;
    }
    if (!options.allowMustChange && mustChange) {
      router.push("/profile");
    }
  }, [ready, token, me, mustChange, options.allowMustChange, router]);

  const canFetch = useMemo(() => {
    if (!ready || !token) {
      return false;
    }
    if (me?.is_blocked) {
      return false;
    }
    if (!options.allowMustChange && mustChange) {
      return false;
    }
    return true;
  }, [ready, token, me, mustChange, options.allowMustChange]);

  return {
    ready: canFetch,
    token,
    me,
    mustChange,
  };
}
