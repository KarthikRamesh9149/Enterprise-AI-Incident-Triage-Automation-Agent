"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    try {
      await login(email, password);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-slate-100 p-6">
      <form onSubmit={submit} className="w-full max-w-md rounded-md border border-line bg-white p-6 shadow-soft">
        <h1 className="text-xl font-semibold text-ink">Incident AI Agent</h1>
        <p className="mt-2 text-sm text-slate-500">Sign in with an account provisioned for this environment.</p>
        <label className="mt-6 block text-xs font-semibold text-slate-600">Email</label>
        <input autoComplete="username" className="mt-1 w-full rounded-md border border-line px-3 py-2 text-sm" id="email" name="email" required type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
        <label className="mt-4 block text-xs font-semibold text-slate-600">Password</label>
        <input autoComplete="current-password" className="mt-1 w-full rounded-md border border-line px-3 py-2 text-sm" id="password" name="password" required value={password} onChange={(event) => setPassword(event.target.value)} type="password" />
        {error && <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        <button className="mt-5 w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800">Sign in</button>
      </form>
    </main>
  );
}
