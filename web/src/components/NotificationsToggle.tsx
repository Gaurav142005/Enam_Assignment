"use client";

import { useEffect, useState } from "react";
import { Bell, BellOff, Loader2 } from "lucide-react";
import { api, apiPost } from "@/lib/api";

type Status = "checking" | "unsupported" | "ios-install" | "denied" | "off" | "on";

function keyBytes(base64url: string): Uint8Array {
  const pad = "=".repeat((4 - (base64url.length % 4)) % 4);
  const raw = atob((base64url + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

/** Turn push notifications on or off for this device, and send a test. */
export function NotificationsToggle() {
  const [status, setStatus] = useState<Status>("checking");
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const ios = /iPhone|iPad|iPod/.test(navigator.userAgent);
      const standalone = window.matchMedia("(display-mode: standalone)").matches || (navigator as { standalone?: boolean }).standalone;
      if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) {
        return setStatus(ios && !standalone ? "ios-install" : "unsupported");
      }
      if (Notification.permission === "denied") return setStatus("denied");
      const reg = await navigator.serviceWorker.getRegistration("/");
      const sub = await reg?.pushManager.getSubscription();
      setStatus(sub ? "on" : "off");
    })().catch(() => setStatus("unsupported"));
  }, []);

  const enable = async () => {
    setBusy(true);
    setNote(null);
    try {
      const reg = await navigator.serviceWorker.register("/sw.js", { scope: "/" });
      await navigator.serviceWorker.ready;
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        setStatus(permission === "denied" ? "denied" : "off");
        return;
      }
      const { public_key } = await api<{ public_key: string }>("/push/notifications");
      const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(public_key) as BufferSource });
      await apiPost("/push/notifications/subscribe", sub.toJSON());
      setStatus("on");
    } catch (e) {
      setNote(`Couldn't turn notifications on: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  const disable = async () => {
    setBusy(true);
    try {
      const reg = await navigator.serviceWorker.getRegistration("/");
      const sub = await reg?.pushManager.getSubscription();
      if (sub) {
        await apiPost("/push/notifications/unsubscribe", { endpoint: sub.endpoint });
        await sub.unsubscribe();
      }
      setStatus("off");
    } finally {
      setBusy(false);
    }
  };

  const test = async () => {
    const r = await apiPost<{ sent: number }>("/push/notifications/test", {});
    setNote(r.sent ? "Sent. It should arrive in a few seconds." : "Nothing was delivered; try turning notifications off and on again.");
  };

  const message: Record<Status, string> = {
    checking: "Checking this device…",
    unsupported: "This browser can't receive push notifications.",
    "ios-install": "On iPhone, add FINN to your Home Screen first (Share → Add to Home Screen), then open it from there.",
    denied: "Notifications are blocked for this site. Allow them in your browser's site settings, then come back.",
    off: "Get a notification for critical filings, items you marked below, thesis challenges and unusual moves.",
    on: "On for this device. FINN sends at most a few per refresh, each item once.",
  };

  return (
    <div className="card mx-4 p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="flex items-center gap-2 text-sm font-medium">
          {status === "on" ? <Bell size={16} className="text-accent" /> : <BellOff size={16} className="text-muted" />}
          Notifications
        </p>
        {(status === "off" || status === "on") && (
          <button
            onClick={status === "on" ? disable : enable}
            disabled={busy}
            role="switch"
            aria-checked={status === "on"}
            aria-label="Notifications"
            className={`relative h-7 w-12 rounded-full transition-colors ${status === "on" ? "bg-accent" : "bg-line"} disabled:opacity-60`}
          >
            <span className={`absolute top-0.5 flex h-6 w-6 items-center justify-center rounded-full bg-surface shadow transition-all ${status === "on" ? "left-[22px]" : "left-0.5"}`}>
              {busy && <Loader2 size={12} className="animate-spin text-muted" />}
            </span>
          </button>
        )}
      </div>
      <p className="mt-1.5 text-xs leading-relaxed text-muted">{message[status]}</p>
      {status === "on" && (
        <button onClick={test} className="mt-2 text-xs font-medium text-accent">
          Send a test notification
        </button>
      )}
      {note && <p className="mt-2 text-xs text-muted">{note}</p>}
    </div>
  );
}
