"use client";

import Link from "next/link";
import { ThemeToggle } from "@/components/ThemeToggle";
import { logout, type User } from "@/lib/api";

export function AppHeader({ user, title }: { user?: User | null; title: string }) {
  async function onLogout() {
    await logout();
    window.location.href = "/login";
  }

  return (
    <header
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        gap: "1rem",
        marginBottom: "2rem",
      }}
    >
      <div>
        <h1 style={{ margin: 0 }}>{title}</h1>
        <nav style={{ marginTop: "0.5rem", display: "flex", gap: "0.75rem", fontSize: "0.9rem" }}>
          <Link href="/units">Einheiten</Link>
          <Link href="/history">Verlauf</Link>
          <Link href="/settings">Einstellungen</Link>
          {user?.is_admin && <Link href="/admin/users">Benutzer</Link>}
        </nav>
      </div>
      <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
        <ThemeToggle />
        {user && (
          <button type="button" onClick={onLogout}>
            Logout
          </button>
        )}
      </div>
    </header>
  );
}
