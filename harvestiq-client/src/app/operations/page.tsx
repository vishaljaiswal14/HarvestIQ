"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AuthGuard } from "@/components/AuthGuard";
import { AppShell } from "@/components/layout/AppShell";
import { useAuthStore } from "@/stores/authStore";
import { useTranslation } from "@/stores/localizationStore";
import {
  useExpenses,
  useHarvests,
  useCreateExpense,
  useUpdateExpense,
  useDeleteExpense,
  useCreateHarvest,
  useUpdateHarvest,
  useDeleteHarvest,
} from "@/hooks/useFarmOperations";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Trash2, Edit2, IndianRupee, Scale } from "lucide-react";

// ── Expense category options ──────────────────────────────────────────────────
const EXPENSE_CATEGORIES = [
  { value: "SEEDS", label: "Seeds" },
  { value: "FERTILIZER", label: "Fertilizer" },
  { value: "PESTICIDES", label: "Pesticides" },
  { value: "IRRIGATION_FUEL", label: "Irrigation / Fuel" },
  { value: "LABOR", label: "Labor" },
  { value: "MACHINERY_RENT", label: "Machinery Rent" },
  { value: "TRANSPORT", label: "Transport" },
  { value: "LAND_RENT", label: "Land Rent" },
  { value: "OTHER", label: "Other" },
] as const;

// Helper to translate categories
const getCategoryKey = (val: string) => {
  if (val === "IRRIGATION_FUEL") return "operations.category.irrigationFuel";
  if (val === "MACHINERY_RENT") return "operations.category.machineryRent";
  if (val === "LAND_RENT") return "operations.category.landRent";
  return `operations.category.${val.toLowerCase()}`;
};

// ── Tiny shared field component ───────────────────────────────────────────────
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <Label className="text-xs font-semibold text-slate-600">{label}</Label>
      {children}
    </div>
  );
}

