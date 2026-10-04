"use client";

import { useEffect, useRef } from "react";
import { authClient } from "@/lib/auth-client";
import { bilingual, type Language } from "@/lib/i18n";
import styles from "./account.module.css";
import { useMe } from "./me";

const copy = bilingual({
  en: { signIn: "Sign in", signOut: "Sign out", account: "Account" },
  "zh-CN": { signIn: "登录", signOut: "退出", account: "账号" },
});

function initials(name: string) {
  return (name.trim().slice(0, 1) || "?").toUpperCase();
}

export function AccountMenu({ language, enabled }: { language: Language; enabled: boolean }) {
  const { state, me } = useMe();
  const menu = useRef<HTMLDetailsElement>(null);
  const c = copy[language];

  useEffect(() => {
    const close = () => menu.current?.removeAttribute("open");
    const onPointer = (event: PointerEvent) => {
      if (menu.current && !menu.current.contains(event.target as Node)) close();
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  if (!enabled) return null;
  if (state === "loading") return <div className={styles.root} data-account-menu aria-hidden="true"><span className={styles.placeholder} /></div>;
  if (!me.enabled) return null;

  if (!me.user) {
    return (
      <div className={styles.root} data-account-menu>
        <button
          type="button"
          className={styles.signIn}
          onClick={() => void authClient.signIn.social({ provider: "google", callbackURL: window.location.pathname + window.location.search })}
        >
          {c.signIn}
        </button>
      </div>
    );
  }

  const { user } = me;
  return (
    <div className={styles.root} data-account-menu>
      <details ref={menu} className={styles.details}>
        <summary className={styles.summary} aria-label={`${c.account}: ${user.name}`}>
          {user.image ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img className={styles.avatar} src={user.image} alt={user.name} width={28} height={28} referrerPolicy="no-referrer" />
          ) : (
            <span className={styles.avatar} aria-hidden="true">{initials(user.name)}</span>
          )}
        </summary>
        <div className={styles.panel}>
          <p className={styles.name}>{user.name}</p>
          <button
            type="button"
            className={styles.item}
            onClick={() => void authClient.signOut().finally(() => window.location.reload())}
          >
            {c.signOut}
          </button>
        </div>
      </details>
    </div>
  );
}
