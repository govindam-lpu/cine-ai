"use client";

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

import type { ScrapeJob, UserProfile } from "@/types/user";

type UserStore = {
  userId: string | null;
  user: UserProfile | null;
  activeJob: ScrapeJob | null;
  setUserId: (userId: string | null) => void;
  setUser: (user: UserProfile | null) => void;
  setActiveJob: (job: ScrapeJob | null) => void;
  clear: () => void;
};

export const useUserStore = create<UserStore>()(
  persist(
    (set) => ({
      userId: null,
      user: null,
      activeJob: null,
      setUserId: (userId) => set({ userId }),
      setUser: (user) => set({ user }),
      setActiveJob: (activeJob) => set({ activeJob }),
      clear: () => set({ userId: null, user: null, activeJob: null })
    }),
    {
      name: "cinerex-user-store",
      storage: createJSONStorage(() => localStorage)
    }
  )
);
