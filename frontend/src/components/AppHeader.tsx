"use client";

import Link from "next/link";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useChildPreview } from "@/lib/childPreview";
import { logout, type User } from "@/lib/api";

type AppHeaderProps = {
  user?: User | null;
  /** Kurzer Seitentitel unter der Navigation (nicht für lange Einheitstitel). */
  title?: string;
};

export function AppHeader({ user, title }: AppHeaderProps) {
  const { asChild, canPreview, preview, togglePreview } = useChildPreview(user);

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
        <nav className="app-nav" aria-label="Hauptnavigation">
          <Link href="/units">Einheiten</Link>
          {user && !asChild && (user.child_count ?? 0) > 0 && <Link href="/parent">Kinder</Link>}
          <Link href="/history">Verlauf</Link>
          <Link href="/settings">Einstellungen</Link>
          {user?.is_admin && !asChild && <Link href="/admin/users">Benutzer</Link>}
          {user?.is_admin && !asChild && <Link href="/admin/golden-set">Golden Set</Link>}
          {user?.is_admin && !asChild && <Link href="/admin/ai-overview">KI-Übersicht</Link>}
          {user?.is_admin && !asChild && <Link href="/admin/unit-report">Qualitätsreport</Link>}
        </nav>
        <div className="header-actions">
          <ThemeToggle />
          {canPreview && (
            <button
              type="button"
              className={preview ? "child-preview-toggle active" : "child-preview-toggle"}
              aria-pressed={preview}
              title="Navigation und Seitenaufbau wie für ein Kind anzeigen"
              onClick={togglePreview}
            >
              Kind-Ansicht
            </button>
          )}
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
      {preview && (
        <p className="child-preview-banner" role="status">
          Kind-Ansicht aktiv — so sieht die Gliederung für Kinder aus. Admin-Seiten bleiben per URL
          erreichbar.
        </p>
      )}
      {title ? (
        <div className="page-heading">
          <h1>{title}</h1>
        </div>
      ) : null}
    </header>
  );
}
