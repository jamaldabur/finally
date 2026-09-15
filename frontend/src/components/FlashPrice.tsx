"use client";

import { useEffect, useRef, useState } from "react";
import type { ChangeDirection } from "@/lib/types";

interface FlashPriceProps {
  price: number;
  direction: ChangeDirection;
  format: (value: number) => string;
  className?: string;
}

// The digits stay colored green/red for the last known direction (a live quote
// reads as stale otherwise between ticks), while a brief background flash marks
// the instant a genuinely new price arrives (direction !== "unchanged"), fading
// out over ~400ms. A repeat heartbeat carrying the same price must not re-flash.
export default function FlashPrice({ price, direction, format, className }: FlashPriceProps) {
  const [flashKey, setFlashKey] = useState(0);
  const [flashClass, setFlashClass] = useState<string | null>(null);
  const [lastDirection, setLastDirection] = useState<"up" | "down" | null>(null);
  const lastPriceRef = useRef(price);

  useEffect(() => {
    if (direction === "unchanged" || price === lastPriceRef.current) {
      lastPriceRef.current = price;
      return;
    }
    lastPriceRef.current = price;
    setLastDirection(direction);
    setFlashClass(direction === "up" ? "flash-up" : "flash-down");
    setFlashKey((k) => k + 1);
  }, [price, direction]);

  const textColorClass = lastDirection === "up" ? "text-up" : lastDirection === "down" ? "text-down" : "";

  return (
    <span
      key={flashKey}
      className={`${className ?? ""} ${textColorClass} ${flashClass ?? ""} rounded-md px-1 transition-colors`}
      onAnimationEnd={() => setFlashClass(null)}
    >
      {format(price)}
    </span>
  );
}
