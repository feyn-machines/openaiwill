"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

/**
 * Scroll-driven reveal, in the two shapes DESIGN.md's homepage exception allows.
 *
 * `once` plays when the section first enters and never plays again, because a
 * reveal that replays turns any re-read into a flicker - which is the thing the
 * site-wide rule exists to prevent. `scrub` is bound to scroll position and is
 * therefore continuous in both directions, so it cannot flicker either; it is
 * allowed only where the movement IS the content (the time axis, and the grid
 * filling up).
 *
 * Content is never gated on any of this. The DOM is complete and in its final
 * state on the server; these hooks add a class or a number that the CSS uses to
 * animate INTO that state. With JavaScript off, or with prefers-reduced-motion,
 * nothing here runs and the reader gets the finished screen.
 */

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Adds `className` once the element has been seen. Never removes it. */
export function useSeen<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [seen, setSeen] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    // Nothing to do under reduced motion, and nothing to fix up: with no
    // `data-seen` attribute no animation rule matches, so the element is
    // already in its finished state. Setting state here would only cause a
    // second render to reach the same pixels.
    if (prefersReducedMotion() || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          setSeen(true);
          // Play once: stop watching the moment it has played, so scrolling
          // back up cannot start it again.
          observer.disconnect();
        }
      },
      { rootMargin: "0px 0px -15% 0px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return { ref, seen };
}

/**
 * How far the reader has scrolled through this element, 0 at its top edge
 * reaching the bottom of the viewport, 1 once its bottom edge has reached the
 * top. Returns 1 - the finished state - until it is measured.
 */
export function useScrub<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [progress, setProgress] = useState(1);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    // `progress` already starts at 1, the finished state, so reduced motion
    // means leaving it alone rather than setting it again.
    if (prefersReducedMotion()) return;

    let frame = 0;
    const measure = () => {
      frame = 0;
      const box = node.getBoundingClientRect();
      const viewport = window.innerHeight || 1;
      // Full travel is the element's own height plus one viewport, so a short
      // element still gets the whole scroll to fill rather than snapping.
      const travelled = viewport - box.top;
      const total = box.height + viewport;
      const value = total <= 0 ? 1 : travelled / total;
      setProgress(Math.min(1, Math.max(0, value)));
    };
    const onScroll = () => {
      if (frame) return;
      frame = requestAnimationFrame(measure);
    };

    // Measured on the next frame rather than inline: a synchronous setState in
    // an effect body renders twice to reach the same value, and the first
    // paint is already correct because `progress` starts at its finished state.
    frame = requestAnimationFrame(measure);
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      if (frame) cancelAnimationFrame(frame);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, []);

  return { ref, progress };
}

/** A section that adds `data-seen` once it has been scrolled into. */
export function Screen({
  id,
  className,
  children,
}: {
  id?: string;
  className?: string;
  children: ReactNode;
}) {
  const { ref, seen } = useSeen<HTMLElement>();
  return (
    <section id={id} ref={ref} className={className} data-seen={seen ? "true" : undefined}>
      {children}
    </section>
  );
}
