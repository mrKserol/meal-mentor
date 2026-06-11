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

export async function getAiChatBootstrap(accessToken: string): Promise<AiChatBootstrapResponse> {
  const { data } = await authClient.get<AiChatBootstrapResponse>("/api/ai-chat/bootstrap", {
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
