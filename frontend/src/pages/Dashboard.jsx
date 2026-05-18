import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Plus, Users, Receipt, ChevronRight, Trash2, Archive, Flame } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import AppShell from "@/components/AppShell";
import BottomNav from "@/components/BottomNav";
import NotificationBell from "@/components/NotificationBell";

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [carretes, setCarretes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [tab, setTab] = useState("active");
  const [confirmDelete, setConfirmDelete] = useState(null);

  const load = async () => {
    try {
      const res = await api.get("/carretes");
      setCarretes(res.data);
    } catch (e) {
      toast.error("No se pudieron cargar los carretes");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
  }, []);

  const createCarrete = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    try {
      const res = await api.post("/carretes", { name: name.trim(), tip_percent: 10 });
      toast.success("Carrete creado");
      navigate(`/carretes/${res.data.id}`);
    } catch (e) {
      toast.error("Error al crear");
    } finally {
      setCreating(false);
    }
  };

  const deleteCarrete = async (id, e) => {
    e.stopPropagation();
    if (confirmDelete !== id) {
      setConfirmDelete(id);
      // Auto-reset after 3s
      setTimeout(() => {
        setConfirmDelete((curr) => (curr === id ? null : curr));
      }, 3000);
      return;
    }
    try {
      await api.delete(`/carretes/${id}`);
      toast.success("Carrete eliminado");
      setConfirmDelete(null);
      load();
    } catch (err) {
      toast.error("No se pudo eliminar");
    }
  };

  return (
    <AppShell
      subtitle={`Hola, capitán ${user?.name?.split(" ")[0] || ""}`}
      title="Tus carretes"
      right={
        <div className="flex items-center gap-2">
          <NotificationBell />
          <div className="w-12 h-12 rounded-full overflow-hidden border border-white/10 glass flex items-center justify-center">
            {user?.picture ? (
              <img src={user.picture} alt={user.name} className="w-full h-full object-cover" />
            ) : (
              <span className="text-white font-bold">{user?.name?.[0] || "U"}</span>
            )}
          </div>
        </div>
      }
    >
      {!showCreate && (
        <motion.button
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          data-testid="new-carrete-btn"
          onClick={() => setShowCreate(true)}
          className="w-full mb-6 card-glass hover:border-[#39FF14]/40 transition-all group flex items-center gap-4 text-left"
        >
          <div className="w-14 h-14 rounded-2xl bg-[#39FF14] flex items-center justify-center shrink-0 group-hover:shadow-[0_0_20px_rgba(57,255,20,0.55)] transition-all">
            <Plus size={28} className="text-black" strokeWidth={3} />
          </div>
          <div>
            <div className="font-display font-bold text-lg text-white">Nuevo carrete</div>
            <div className="text-xs text-zinc-400">Partir la dolorosa de cero</div>
          </div>
        </motion.button>
      )}

      {showCreate && (
        <motion.form
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          onSubmit={createCarrete}
          className="card-glass mb-6 space-y-3"
        >
          <label className="label-small">Nombre del carrete</label>
          <input
            data-testid="new-carrete-name-input"
            className="input-field"
            placeholder="Ej: Asado en la terraza"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
          />
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="btn-secondary flex-1"
            >
              Cancelar
            </button>
            <button
              type="submit"
              data-testid="new-carrete-submit"
              className="btn-primary flex-1"
              disabled={creating}
            >
              {creating ? "Creando..." : "Crear"}
            </button>
          </div>
        </motion.form>
      )}

      {loading ? (
        <div className="card-glass text-center text-zinc-400">Cargando...</div>
      ) : (
        <>
          <div className="flex items-center gap-2 mb-4 glass rounded-2xl p-1">
            {[
              { id: "active", label: "Activos", icon: Flame },
              { id: "closed", label: "Archivados", icon: Archive },
            ].map((t) => {
              const Icon = t.icon;
              const isActive = tab === t.id;
              const count = carretes.filter((c) =>
                t.id === "active" ? c.status !== "closed" : c.status === "closed"
              ).length;
              return (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  data-testid={`tab-${t.id}`}
                  className={`flex-1 h-11 rounded-xl flex items-center justify-center gap-2 text-sm font-bold transition-all ${
                    isActive
                      ? "bg-[#39FF14] text-black shadow-[0_0_16px_rgba(57,255,20,0.4)]"
                      : "text-zinc-400 hover:text-white"
                  }`}
                >
                  <Icon size={14} />
                  {t.label}
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                      isActive ? "bg-black/20" : "bg-white/10"
                    }`}
                  >
                    {count}
                  </span>
                </button>
              );
            })}
          </div>
          {(() => {
            const filtered = carretes.filter((c) =>
              tab === "active" ? c.status !== "closed" : c.status === "closed"
            );
            if (filtered.length === 0) {
              return (
                <div className="card-glass text-center py-12">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-[#BF40FF]/20 flex items-center justify-center">
                    {tab === "active" ? (
                      <Receipt size={32} className="text-[#BF40FF]" />
                    ) : (
                      <Archive size={32} className="text-[#BF40FF]" />
                    )}
                  </div>
                  <div className="font-display font-bold text-white mb-1">
                    {tab === "active" ? "Aún no hay carretes activos" : "Sin carretes archivados"}
                  </div>
                  <div className="text-sm text-zinc-400">
                    {tab === "active"
                      ? "Crea uno y empieza a dividir."
                      : "Cuando cierres un carrete lo verás acá."}
                  </div>
                </div>
              );
            }
            return (
              <div className="space-y-3">
                {filtered.map((c) => (
                  <motion.div
                    key={c.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    data-testid={`carrete-card-${c.id}`}
                    role="button"
                    tabIndex={0}
                    onClick={() => navigate(`/carretes/${c.id}`)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") navigate(`/carretes/${c.id}`);
                    }}
                    className="w-full card-glass hover:border-[#39FF14]/30 transition-all text-left group cursor-pointer"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="font-display font-bold text-lg text-white truncate">{c.name}</div>
                        <div className="flex items-center gap-4 mt-2 text-xs text-zinc-400">
                          <span className="flex items-center gap-1">
                            <Users size={12} />
                            {c.participants?.length || 0}
                          </span>
                          <span className="flex items-center gap-1">
                            <Receipt size={12} />
                            {c.items?.length || 0} ítems
                          </span>
                          <span className="flex items-center gap-1">
                            <span
                              className={`w-1.5 h-1.5 rounded-full ${
                                c.status === "closed" ? "bg-zinc-500" : "bg-[#39FF14]"
                              }`}
                            />
                            {c.status === "closed" ? "archivado" : "activo"}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={(e) => deleteCarrete(c.id, e)}
                          className={`h-8 rounded-lg flex items-center justify-center transition-all text-xs font-bold gap-1 ${
                            confirmDelete === c.id
                              ? "px-3 bg-[#FF3366] text-white"
                              : "w-8 hover:bg-[#FF3366]/20 text-zinc-500 hover:text-[#FF3366]"
                          }`}
                          data-testid={`delete-carrete-${c.id}`}
                          aria-label="Eliminar carrete"
                        >
                          <Trash2 size={14} />
                          {confirmDelete === c.id && <span>Confirmar</span>}
                        </button>
                        {confirmDelete !== c.id && (
                          <ChevronRight size={20} className="text-zinc-500 group-hover:text-[#39FF14] transition-all" />
                        )}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            );
          })()}
        </>
      )}

      <BottomNav />
    </AppShell>
  );
}