// ── Expense section ───────────────────────────────────────────────────────────
function ExpenseSection({ cycleId }: { cycleId: string }) {
  const { t } = useTranslation();
  const today = new Date().toISOString().split("T")[0];

  const [form, setForm] = useState({
    category: "FERTILIZER",
    amount: "",
    expense_date: today,
    notes: "",
  });
  const [editId, setEditId] = useState<string | null>(null);

  const { data: expenses, isLoading, error } = useExpenses(cycleId);
  const create = useCreateExpense(cycleId);
  const update = useUpdateExpense(cycleId);
  const del = useDeleteExpense(cycleId);

  const isBusy = create.isPending || update.isPending;

  const resetForm = () =>
    setForm({ category: "FERTILIZER", amount: "", expense_date: today, notes: "" });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const amount = parseFloat(form.amount);
    if (!amount || amount <= 0) return;

    const payload = {
      crop_cycle_id: cycleId,
      category: form.category,
      amount,
      notes: form.notes || undefined,
      expense_date: form.expense_date,
    };

    if (editId) {
      await update.mutateAsync({ id: editId, payload });
      setEditId(null);
    } else {
      await create.mutateAsync(payload);
    }
    resetForm();
  };

  const startEdit = (exp: any) => {
    setEditId(exp.id);
    setForm({
      category: exp.category,
      amount: String(exp.amount),
      expense_date: exp.expense_date,
      notes: exp.notes ?? "",
    });
  };

  const cancelEdit = () => {
    setEditId(null);
    resetForm();
  };

  return (
    <div className="space-y-6">
      {/* ── Form ── */}
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <h3 className="text-sm font-bold text-slate-700 mb-3">
          {editId ? t("operations.editExpense", "Edit Expense") : t("operations.addExpense", "Add Expense")}
        </h3>
        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Field label={t("operations.categoryLabel", "Category")}>
              <select
                id="expense-category"
                className="flex h-10 w-full rounded-md border border-emerald-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                value={form.category}
                onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
              >
                {EXPENSE_CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {t(getCategoryKey(c.value), c.label)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={t("operations.amountLabel", "Amount (₹)")}>
              <Input
                id="expense-amount"
                type="number"
                min="0"
                step="any"
                placeholder={t("operations.amountRupeesPlaceholder", "Amount in Rupees")}
                value={form.amount}
                onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                required
              />
            </Field>
            <Field label={t("operations.dateLabel", "Date")}>
              <Input
                id="expense-date"
                type="date"
                value={form.expense_date}
                onChange={(e) => setForm((f) => ({ ...f, expense_date: e.target.value }))}
                required
              />
            </Field>
            <Field label={t("operations.notesLabelOptional", "Notes (optional)")}>
              <Input
                id="expense-notes"
                type="text"
                placeholder={t("operations.notesPlaceholder", "e.g. Urea purchase")}
                value={form.notes}
                onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              />
            </Field>
          </div>

          {(create.error || update.error) && (
            <p className="text-xs text-rose-600">
              {((create.error ?? update.error) as Error).message}
            </p>
          )}

          <div className="flex gap-2 pt-1">
            <Button id="expense-submit-btn" type="submit" size="sm" disabled={isBusy}>
              {isBusy ? t("operations.saving", "Saving…") : editId ? t("operations.update", "Update") : t("operations.saveExpense", "Save Expense")}
            </Button>
            {editId && (
              <Button type="button" variant="outline" size="sm" onClick={cancelEdit}>
                {t("operations.cancel", "Cancel")}
              </Button>
            )}
          </div>
        </form>
      </div>

      {/* ── List ── */}
      <div>
        <h3 className="text-sm font-semibold text-slate-600 mb-2">
          {t("operations.recordedExpenses", "Recorded Expenses")}
        </h3>
        {isLoading && (
          <div className="h-16 animate-pulse rounded-xl bg-slate-100" />
        )}
        {error && (
          <p className="text-xs text-rose-600">{t("operations.failedLoadExpenses", "Failed to load expenses.")}</p>
        )}
        {!isLoading && !error && (!expenses || expenses.length === 0) && (
          <p className="text-sm text-slate-400 py-4 text-center rounded-xl border border-dashed border-slate-200">
            {t("operations.noExpenses", "No expenses yet.")}
          </p>
        )}
        {expenses && expenses.length > 0 && (
          <ul className="space-y-2">
            {(expenses as any[]).map((exp) => (
              <li
                key={exp.id}
                className="flex items-center justify-between rounded-xl border border-slate-100 bg-white px-4 py-3"
              >
                <div className="space-y-0.5">
                  <span className="text-xs font-bold text-slate-700 rounded-full bg-slate-100 px-2 py-0.5">
                    {t(getCategoryKey(exp.category), exp.category)}
                  </span>
                  {exp.notes && (
                    <p className="text-xs text-slate-500">{exp.notes}</p>
                  )}
                  <p className="text-[10px] text-slate-400">{exp.expense_date}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="flex items-center text-sm font-bold text-slate-800">
                    <IndianRupee className="h-3 w-3" />
                    {Number(exp.amount).toLocaleString("en-IN")}
                  </span>
                  <button
                    onClick={() => startEdit(exp)}
                    className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-500"
                    aria-label="Edit"
                  >
                    <Edit2 className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => {
                      if (confirm(t("operations.confirmDeleteExpenseMsg", "Are you sure you want to delete this expense?"))) del.mutate(exp.id);
                    }}
                    className="p-1.5 rounded-lg hover:bg-rose-50 text-rose-500"
                    aria-label="Delete"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

// ── Harvest section ───────────────────────────────────────────────────────────
function HarvestSection({ cycleId }: { cycleId: string }) {
  const { t } = useTranslation();
  const today = new Date().toISOString().split("T")[0];

  const [form, setForm] = useState({
    yield_quantity: "",
    yield_unit: "Quintal",
    revenue: "",
    harvest_date: today,
  });
  const [editId, setEditId] = useState<string | null>(null);

  const { data: harvests, isLoading, error } = useHarvests(cycleId);
  const create = useCreateHarvest(cycleId);
  const update = useUpdateHarvest(cycleId);
  const del = useDeleteHarvest(cycleId);

  const isBusy = create.isPending || update.isPending;

  const resetForm = () =>
    setForm({ yield_quantity: "", yield_unit: "Quintal", revenue: "", harvest_date: today });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const qty = parseFloat(form.yield_quantity);
    const rev = parseFloat(form.revenue);
    if (!qty || qty <= 0 || isNaN(rev) || rev < 0) return;

    const payload = {
      crop_cycle_id: cycleId,
      yield_quantity: qty,
      yield_unit: form.yield_unit,
      revenue: rev,
      harvest_date: form.harvest_date,
    };

    if (editId) {
      await update.mutateAsync({ id: editId, payload });
      setEditId(null);
    } else {
      await create.mutateAsync(payload);
    }
    resetForm();
  };

  const startEdit = (harv: any) => {
    setEditId(harv.id);
    setForm({
      yield_quantity: String(harv.yield_quantity),
      yield_unit: harv.yield_unit,
      revenue: String(harv.revenue),
      harvest_date: harv.harvest_date,
    });
  };

  const cancelEdit = () => {
    setEditId(null);
    resetForm();
  };

  return (
    <div className="space-y-6">
      {/* ── Form ── */}
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <h3 className="text-sm font-bold text-slate-700 mb-3">
          {editId ? t("operations.editHarvest", "Edit Harvest") : t("operations.addHarvest", "Add Harvest")}
        </h3>
        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Field label={t("operations.yieldQuantity", "Yield Quantity")}>
              <Input
                id="harvest-yield-qty"
                type="number"
                min="0"
                step="any"
                placeholder={t("operations.qtyHarvestedPlaceholder", "Quantity harvested")}
                value={form.yield_quantity}
                onChange={(e) => setForm((f) => ({ ...f, yield_quantity: e.target.value }))}
                required
              />
            </Field>
            <Field label={t("operations.yieldUnit", "Yield Unit")}>
              <Input
                id="harvest-yield-unit"
                type="text"
                placeholder={t("operations.yieldUnitPlaceholder", "e.g. Quintal, Kg, Bags")}
                value={form.yield_unit}
                onChange={(e) => setForm((f) => ({ ...f, yield_unit: e.target.value }))}
                required
              />
            </Field>
            <Field label={t("operations.revenueLabel", "Revenue (₹)")}>
              <Input
                id="harvest-revenue"
                type="number"
                min="0"
                step="any"
                placeholder={t("operations.revenuePlaceholder", "Total sale amount")}
                value={form.revenue}
                onChange={(e) => setForm((f) => ({ ...f, revenue: e.target.value }))}
                required
              />
            </Field>
            <Field label={t("operations.dateLabel", "Date")}>
              <Input
                id="harvest-date"
                type="date"
                value={form.harvest_date}
                onChange={(e) => setForm((f) => ({ ...f, harvest_date: e.target.value }))}
                required
              />
            </Field>
          </div>

          {(create.error || update.error) && (
            <p className="text-xs text-rose-600">
              {((create.error ?? update.error) as Error).message}
            </p>
          )}

          <div className="flex gap-2 pt-1">
            <Button id="harvest-submit-btn" type="submit" size="sm" disabled={isBusy}>
              {isBusy ? t("operations.saving", "Saving…") : editId ? t("operations.update", "Update") : t("operations.saveHarvest", "Save Harvest")}
            </Button>
            {editId && (
              <Button type="button" variant="outline" size="sm" onClick={cancelEdit}>
                {t("operations.cancel", "Cancel")}
              </Button>
            )}
          </div>
        </form>
      </div>

      {/* ── List ── */}
      <div>
        <h3 className="text-sm font-semibold text-slate-600 mb-2">
          {t("operations.recordedHarvests", "Recorded Harvests")}
        </h3>
        {isLoading && (
          <div className="h-16 animate-pulse rounded-xl bg-slate-100" />
        )}
        {error && (
          <p className="text-xs text-rose-600">{t("operations.failedLoadHarvests", "Failed to load harvests.")}</p>
        )}
        {!isLoading && !error && (!harvests || harvests.length === 0) && (
          <p className="text-sm text-slate-400 py-4 text-center rounded-xl border border-dashed border-slate-200">
            {t("operations.noHarvests", "No harvests yet.")}
          </p>
        )}
        {harvests && harvests.length > 0 && (
          <ul className="space-y-2">
            {(harvests as any[]).map((harv) => (
              <li
                key={harv.id}
                className="flex items-center justify-between rounded-xl border border-slate-100 bg-white px-4 py-3"
              >
                <div className="space-y-0.5">
                  <span className="flex items-center gap-1 text-xs font-bold text-emerald-700 rounded-full bg-emerald-50 px-2 py-0.5 w-fit">
                    <Scale className="h-3 w-3" />
                    {harv.yield_quantity} {harv.yield_unit}
                  </span>
                  <p className="text-[10px] text-slate-400">{harv.harvest_date}</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <span className="flex items-center text-sm font-bold text-slate-800">
                      <IndianRupee className="h-3 w-3" />
                      {Number(harv.revenue).toLocaleString("en-IN")}
                    </span>
                    <span className="text-[9px] text-slate-400">{t("operations.revenue", "revenue")}</span>
                  </div>
                  <button
                    onClick={() => startEdit(harv)}
                    className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-500"
                    aria-label="Edit"
                  >
                    <Edit2 className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => {
                      if (confirm(t("operations.confirmDeleteHarvestMsg", "Are you sure you want to delete this harvest record?"))) del.mutate(harv.id);
                    }}
                    className="p-1.5 rounded-lg hover:bg-rose-50 text-rose-500"
                    aria-label="Delete"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
function OperationsPageContent() {
  const router = useRouter();
  const { t } = useTranslation();
  const farm = useAuthStore((s) => s.farm);
  const user = useAuthStore((s) => s.user);
  const cycleId = farm?.crop_cycle_id ?? null;

  return (
    <AppShell
      userName={user?.name}
      pageTitle={t("operations.pageTitle", "Farm Operations")}
      pageSubtitle={t("operations.pageSubtitle", "Log expenses and harvest records for the active crop cycle")}
      showBack={{ href: "/", label: t("common.dashboard", "Dashboard") }}
      narrow
    >
      {!cycleId ? (
        <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-slate-500">
          {t("operations.noActiveCropCycle", "No active crop cycle found. Complete farm setup first.")}
          <br />
          <button
            onClick={() => router.push("/farm-setup")}
            className="mt-3 text-emerald-600 underline text-xs"
          >
            {t("operations.goToFarmSetup", "Go to Farm Setup")}
          </button>
        </div>
      ) : (
        <Tabs defaultValue="expenses">
          <TabsList className="mb-6">
            <TabsTrigger value="expenses">{t("operations.expensesTab", "Expenses")}</TabsTrigger>
            <TabsTrigger value="harvests">{t("operations.harvestsTab", "Harvests")}</TabsTrigger>
          </TabsList>
          <TabsContent value="expenses">
            <ExpenseSection cycleId={cycleId} />
          </TabsContent>
          <TabsContent value="harvests">
            <HarvestSection cycleId={cycleId} />
          </TabsContent>
        </Tabs>
      )}
    </AppShell>
  );
}

export default function OperationsPage() {
  return (
    <AuthGuard requireOnboarding>
      <OperationsPageContent />
    </AuthGuard>
  );
}
