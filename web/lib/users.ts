import { apiUrl } from "./api";

export type CurrentUser = {
  id: string;
};

export async function getCurrentUser(token: string): Promise<CurrentUser> {
  const response = await fetch(`${apiUrl("/users/me")}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error("Failed to get current user.");
  }

  return response.json();
}
