import type { Localised, Lang } from "@/content/types";
import styles from "./MapPlaceholder.module.css";

const labels: { x: number; y: number; text: Localised }[] = [
  { x: 548, y: 472, text: { ja: "緑川駅", en: "Midorigawa Sta." } },
  { x: 330, y: 300, text: { ja: "竹林", en: "Bamboo grove" } },
];

/** Static drawing that stands in for the map until Google Maps is integrated. */
export function MapPlaceholder({ lang }: { lang: Lang }) {
  return (
    <svg className={styles.map} viewBox="0 0 1000 1000" aria-hidden="true">
      <rect width="1000" height="1000" fill="var(--map-land)" />

      <g fill="none" stroke="var(--map-contour)" strokeWidth="1.5">
        <path d="M-20 170c120-40 200 30 320 0s190-120 300-140" />
        <path d="M-20 215c130-40 210 34 340 2s200-120 330-146" />
        <path d="M-20 262c140-42 220 38 360 4s215-122 355-150" />
        <path d="M-20 312c150-44 235 42 382 6s230-124 385-154" />
      </g>

      <path
        d="M210 130c80-30 190-20 240 40s10 150-70 170-190-10-225-80 0-110 55-130z"
        fill="var(--map-green)"
      />
      <path
        d="M690 700c70-30 170-10 200 50s-20 130-100 130-150-30-160-90 10-70 60-90z"
        fill="var(--map-green)"
      />

      <g fill="none" stroke="var(--map-road)" strokeLinecap="round" strokeLinejoin="round">
        <g strokeWidth="9">
          <path d="M520 330 640 300l190 50" />
          <path d="M300 440l120 40M420 480l-30 150 120 90" />
          <path d="M640 300l-20 170 60 140 150 40" />
          <path d="M380 340l40 140" />
          <path d="M510 720l-90 180" />
          <path d="M680 610l-160 30" />
        </g>
        <g strokeWidth="16">
          <path d="M-20 400c200-20 360 90 560 70s300-110 480-100" />
          <path d="M500-20c-10 180-120 310-30 500s-20 340 10 540" />
        </g>
      </g>

      <path
        d="M-20 820c130-60 230-60 320-140s170-40 270 30 260 40 450-60"
        fill="none"
        stroke="var(--map-water)"
        strokeWidth="46"
        strokeLinecap="round"
      />

      <path d="M-20 590 1020 250" fill="none" stroke="var(--map-rail)" strokeWidth="5" />
      <path
        d="M-20 590 1020 250"
        fill="none"
        stroke="var(--map-land)"
        strokeWidth="3"
        strokeDasharray="16 16"
      />
      <rect
        x="500"
        y="430"
        width="44"
        height="18"
        rx="3"
        fill="var(--color-ink-soft)"
        transform="rotate(-18 522 439)"
      />

      <g className={styles.labels}>
        {labels.map((label) => (
          <text key={label.x} x={label.x} y={label.y}>
            {label.text[lang]}
          </text>
        ))}
      </g>
    </svg>
  );
}
