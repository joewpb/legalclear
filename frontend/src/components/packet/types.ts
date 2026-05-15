export type PacketMetadata = {
  id: string;
  user_id: string;
  packet_type:
    | "small_claims"
    | "expungement"
    | "landlord_deposit"
    | "landlord_repairs"
    | "landlord_eviction"
    | "traffic";
  language: "en" | "es";
  county: string;
  fee_usd: number;
  zip_path: string;
  status: "pending_payment" | "paid";
  confirmation_number: string | null;
  filed_at: string | null;
  created_at: string;
};
