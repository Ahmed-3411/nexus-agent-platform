"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { Icons } from "@/components/icons";

const navigation = [
  { href: "/dashboard", label: "Overview", icon: Icons.grid },
  { href: "/workflows/new", label: "Create", icon: Icons.plus },
  { href: "/health", label: "Health", icon: Icons.pulse },
  { href: "/benchmark", label: "Benchmarks", icon: Icons.chart },
];

export function Brand() {
  return (
    <Link href="/dashboard" className="group inline-flex items-center gap-3" aria-label="Nexus home">
      <span className="relative grid h-9 w-9 place-items-center overflow-hidden rounded-xl bg-brand text-white shadow-[0_8px_22px_rgba(37,99,235,0.22)] transition-transform duration-200 group-hover:-translate-y-0.5">
        <span className="absolute -right-2 -top-2 h-6 w-6 rounded-full bg-cyan" />
        <Icons.workflow className="relative h-4 w-4" />
      </span>
      <span><span className="block text-sm font-bold tracking-[0.16em] text-ink">NEXUS</span><span className="block text-[9px] font-medium uppercase tracking-[0.19em] text-slate-400">Agent platform</span></span>
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { ready, authenticated, role, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  if (!ready || !authenticated) {
    return <div className="grid min-h-screen place-items-center bg-canvas"><div className="h-8 w-8 animate-spin rounded-full border-2 border-brand/20 border-t-brand" /></div>;
  }

  return (
    <div className="min-h-screen text-ink">
      <header className="sticky top-0 z-30 border-b border-line/70 bg-canvas/[0.88] backdrop-blur-2xl supports-[backdrop-filter]:bg-canvas/[0.78]">
        <div className="mx-auto flex h-[72px] max-w-[1480px] items-center justify-between px-4 sm:px-6 lg:px-10">
          <Brand />
          <nav className="hidden items-center gap-1 rounded-full border border-line/70 bg-white/[0.82] p-1.5 shadow-[0_5px_18px_rgba(18,24,38,0.035)] backdrop-blur-xl md:flex">
            {navigation.map(({ href, label }) => {
              const active = pathname === href || (href === "/dashboard" && pathname.startsWith("/workflows/") && pathname !== "/workflows/new");
              return <Link key={href} href={href} className={`rounded-full px-4 py-2 text-xs font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand/10 ${active ? "bg-brand text-white shadow-[0_6px_18px_rgba(37,99,235,0.20)]" : "text-slate-500 hover:bg-brandSoft/80 hover:text-brand"}`}>{label}</Link>;
            })}
          </nav>
          <div className="hidden items-center gap-3 md:flex">
            <div className="rounded-full border border-line/70 bg-white/80 px-3.5 py-2 text-[11px] font-medium capitalize text-slate-600 shadow-[0_4px_14px_rgba(18,24,38,0.035)]"><span className="mr-2 inline-block h-1.5 w-1.5 rounded-full bg-emerald-500 ring-4 ring-emerald-500/10" />{role?.replaceAll("_", " ")}</div>
            <button onClick={signOut} className="grid h-9 w-9 place-items-center rounded-full text-slate-400 transition hover:bg-white hover:text-ink" title="Sign out"><Icons.logout className="h-4 w-4" /></button>
          </div>
          <button onClick={() => setOpen((value) => !value)} className="grid h-10 w-10 place-items-center rounded-full border border-line bg-white text-slate-600 md:hidden" aria-label="Toggle navigation"><Icons.menu className="h-5 w-5" /></button>
        </div>
        {open && <div className="border-t border-line bg-white px-4 py-4 md:hidden"><nav className="grid gap-1">{navigation.map(({ href, label, icon: NavIcon }) => <Link key={href} href={href} onClick={() => setOpen(false)} className="flex items-center gap-3 rounded-xl px-3 py-3 text-sm text-slate-600 hover:bg-canvas"><NavIcon className="h-4 w-4" />{label}</Link>)}</nav><button onClick={signOut} className="mt-2 flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm text-slate-600 hover:bg-canvas"><Icons.logout className="h-4 w-4" />Sign out</button></div>}
      </header>
      <main className="mx-auto max-w-[1480px] px-4 py-9 sm:px-6 sm:py-11 lg:px-10 lg:py-14">{children}</main>
    </div>
  );
}

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow: string; title: string; description: string; actions?: React.ReactNode }) {
  return (
    <div className="mb-10 flex flex-col justify-between gap-7 lg:flex-row lg:items-end">
      <div className="max-w-4xl">
        <p className="eyebrow mb-3">{eyebrow}</p>
        <h1 className="text-4xl font-semibold leading-[1.04] tracking-[-0.05em] text-ink sm:text-5xl lg:text-[3.5rem]">{title}</h1>
        <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-500 sm:text-base">{description}</p>
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-3">{actions}</div>}
    </div>
  );
}
