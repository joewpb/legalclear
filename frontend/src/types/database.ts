// Auto-generated Supabase types — regenerated 2026-05-19 (Phase 1 schema)
// Do not edit manually. Regenerate with: supabase gen types typescript

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      chat_messages: {
        Row: {
          content: string | null
          created_at: string | null
          document_id: string | null
          id: string
          language: string | null
          role: string | null
        }
        Insert: {
          content?: string | null
          created_at?: string | null
          document_id?: string | null
          id?: string
          language?: string | null
          role?: string | null
        }
        Update: {
          content?: string | null
          created_at?: string | null
          document_id?: string | null
          id?: string
          language?: string | null
          role?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "chat_messages_document_id_fkey"
            columns: ["document_id"]
            isOneToOne: false
            referencedRelation: "documents"
            referencedColumns: ["id"]
          },
        ]
      }
      court_forms: {
        Row: {
          category: string
          content_hash: string | null
          content_id: string | null
          court_revision_date: string | null
          created_at: string
          form_number: string
          id: string
          last_changed_at: string | null
          last_checked_at: string | null
          plain_language_summary: string | null
          situation_tags: string[] | null
          source_download_url: string | null
          source_page_url: string | null
          status: string
          storage_path: string | null
          title: string
          updated_at: string
        }
        Insert: {
          category: string
          content_hash?: string | null
          content_id?: string | null
          court_revision_date?: string | null
          created_at?: string
          form_number: string
          id?: string
          last_changed_at?: string | null
          last_checked_at?: string | null
          plain_language_summary?: string | null
          situation_tags?: string[] | null
          source_download_url?: string | null
          source_page_url?: string | null
          status?: string
          storage_path?: string | null
          title: string
          updated_at?: string
        }
        Update: {
          category?: string
          content_hash?: string | null
          content_id?: string | null
          court_revision_date?: string | null
          created_at?: string
          form_number?: string
          id?: string
          last_changed_at?: string | null
          last_checked_at?: string | null
          plain_language_summary?: string | null
          situation_tags?: string[] | null
          source_download_url?: string | null
          source_page_url?: string | null
          status?: string
          storage_path?: string | null
          title?: string
          updated_at?: string
        }
        Relationships: []
      }
      deadlines: {
        Row: {
          computation_trace: Json
          confidence: number
          consequence_if_missed: string
          created_at: string
          document_id: string | null
          due_date: string
          escalation_recommended: boolean
          governing_rule: string
          id: string
          label: string
          reminder_state: string
          severity: string
          trigger_event_id: string | null
        }
        Insert: {
          computation_trace: Json
          confidence: number
          consequence_if_missed: string
          created_at?: string
          document_id?: string | null
          due_date: string
          escalation_recommended?: boolean
          governing_rule: string
          id?: string
          label: string
          reminder_state?: string
          severity: string
          trigger_event_id?: string | null
        }
        Update: {
          computation_trace?: Json
          confidence?: number
          consequence_if_missed?: string
          created_at?: string
          document_id?: string | null
          due_date?: string
          escalation_recommended?: boolean
          governing_rule?: string
          id?: string
          label?: string
          reminder_state?: string
          severity?: string
          trigger_event_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "deadlines_document_id_fkey"
            columns: ["document_id"]
            isOneToOne: false
            referencedRelation: "documents"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "deadlines_trigger_event_id_fkey"
            columns: ["trigger_event_id"]
            isOneToOne: false
            referencedRelation: "trigger_events"
            referencedColumns: ["id"]
          },
        ]
      }
      documents: {
        Row: {
          classification: Json | null
          created_at: string | null
          document_text: string | null
          escalation: Json | null
          explanation: Json | null
          expungement_guide: Json | null
          form_guide: Json | null
          id: string
          language: string | null
          risk_scan: Json | null
          session_id: string | null
          status: string | null
        }
        Insert: {
          classification?: Json | null
          created_at?: string | null
          document_text?: string | null
          escalation?: Json | null
          explanation?: Json | null
          expungement_guide?: Json | null
          form_guide?: Json | null
          id?: string
          language?: string | null
          risk_scan?: Json | null
          session_id?: string | null
          status?: string | null
        }
        Update: {
          classification?: Json | null
          created_at?: string | null
          document_text?: string | null
          escalation?: Json | null
          explanation?: Json | null
          expungement_guide?: Json | null
          form_guide?: Json | null
          id?: string
          language?: string | null
          risk_scan?: Json | null
          session_id?: string | null
          status?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "documents_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      packets: {
        Row: {
          confirmation_number: string | null
          county: string
          created_at: string
          fee_usd: number
          filed_at: string | null
          id: string
          language: string
          packet_type: string
          paid_at: string | null
          status: string
          user_id: string | null
          zip_path: string
        }
        Insert: {
          confirmation_number?: string | null
          county: string
          created_at?: string
          fee_usd: number
          filed_at?: string | null
          id?: string
          language: string
          packet_type: string
          paid_at?: string | null
          status?: string
          user_id?: string | null
          zip_path: string
        }
        Update: {
          confirmation_number?: string | null
          county?: string
          created_at?: string
          fee_usd?: number
          filed_at?: string | null
          id?: string
          language?: string
          packet_type?: string
          paid_at?: string | null
          status?: string
          user_id?: string | null
          zip_path?: string
        }
        Relationships: [
          {
            foreignKeyName: "packets_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      push_tokens: {
        Row: {
          created_at: string | null
          expo_token: string | null
          id: string
          platform: string | null
          user_id: string | null
        }
        Insert: {
          created_at?: string | null
          expo_token?: string | null
          id?: string
          platform?: string | null
          user_id?: string | null
        }
        Update: {
          created_at?: string | null
          expo_token?: string | null
          id?: string
          platform?: string | null
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "push_tokens_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      sessions: {
        Row: {
          created_at: string | null
          document_filename: string | null
          document_token_count: number | null
          id: string
          payment_status: string | null
          payment_type: string | null
          price_paid_usd: number | null
          price_tier: string | null
          stripe_payment_intent: string | null
          stripe_subscription_id: string | null
          user_id: string | null
        }
        Insert: {
          created_at?: string | null
          document_filename?: string | null
          document_token_count?: number | null
          id?: string
          payment_status?: string | null
          payment_type?: string | null
          price_paid_usd?: number | null
          price_tier?: string | null
          stripe_payment_intent?: string | null
          stripe_subscription_id?: string | null
          user_id?: string | null
        }
        Update: {
          created_at?: string | null
          document_filename?: string | null
          document_token_count?: number | null
          id?: string
          payment_status?: string | null
          payment_type?: string | null
          price_paid_usd?: number | null
          price_tier?: string | null
          stripe_payment_intent?: string | null
          stripe_subscription_id?: string | null
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "sessions_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      trigger_events: {
        Row: {
          case_number: string | null
          circuit: number | null
          confidence: number
          county: string | null
          created_at: string
          document_id: string | null
          document_type: string
          event_date: string
          event_type: string
          id: string
          jurisdiction: string
          raw_text_excerpt: string
          service_method: string
        }
        Insert: {
          case_number?: string | null
          circuit?: number | null
          confidence: number
          county?: string | null
          created_at?: string
          document_id?: string | null
          document_type: string
          event_date: string
          event_type: string
          id?: string
          jurisdiction?: string
          raw_text_excerpt: string
          service_method: string
        }
        Update: {
          case_number?: string | null
          circuit?: number | null
          confidence?: number
          county?: string | null
          created_at?: string
          document_id?: string | null
          document_type?: string
          event_date?: string
          event_type?: string
          id?: string
          jurisdiction?: string
          raw_text_excerpt?: string
          service_method?: string
        }
        Relationships: [
          {
            foreignKeyName: "trigger_events_document_id_fkey"
            columns: ["document_id"]
            isOneToOne: false
            referencedRelation: "documents"
            referencedColumns: ["id"]
          },
        ]
      }
      usage_stats: {
        Row: {
          created_at: string | null
          document_category: string | null
          estimated_cost_usd: number | null
          id: string
          jurisdiction: string | null
          language: string | null
          price_tier: string | null
          processing_time_seconds: number | null
          total_input_tokens: number | null
          total_output_tokens: number | null
        }
        Insert: {
          created_at?: string | null
          document_category?: string | null
          estimated_cost_usd?: number | null
          id?: string
          jurisdiction?: string | null
          language?: string | null
          price_tier?: string | null
          processing_time_seconds?: number | null
          total_input_tokens?: number | null
          total_output_tokens?: number | null
        }
        Update: {
          created_at?: string | null
          document_category?: string | null
          estimated_cost_usd?: number | null
          id?: string
          jurisdiction?: string | null
          language?: string | null
          price_tier?: string | null
          processing_time_seconds?: number | null
          total_input_tokens?: number | null
          total_output_tokens?: number | null
        }
        Relationships: []
      }
      users: {
        Row: {
          created_at: string | null
          email: string | null
          expo_push_token: string | null
          free_doc_used: boolean | null
          id: string
          preferred_language: string | null
          stripe_customer_id: string | null
          subscription_id: string | null
          subscription_status: string | null
        }
        Insert: {
          created_at?: string | null
          email?: string | null
          expo_push_token?: string | null
          free_doc_used?: boolean | null
          id?: string
          preferred_language?: string | null
          stripe_customer_id?: string | null
          subscription_id?: string | null
          subscription_status?: string | null
        }
        Update: {
          created_at?: string | null
          email?: string | null
          expo_push_token?: string | null
          free_doc_used?: boolean | null
          id?: string
          preferred_language?: string | null
          stripe_customer_id?: string | null
          subscription_id?: string | null
          subscription_status?: string | null
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">
type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never
