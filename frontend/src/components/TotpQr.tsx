"use client";

import { useEffect, useState } from "react";
import QRCode from "qrcode";

export function TotpQr({ uri }: { uri: string }) {
  const [src, setSrc] = useState<string | null>(null);
  const [fail, setFail] = useState(false);

  useEffect(() => {
    setFail(false);
    QRCode.toDataURL(uri, {
      width: 256,
      margin: 2,
      errorCorrectionLevel: "M",
      color: { dark: "#1c1917", light: "#fffaf3" },
    })
      .then(setSrc)
      .catch(() => setFail(true));
  }, [uri]);

  if (fail) {
    return <p className="muted">QR-Code konnte nicht erzeugt werden. Secret unten manuell eintragen.</p>;
  }
  if (!src) {
    return <p className="muted">QR-Code wird erzeugt…</p>;
  }
  return (
    <img
      className="qr"
      src={src}
      width={256}
      height={256}
      alt="QR-Code für die Authenticator-App"
    />
  );
}
