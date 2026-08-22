"use client";

import { InputHTMLAttributes, useId, useState } from "react";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & {
  label: string;
};

export function PasswordInput({ label, id, className, ...inputProps }: Props) {
  const autoId = useId();
  const inputId = id || autoId;
  const [visible, setVisible] = useState(false);

  return (
    <label className={["password-field", className].filter(Boolean).join(" ")} htmlFor={inputId}>
      <span className="password-field-label">{label}</span>
      <span className="password-field-wrap">
        <input
          {...inputProps}
          id={inputId}
          type={visible ? "text" : "password"}
          className="password-field-input"
        />
        <button
          type="button"
          className="password-field-toggle"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "Passwort verbergen" : "Passwort anzeigen"}
          aria-pressed={visible}
          tabIndex={-1}
        >
          {visible ? (
            <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
              <path
                fill="currentColor"
                d="M12 6a9.77 9.77 0 0 1 8.82 5.5 9.77 9.77 0 0 1-17.64 0A9.77 9.77 0 0 1 12 6m0 3a3 3 0 1 0 0 6 3 3 0 0 0 0-6m0 1.5a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3"
              />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
              <path
                fill="currentColor"
                d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5M12 17a5 5 0 1 1 0-10 5 5 0 0 1 0 10m0-2.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5"
              />
            </svg>
          )}
        </button>
      </span>
    </label>
  );
}
