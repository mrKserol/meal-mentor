import { authClient } from "./authApi";

export interface AiChatMessage {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

export interface AiChatBootstrapResponse {
  thread_id: number | null;
  disclaimer_required: boolean;
  disclaimer_version: string;
  messages: AiChatMessage[];
  has_more_messages: boolean;
  oldest_message_id: number | null;
}

export interface AiChatMessagesPageResponse {
  messages: AiChatMessage[];
  has_more: boolean;
  oldest_message_id: number | null;
}

export interface AiChatSendResponse {
  thread_id: number;
  user_message: AiChatMessage;
  assistant_message: AiChatMessage;
}

export interface AiChatDisclaimerStatus {
  accepted: boolean;
  consent_type: string;
  consent_version: string;
  accepted_at: string | null;
}

export interface AiChatLimitsResponse {
  enabled: boolean;
  daily_limit: number;
  used_today: number;
  remaining_today: number | null;
}

export async function getAiChatBootstrap(accessToken: string): Promise<AiChatBootstrapResponse> {
  const { data } = await authClient.get<AiChatBootstrapResponse>("/api/ai-chat/bootstrap", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return data;
}

export async function getAiChatMessagesPage(
  accessToken: string,
  beforeId?: number | null,
  limit = 10,
): Promise<AiChatMessagesPageResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  if (beforeId) {
    params.set("before_id", String(beforeId));
  }

  const { data } = await authClient.get<AiChatMessagesPageResponse>(`/api/ai-chat/messages?${params.toString()}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return data;
}

export async function sendAiChatMessage(accessToken: string, message: string): Promise<AiChatSendResponse> {
  const { data } = await authClient.post<AiChatSendResponse>(
    "/api/ai-chat/message",
    { message },
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
  return data;
}

export async function acceptAiChatDisclaimer(accessToken: string): Promise<void> {
  await authClient.post("/api/consents/ai-chat/accept", {}, { headers: { Authorization: `Bearer ${accessToken}` } });
}

export async function getAiChatDisclaimerStatus(accessToken: string): Promise<AiChatDisclaimerStatus> {
  const { data } = await authClient.get<AiChatDisclaimerStatus>("/api/consents/ai-chat/status", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return data;
}

export async function getAiChatLimits(accessToken: string): Promise<AiChatLimitsResponse> {
  const { data } = await authClient.get<AiChatLimitsResponse>("/api/ai-chat/limits", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return data;
}
