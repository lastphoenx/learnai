"use client";

import Link from "next/link";
import { ThemeToggle } from "@/components/ThemeToggle";
import { logout, type User } from "@/lib/api";

type AppHeaderProps = {
  user?: User | null;
  /** Kurzer Seitentitel unter der Navigation (nicht für lange Einheitstitel). */
  title?: string;
};

export function AppHeader({ user, title }: AppHeaderProps) {
  async function onLogout() {
    await logout();
    window.location.href = "/login";
  }

  return (
    <header className="app-header">
      <div className="app-header-bar">
        <Link href="/units" className="brand">
          LearnAI
        </Link>
        <div className="header-actions">
          <ThemeToggle />
          {user && (
            <>
              {user.display_name ? <span className="header-user">{user.display_name}</span> : null}
              <button type="button" className="btn btn-sm ghost" onClick={onLogout}>
                Logout
              </button>
            </>
          )}
        </div>
      </div>
      <nav className="app-nav" aria-label="Hauptnavigation">
        <Link href="/units">Einheiten</Link>
        {user && !user.is_child && (user.child_count ?? 0) > 0 && <Link href="/parent">Kinder</Link>}
        <Link href="/history">Verlauf</Link>
        <Link href="/settings">Einstellungen</Link>
        {user?.is_admin && <Link href="/admin/users">Benutzer</Link>}
        {user?.is_admin && <Link href="/admin/golden-set">Golden Set</Link>}
      </nav>
      {title ? (
        <div className="page-heading">
          <h1>{title}</h1>
        </div>
      ) : null}
    </header>
  );
}
