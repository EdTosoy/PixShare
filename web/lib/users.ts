import { apiFetch } from "./api";
export type CurrentUser = { id: string };
export function getCurrentUser(token: string): Promise<CurrentUser> {
  return apiFetch("/users/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
}
