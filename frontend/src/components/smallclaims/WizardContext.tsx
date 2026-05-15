import { createContext, useContext, useState, useMemo, ReactNode } from "react";

export type WizardData = {
  claim_type: string;
  amount: string; // string so the input stays controlled; cast on submit
  defendant_type: string;
  defendant_name: string;
  defendant_address: string;
  defendant_phone: string;
  defendant_email: string;
  county: string;
};

export const INITIAL_DATA: WizardData = {
  claim_type: "",
  amount: "",
  defendant_type: "Individual",
  defendant_name: "",
  defendant_address: "",
  defendant_phone: "",
  defendant_email: "",
  county: "",
};

export type WizardContextValue = {
  step: number;
  data: WizardData;
  setField: <K extends keyof WizardData>(k: K, v: WizardData[K]) => void;
  next: () => void;
  back: () => void;
  goto: (s: number) => void;
};

const Ctx = createContext<WizardContextValue | null>(null);

export function WizardProvider({ children }: { children: ReactNode }) {
  const [step, setStep] = useState(1);
  const [data, setData] = useState<WizardData>(INITIAL_DATA);

  const value = useMemo<WizardContextValue>(
    () => ({
      step,
      data,
      setField: (k, v) => setData((d) => ({ ...d, [k]: v })),
      next: () => setStep((s) => Math.min(5, s + 1)),
      back: () => setStep((s) => Math.max(1, s - 1)),
      goto: (s) => setStep(Math.max(1, Math.min(5, s))),
    }),
    [step, data],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useWizard(): WizardContextValue {
  const v = useContext(Ctx);
  if (!v) throw new Error("useWizard must be used inside <WizardProvider>");
  return v;
}
