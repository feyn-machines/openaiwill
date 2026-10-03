"use client";

import { useEffect, useRef, type CSSProperties, type ReactNode } from "react";
import frame from "./section.module.css";

export type Tone = "base" | "ink" | "green";

/**
 * One block of the homepage, and the only place its motion is decided. Every
 * module is wrapped in this, so every module moves the same way:
 *
 *   - The block pins when its end reaches the bottom of the viewport, and the
 *     next block slides up over it as one piece. While it is being covered it
 *     dims and draws back a little.
 *   - A soft wash of the block's ground runs ahead of its top edge.
 *   - A large word crosses behind it for as long as it is on screen.
 *   - Its headline lights from left to right, and its figure rises as a whole.
 *
 * The script only writes numbers; the stylesheet turns them into movement:
 *   --p      0 as the top edge enters the viewport, 1 once the block is well in
 *   --v      0 entering, 1 gone: the whole pass across the screen
 *   --cover  how much of the screen the next block has taken
 *   --stick  where the block pins, so a block taller than the screen is read to its end first
 *
 * A block given `travel` is a scene: it pins and the scroll that follows is
 * handed to the module as `--h` (0..1), to spend on movement across the screen
 * instead of down it. The same number is sent as a `scene` event for modules
 * that turn it into state. `chapter` names the block for the rail.
 *
 * Without the script, or under reduced motion, the defaults leave every block
 * in place, lit and unpinned.
 */
export function Reveal({ children, tone = "base", ghost, travel, chapter }: { children: ReactNode; tone?: Tone; ghost?: string; travel?: number; chapter?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const pin = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let frameId = 0;
    const last: Record<string, string> = {};
    const set = (name: string, value: string) => { if (last[name] !== value) { last[name] = value; node.style.setProperty(name, value); } };
    const clamp = (v: number) => Math.min(1, Math.max(0, v));
    const measure = () => {
      frameId = 0;
      const vh = window.innerHeight, height = node.offsetHeight;
      set("--stick", `${Math.min(0, vh - height)}px`);
      const rect = node.getBoundingClientRect();
      // A scene: the block is taller than what it shows by the distance it travels while pinned.
      const shown = pin.current?.offsetHeight ?? height, distance = height - shown, pinTop = Math.min(0, vh - shown);
      const h = distance > 4 ? clamp((pinTop - rect.top) / distance) : 0;
      set("--pin-top", `${pinTop}px`);
      if (last["--h"] !== h.toFixed(3)) node.dispatchEvent(new CustomEvent("scene", { detail: h }));
      set("--h", h.toFixed(3));
      // The last block cannot travel as far as the others: the page ends first.
      const left = document.documentElement.scrollHeight - vh - window.scrollY;
      const reach = Math.max(1, vh - rect.top + left);
      set("--p", clamp((vh - rect.top) / Math.min(vh * 0.85, reach * 0.9)).toFixed(3));
      const next = node.nextElementSibling;
      const cover = next ? clamp(1 - next.getBoundingClientRect().top / vh) : 0;
      set("--cover", cover.toFixed(3));
      // Pinned blocks stop moving, so the pass keeps counting through the cover.
      set("--v", clamp(((vh - rect.top) / (vh + height)) * 0.8 + cover * 0.2).toFixed(3));
    };
    const request = () => { if (!frameId) frameId = requestAnimationFrame(measure); };
    const observer = new ResizeObserver(request);
    observer.observe(node);
    node.dataset.live = "";
    measure();
    window.addEventListener("scroll", request, { passive: true });
    window.addEventListener("resize", request);
    return () => {
      cancelAnimationFrame(frameId);
      observer.disconnect();
      window.removeEventListener("scroll", request);
      window.removeEventListener("resize", request);
      delete node.dataset.live;
      for (const name of Object.keys(last)) node.style.removeProperty(name);
    };
  }, []);

  return (
    <div ref={ref} className={frame.reveal} data-tone={tone} data-chapter={chapter} data-travel={travel || undefined} style={travel ? ({ "--travel": `${travel}vh` } as CSSProperties) : undefined}>
      <div className={frame.wash} aria-hidden="true" />
      <div className={frame.inner}>
        <div ref={pin} className={frame.pin}>
          {ghost && <div className={frame.ghostBox} aria-hidden="true"><div className={frame.ghost}>{ghost}</div></div>}
          {children}
        </div>
        {travel ? <div className={frame.travel} /> : null}
      </div>
    </div>
  );
}
