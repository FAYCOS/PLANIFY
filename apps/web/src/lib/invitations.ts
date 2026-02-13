import crypto from "crypto";

const INVITE_TTL_DAYS = 7;

export function getInviteSecret() {
  return (
    process.env.INVITE_TOKEN_SECRET ||
    process.env.BETTER_AUTH_SECRET ||
    "planify-invite"
  );
}

export function generateInviteToken() {
  return crypto.randomUUID();
}

export function hashInviteToken(token: string) {
  return crypto
    .createHash("sha256")
    .update(`${token}:${getInviteSecret()}`)
    .digest("hex");
}

export function getInviteExpiryDate() {
  return new Date(Date.now() + INVITE_TTL_DAYS * 24 * 60 * 60 * 1000);
}
