import crypto from "crypto";

const PREFIX = "enc:";

function getKey(): Buffer | null {
  const raw = process.env.APP_ENCRYPTION_KEY || "";
  if (!raw) return null;
  let key: Buffer;
  try {
    key = Buffer.from(raw, "base64");
  } catch {
    key = Buffer.from(raw, "hex");
  }
  if (key.length !== 32) {
    return null;
  }
  return key;
}

export function encryptSensitive(value?: string | null) {
  if (!value) return null;
  if (value.startsWith(PREFIX)) return value;
  const key = getKey();
  if (!key) {
    throw new Error("APP_ENCRYPTION_KEY manquante ou invalide.");
  }
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv("aes-256-gcm", key, iv);
  const encrypted = Buffer.concat([cipher.update(value, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return `${PREFIX}${Buffer.concat([iv, tag, encrypted]).toString("base64")}`;
}

export function decryptSensitive(value?: string | null) {
  if (!value) return null;
  if (!value.startsWith(PREFIX)) return value;
  const key = getKey();
  if (!key) return null;
  const raw = Buffer.from(value.slice(PREFIX.length), "base64");
  const iv = raw.subarray(0, 12);
  const tag = raw.subarray(12, 28);
  const encrypted = raw.subarray(28);
  const decipher = crypto.createDecipheriv("aes-256-gcm", key, iv);
  decipher.setAuthTag(tag);
  const decrypted = Buffer.concat([decipher.update(encrypted), decipher.final()]);
  return decrypted.toString("utf8");
}

export function maskSensitive(value?: string | null, showLast = 4) {
  if (!value) return "";
  const str = String(value);
  if (str.length <= showLast) return "*".repeat(str.length);
  return "*".repeat(str.length - showLast) + str.slice(-showLast);
}

export function isMaskedInput(value?: string | null) {
  if (!value) return false;
  return value.includes("*");
}
