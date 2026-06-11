export interface ConsentStatus {
  required: boolean;
  accepted: boolean;
  consent_type: "disclaimer";
  current_version: string;
  accepted_at: string | null;
}

export interface ConsentAcceptPayload {
  consent_type: "disclaimer";
  consent_version: string;
}

export interface ConsentAcceptResponse {
  accepted: boolean;
  consent_type: "disclaimer";
  consent_version: string;
  accepted_at: string;
}
