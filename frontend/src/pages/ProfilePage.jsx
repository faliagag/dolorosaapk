import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Save, CreditCard } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import AppShell from "@/components/AppShell";
import BottomNav from "@/components/BottomNav";

export default function ProfilePage() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [bankDetails, setBankDetails] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (user) setBankDetails(user.bank_details || "");
  }, [user]);

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await api.put("/profile", { bank_details: bankDetails });
      setUser(res.data);
      toast.success("Perfil actualizado");
    } catch {
      toast.error("Error al guardar");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppShell>
      <button
        onClick={() => navigate("/dashboard")}
        className="mb-6 flex items-center gap-2 text-zinc-400 hover:text-white transition"
        data-testid="back-btn"
      >
        <ArrowLeft size={18} /> Volver
      </button>

      <div className="card-glass text-center mb-6">
        <div className="w-20 h-20 mx-auto rounded-full overflow-hidden border-2 border-[#39FF14]/50 mb-4">
          {user?.picture ? (
            <img src={user.picture} alt={user.name} className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full bg-[#BF40FF] flex items-center justify-center text-2xl font-bold">
              {user?.name?.[0] || "U"}
            </div>
          )}
        </div>
        <div className="font-display font-bold text-xl text-white">{user?.name}</div>
        <div className="text-xs text-zinc-400">{user?.email}</div>
      </div>

      <form onSubmit={save} className="card-glass space-y-4">
        <div className="flex items-center gap-2 mb-2">
          <CreditCard size={18} className="text-[#39FF14]" />
          <div className="font-display font-bold text-white">Datos bancarios</div>
        </div>
        <p className="text-xs text-zinc-400 -mt-2">
          Se incluyen automáticamente en los mensajes de WhatsApp que envías a tus amigos.
        </p>
        <textarea
          data-testid="bank-details-input"
          className="input-field"
          rows={6}
          style={{ height: "auto", paddingTop: "1rem", paddingBottom: "1rem" }}
          placeholder={`Ej:\nBanco de Chile\nCta Vista 123456789\nRUT 12.345.678-9\nMaría Pérez\nmaria@mail.cl`}
          value={bankDetails}
          onChange={(e) => setBankDetails(e.target.value)}
        />
        <button
          type="submit"
          className="btn-primary w-full"
          disabled={saving}
          data-testid="save-profile-btn"
        >
          <Save size={18} />
          {saving ? "Guardando..." : "Guardar"}
        </button>
      </form>

      <BottomNav />
    </AppShell>
  );
}
