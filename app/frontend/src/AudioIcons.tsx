import type { ReactNode } from "react";

/** Scalable, consistent-size pictograms instead of platform-dependent emoji glyphs. */
const graphics: Record<string, ReactNode> = {
  Vocals: <><rect x="12" y="3" width="8" height="17" rx="4"/><path d="M7 14v2a9 9 0 0 0 18 0v-2M16 25v4m-6 0h12"/></>,
  Drums: <><ellipse cx="16" cy="10" rx="12" ry="5"/><path d="M4 10v11c0 3 5.4 5 12 5s12-2 12-5V10M4 21c0 3 5.4 5 12 5s12-2 12-5M8 15l5 9m11-9-5 9"/><path d="M5 3l22 8M27 3 5 11"/></>,
  Bass: <><path d="M22 3 12 13m11-9 5 5-6 6m-9-2-7 7c-2 2-2 5 0 7s5 2 7 0l7-7"/><path d="m13 13 6 6m-8 1 6 6M21 6l5 5"/></>,
  Guitar: <><path d="m20 3 9 9-4 4-4-4-4 4c1.5 5-2 8-6 10-3 2-7 2-9-1s-1-7 2-9c3-3 6-4 10-3l4-4-3-3z"/><path d="M21 7 10 18m-3 3h.01"/></>,
  Piano: <><rect x="3" y="5" width="26" height="23" rx="2"/><path d="M3 19h26M10 19v9m7-9v9m7-9v9M8 5v13h4V5m5 0v13h4V5"/></>,
  Other: <><path d="M13 6v19a4 4 0 1 1-3-3.9V11l14-3v14a4 4 0 1 1-3-3.9V4z"/></>,
};
export function AudioIcon({kind, size=30}: {kind:string;size?:number}) {
  return <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"
    width={size} height={size} aria-hidden="true" focusable="false" fill="none"
    stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"
    className="audio-stem-pictogram">{graphics[kind] || graphics.Other}</svg>;
}
