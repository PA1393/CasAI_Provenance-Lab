type Props = {
  className?: string;
};

/**
 * The CasAI mark: a DNA double helix interrupted mid-strand by an open pair of
 * scissors — the product in one glyph, an edit made to a sequence.
 *
 * Inline SVG rather than an image file so it stays crisp at any size and takes
 * its colours from the theme: the helix inherits the green accent, the scissors
 * the foreground, so the cut reads as the subject rather than the backdrop.
 *
 * Two details keep it legible at nav size (24px): the base-pair rungs are drawn
 * only where the strands are furthest apart, and the scissors are stroked twice
 * — once fat in the background colour, then again on top — so the blades punch
 * a clean gap through the strands they cross instead of muddying into them.
 */
export function LogoMark({ className }: Props) {
  return (
    <svg viewBox="0 0 32 32" fill="none" aria-hidden="true" className={className}>
      <g
        className="text-accent"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      >
        <path d="M9 3C9 11 23 12 23 16s-14 5-14 13" />
        <path d="M23 3c0 8-14 9-14 13s14 5 14 13" />
      </g>

      <g
        className="text-accent"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        opacity="0.4"
      >
        <path d="M9.9 5.6h12.2" />
        <path d="M9.9 26.4h12.2" />
      </g>

      <g fill="none" strokeLinecap="round">
        <g className="text-bg" stroke="currentColor" strokeWidth="4.5">
          <path d="M10.5 11.5 21.5 20" />
          <path d="M21.5 11.5 10.5 20" />
          <circle cx="9.6" cy="21.4" r="1.8" />
          <circle cx="22.4" cy="21.4" r="1.8" />
        </g>
        <g className="text-text" stroke="currentColor" strokeWidth="1.8">
          <path d="M10.5 11.5 21.5 20" />
          <path d="M21.5 11.5 10.5 20" />
          <circle cx="9.6" cy="21.4" r="1.8" />
          <circle cx="22.4" cy="21.4" r="1.8" />
        </g>
      </g>
    </svg>
  );
}
