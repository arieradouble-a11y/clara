"use client";

// The single announcement channel for the whole app.
//
// Rules this component exists to keep (see docs/research/a11y-layer-design-brief.md):
//   1. A live region must be in the tree and EMPTY before content lands in it.
//      Rendering a region together with its text announces nothing — the most
//      common silent failure, and it looks correct in review.
//   2. Never put live semantics on the content itself. A re-rendered or streamed
//      container fires one announcement per mutation, uncoalesced, and floods
//      the user.
//   3. One live region per page: simultaneous updates to two are undefined in
//      ARIA, and in practice only one is spoken.
//
// So result panels and error boxes are plain content, and anything worth
// speaking is written here briefly, then cleared.

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";

const Ctx = createContext<(msg: string) => void>(() => {});

export function AnnouncerProvider({ children }: { children: ReactNode }) {
  const [text, setText] = useState("");
  const clearRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const setRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const announce = useCallback((msg: string) => {
    if (!msg) return;
    if (clearRef.current) clearTimeout(clearRef.current);
    if (setRef.current) clearTimeout(setRef.current);
    setText("");                       // screen readers suppress identical repeats
    // A separate task, not requestAnimationFrame: rAF never runs in a hidden or
    // throttled tab, which swallows the announcement entirely.
    setRef.current = setTimeout(() => {
      setText(msg);
      clearRef.current = setTimeout(() => setText(""), 3000);
    }, 60);
  }, []);

  useEffect(() => () => {
    if (clearRef.current) clearTimeout(clearRef.current);
    if (setRef.current) clearTimeout(setRef.current);
  }, []);

  return (
    <Ctx.Provider value={announce}>
      {/* Mounted once, at app root, empty. */}
      <div
        aria-live="polite"
        aria-atomic="false"
        style={{
          position: "absolute", width: 1, height: 1, margin: -1, padding: 0,
          overflow: "hidden", clipPath: "inset(50%)", whiteSpace: "nowrap", border: 0,
        }}
      >
        {text}
      </div>
      {children}
    </Ctx.Provider>
  );
}

export const useAnnounce = () => useContext(Ctx);
