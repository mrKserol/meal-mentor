import { authClient } from "./authApi";
import type { ConsentAcceptPayload, ConsentAcceptResponse, ConsentStatus } from "../types/consents";

export const getConsentStatus = async (accessToken: string): Promise<ConsentStatus> => {
  const response = await authClient.get<ConsentStatus>("/api/consents/status", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return response.data;
};

export const acceptConsent = async (
  accessToken: string,
  payload: ConsentAcceptPayload,
): Promise<ConsentAcceptResponse> => {
  const response = await authClient.post<ConsentAcceptResponse>("/api/consents/accept", payload, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return response.data;
};
