"use client";

import { Activity, BookOpen, ClipboardCheck, Gauge, Home, ListChecks, LockKeyhole, Shield, Siren, Wrench } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api, clearToken } from "@/lib/api";
import type { Role, User } from "@/types/api";

const nav = [
  { href: "/", label: "Dashboard", icon: Home, min: "viewer" },
  { href: "/incidents", label: "Incidents", icon: Siren, min: "viewer" },
  { href: "/runbooks", label: "Runbooks", icon: BookOpen, min: "engineer" },
  { href: "/tools", label: "MCP Tools", icon: Wrench, min: "engineer" },
  { href: "/agent-runs", label: "Agent Runs", icon: Activity, min: "engineer" },
  { href: "/approvals", label: "Approvals", icon: ClipboardCheck, min: "incident_commander" },
  { href: "/reports", label: "Reports", icon: ListChecks, min: "viewer" },
  { href: "/evals", label: "Evals", icon: Gauge, min: "admin" },
  { href: "/admin", label: "Admin", icon: Shield, min: "admin" }
] as const;

const rank: Record<Role, number> = { viewer: 1, engineer: 2, incident_commander: 3, admin: 4 };

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.me()
      .then(setUser)
      .catch(() => {
        if (pathname !== "/login") router.replace("/login");
      })
      .finally(() => setLoading(false));
  }, [pathname, router]);

  const visibleNav = useMemo(() => nav.filter((item) => user && rank[user.role] >= rank[item.min]), [user]);

  if (pathname === "/login") return <>{children}</>;
  if (loading) return <div className="p-8 text-sm text-slate-500">Loading secure workspace...</div>;

  return (
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 left-0 w-64 border-r border-line bg-white">
        <div className="border-b border-line px-5 py-5">
          <div className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-md bg-teal text-white"><LockKeyhole size={18} /></span>
            <div>
              <div className="text-sm font-semibold">Incident AI Agent</div>
              <div className="text-xs text-slate-500">Local enterprise demo</div>
            </div>
          </div>
        </div>
        <nav className="space-y-1 p-3">
          {visibleNav.map((item) => {
            const Icon = item.icon;
            const selected = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            return (
              <Link
                className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium ${selected ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"}`}
                href={item.href}
                key={item.href}
              >
                <Icon size={17} />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <main className="ml-64 flex min-h-screen flex-1 flex-col">
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-line bg-white/90 px-6 backdrop-blur">
          <div>
            <div className="text-sm font-semibold text-ink">Enterprise AI Incident Triage & Automation Agent</div>
            <div className="text-xs text-slate-500">Mock-only external actions, approval-gated, fully local</div>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="rounded-md border border-line bg-slate-50 px-3 py-1 text-xs">{user?.email} · {user?.role}</span>
            <button
              className="rounded-md border border-line px-3 py-1 text-xs hover:bg-slate-100"
              onClick={() => {
                clearToken();
                router.replace("/login");
              }}
            >
              Sign out
            </button>
          </div>
        </header>
        <div className="p-6">{children}</div>
      </main>
    </div>
  );
}

