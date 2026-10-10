"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SectionCard } from "./SectionCard";

export function AdminSignIn({ busy, message, onSignIn }: { busy: boolean; message?: string; onSignIn: (email: string, password: string) => Promise<void> }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  return <main className="admin-auth"><SectionCard title="AURA Admin" description="Sign in with your Aura account. Administrator permission is required."><form className="settings-form" onSubmit={event => { event.preventDefault(); const credential = password; setPassword(""); void onSignIn(email, credential); }}><label htmlFor="admin-email">Email address<Input id="admin-email" type="email" autoComplete="username" required maxLength={254} value={email} onChange={event => setEmail(event.target.value)} disabled={busy}/></label><label htmlFor="admin-password">Password<Input id="admin-password" type="password" autoComplete="current-password" required value={password} onChange={event => setPassword(event.target.value)} disabled={busy}/></label>{message && <p role="alert">{message}</p>}<Button type="submit" className="gradient-button" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</Button></form></SectionCard></main>;
}
