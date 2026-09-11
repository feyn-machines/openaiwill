import { getLocale } from "@/lib/i18n";
import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Will AI Kill Your Idea?", template: "%s | WillAI" },
  description: "Every AI update could change your answer. Check your idea against what AI platforms already do and track what changes.",
};

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const { language, t } = await getLocale();
  return (
    <html lang={language}>
      <body>
        <header className="header wrap">
          <Link href="/" className="brand" aria-label="AgentHowTo home">agent<span>howto</span><span className="brand-dot">.</span></Link>
          <nav aria-label="Main navigation"><Link href="/updates">{t("AI Updates")}</Link><Link href="/check" className="nav-cta">{t("Check your idea ↗")}</Link></nav>
        </header>
        <main className="wrap">{children}</main>
        <footer className="footer wrap"><span>{t("WillAI · Before you build.")}</span><span>{t("Evidence first. Opinions that can change.")}</span></footer>
      </body>
    </html>
  );
}
