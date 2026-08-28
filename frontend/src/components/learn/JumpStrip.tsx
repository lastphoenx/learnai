"use client";

import { useEffect, useState, type CSSProperties } from "react";

const WINDOW_DESKTOP = 10;
const WINDOW_PHONE = 6;

function useJumpWindowSize() {
  const [size, setSize] = useState(WINDOW_DESKTOP);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 639px)");
    const apply = () => setSize(mq.matches ? WINDOW_PHONE : WINDOW_DESKTOP);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);
  return size;
}

type Props = {
  count: number;
  currentIndex: number;
  disabled?: boolean;
  ariaLabel: string;
  windowSize?: number;
  itemKey?: (index: number) => string;
  itemClassName: (index: number) => string;
  itemTitle: (index: number) => string;
  itemStyle?: (index: number) => CSSProperties | undefined;
  onSelect: (index: number) => void;
};

export function JumpStrip({
  count,
  currentIndex,
  disabled,
  ariaLabel,
  windowSize: requestedWindow,
  itemKey,
  itemClassName,
  itemTitle,
  itemStyle,
  onSelect,
}: Props) {
  const autoSize = useJumpWindowSize();
  const windowSize = requestedWindow ?? autoSize;
  const [start, setStart] = useState(0);
  const size = Math.min(windowSize, Math.max(0, count));
  const needsPager = count > windowSize;

  useEffect(() => {
    setStart((prev) => {
      const maxStart = Math.max(0, count - windowSize);
      const clamped = Math.min(Math.max(0, prev), maxStart);
      if (currentIndex >= clamped && currentIndex < clamped + windowSize) return clamped;
      const next = currentIndex - Math.floor((Math.min(windowSize, count) - 1) / 2);
      return Math.max(0, Math.min(next, maxStart));
    });
  }, [currentIndex, count, windowSize]);

  function page(direction: -1 | 1) {
    const maxStart = Math.max(0, count - windowSize);
    setStart((prev) => Math.max(0, Math.min(prev + direction * windowSize, maxStart)));
  }

  const end = Math.min(count, start + size);

  return (
    <div className="quiz-nav-pager">
      {needsPager && (
        <button
          type="button"
          className="quiz-nav-page"
          disabled={disabled || start <= 0}
          aria-label="Vorherige Nummern"
          onClick={() => page(-1)}
        >
          ‹
        </button>
      )}
      <div className="quiz-nav-strip" role="tablist" aria-label={ariaLabel}>
        {Array.from({ length: Math.max(0, end - start) }, (_, offset) => {
          const i = start + offset;
          const title = itemTitle(i);
          return (
            <button
              key={itemKey ? itemKey(i) : i}
              type="button"
              className={itemClassName(i)}
              style={itemStyle?.(i)}
              disabled={disabled}
              title={title}
              aria-label={title}
              aria-current={i === currentIndex ? "true" : undefined}
              onClick={() => onSelect(i)}
            >
              {i + 1}
            </button>
          );
        })}
      </div>
      {needsPager && (
        <button
          type="button"
          className="quiz-nav-page"
          disabled={disabled || start + windowSize >= count}
          aria-label="Weitere Nummern"
          onClick={() => page(1)}
        >
          ›
        </button>
      )}
    </div>
  );
}
