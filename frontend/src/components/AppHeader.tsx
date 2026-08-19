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
    <header className="app-header">
      <div>
        <h1>{title}</h1>
        <nav className="app-nav">
          <Link href="/units">Einheiten</Link>
          <Link href="/history">Verlauf</Link>
          <Link href="/settings">Einstellungen</Link>
          {user?.is_admin && <Link href="/admin/users">Benutzer</Link>}
        </nav>
      </div>
      <div className="header-actions">
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
