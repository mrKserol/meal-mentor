import { authClient } from "./authApi";
import type { DiarySnapshot } from "../types/diary";

export async function getMyDiary(accessToken: string): Promise<DiarySnapshot> {
  const { data } = await authClient.get<DiarySnapshot>("/users/me/diary", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return data;
}
