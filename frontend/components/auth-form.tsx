"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { Brand } from "@/components/app-shell";
import { Icons } from "@/components/icons";
import { api, ApiError } from "@/lib/api";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const registering = mode === "register";

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const response = registering ? await api.register(email, password, fullName) : await api.login(email, password);
      signIn(response);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-canvas px-5 py-8 text-ink">
      <div className="pointer-events-none absolute -left-28 top-20 h-[30rem] w-[30rem] rounded-full bg-cyan/10 blur-[100px]" />
      <div className="pointer-events-none absolute -right-36 bottom-0 h-[34rem] w-[34rem] rounded-full bg-brand/10 blur-[110px]" />
      <div className="relative mx-auto flex min-h-[calc(100vh-4rem)] max-w-7xl flex-col">
        <Brand />
        <div className="grid flex-1 items-center gap-16 py-12 lg:grid-cols-[1.2fr_.8fr]">
          <section className="hidden max-w-3xl lg:block">
            <p className="eyebrow">Secure agent operations</p>
            <h1 className="mt-5 text-6xl font-semibold leading-[1.02] tracking-[-0.055em] xl:text-7xl">Turn complex work into <span className="bg-gradient-to-r from-brand via-[#3B82F6] to-cyan bg-clip-text text-transparent">trusted outcomes.</span></h1>
            <p className="mt-7 max-w-xl text-lg leading-8 text-slate-500">Plan, govern, approve, and inspect enterprise AI workflows from one considered control surface.</p>
            <div className="mt-12 flex gap-10">{["Policy governed", "Human controlled", "Audit ready"].map((item, index) => <div key={item}><p className="text-2xl font-semibold text-ink">0{index + 1}</p><p className="mt-1 text-xs uppercase tracking-[.14em] text-slate-400">{item}</p></div>)}</div>
          </section>

          <section className="rounded-[32px] border border-white bg-white/90 p-7 shadow-soft backdrop-blur-xl sm:p-10">
            <div className="mb-8 lg:hidden"><p className="eyebrow">Secure agent operations</p></div>
            <p className="section-label">{registering ? "Start your workspace" : "Secure access"}</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-[-.035em] text-ink">{registering ? "Create an account" : "Welcome back"}</h2>
            <p className="mt-3 text-sm leading-6 text-slate-500">{registering ? "Your account starts with the least-privilege analyst role." : "Sign in to enter the agent operations workspace."}</p>
            <form className="mt-8 space-y-5" onSubmit={submit}>
              {registering && <label className="block"><span className="mb-2 block text-xs font-semibold text-slate-600">Full name <span className="font-normal text-slate-400">(optional)</span></span><input className="field" value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Alex Morgan" autoComplete="name" /></label>}
              <label className="block"><span className="mb-2 block text-xs font-semibold text-slate-600">Email address</span><input className="field" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@company.com" type="email" autoComplete="email" required /></label>
              <label className="block"><span className="mb-2 block text-xs font-semibold text-slate-600">Password</span><input className="field" value={password} onChange={(event) => setPassword(event.target.value)} placeholder={registering ? "Minimum 8 characters" : "Enter your password"} type="password" minLength={registering ? 8 : undefined} autoComplete={registering ? "new-password" : "current-password"} required /></label>
              {error && <div role="alert" className="rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-700 ring-1 ring-inset ring-rose-600/10">{error}</div>}
              <button className="btn-primary mt-2 w-full py-3" disabled={loading}>{loading ? <><span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />Please wait</> : <>{registering ? "Create account" : "Sign in"}<Icons.arrow className="h-4 w-4" /></>}</button>
            </form>
            <p className="mt-7 text-center text-sm text-slate-500">{registering ? "Already have an account?" : "New to Nexus?"} <Link className="font-semibold text-brand hover:text-brandDark" href={registering ? "/login" : "/register"}>{registering ? "Sign in" : "Create account"}</Link></p>
          </section>
        </div>
      </div>
    </main>
  );
}
