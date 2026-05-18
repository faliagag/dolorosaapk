import React, { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Plus,
  Users,
  Receipt,
  Camera,
  Trash2,
  Edit2,
  MessageCircle,
  Share2,
  Check,
  X,
  ChevronDown,
  ChevronUp,
  Link2,
  FileDown,
  Instagram,
  Copy as CopyIcon,
  Archive,
  RotateCcw,
  Cake,
  Lock,
  Unlock,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import AppShell from "@/components/AppShell";
import BottomNav from "@/components/BottomNav";
import ItemAssignmentModal from "@/components/ItemAssignmentModal";
import OCRModal from "@/components/OCRModal";
import { exportCarretePDF, exportStoryImage } from "@/lib/exports";

const money = (n) =>
  new Intl.NumberFormat("es-CL", { maximumFractionDigits: 0 }).format(
    Math.round(n || 0)
  );

export default function CarreteDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [carrete, setCarrete] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [newParticipant, setNewParticipant] = useState("");
  const [showItemModal, setShowItemModal] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [showOCR, setShowOCR] = useState(false);
  const [expandedPerson, setExpandedPerson] = useState(null);
  const [showShare, setShowShare] = useState(false);
  const [exportingStory, setExportingStory] = useState(false);
  const [editOverride, setEditOverride] = useState(false);
  const storyRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const [c, s] = await Promise.all([
        api.get(`/carretes/${id}`),
        api.get(`/carretes/${id}/summary`),
      ]);
      setCarrete(c.data);
      setSummary(s.data);
    } catch (e) {
      toast.error("No se pudo cargar el carrete");
      navigate("/dashboard");
    } finally {
      setLoading(false);
    }
  }, [id, navigate]);

  useEffect(() => {
    load();
  }, [load]);

  const addParticipant = async (e) => {
    e.preventDefault();
    if (!newParticipant.trim()) return;
    await api.post(`/carretes/${id}/participants`, {
      name: newParticipant.trim(),
      is_birthday: false,
    });
    setNewParticipant("");
    load();
  };

  const toggleBirthday = async (p) => {
    await api.put(`/carretes/${id}/participants/${p.id}`, {
      name: p.name,
      is_birthday: !p.is_birthday,
    });
    load();
  };

  const removeParticipant = async (pid) => {
    await api.delete(`/carretes/${id}/participants/${pid}`);
    toast.success("Participante eliminado");
    load();
  };

  const saveItem = async (data) => {
    if (editingItem) {
      await api.put(`/carretes/${id}/items/${editingItem.id}`, data);
      toast.success("Ítem actualizado");
    } else {
      await api.post(`/carretes/${id}/items`, data);
      toast.success("Ítem agregado");
    }
    setShowItemModal(false);
    setEditingItem(null);
    load();
  };

  const deleteItem = async (iid) => {
    await api.delete(`/carretes/${id}/items/${iid}`);
    load();
  };

  const setTipPercent = async (pct) => {
    await api.put(`/carretes/${id}`, { tip_percent: pct });
    load();
  };

  const onOCRItems = async (items) => {
    if (!carrete) return;
    const allIds = carrete.participants.map((p) => p.id);
    for (const it of items) {
      await api.post(`/carretes/${id}/items`, {
        name: it.name,
        price: it.price,
        quantity: 1,
        consumer_ids: allIds,
        is_birthday_item: false,
      });
    }
    toast.success(`${items.length} ítems agregados`);
    load();
  };

  const validatePayment = async (paymentId, status) => {
    await api.put(
      `/carretes/${id}/payments/${paymentId}/validate?status=${status}`
    );
    toast.success(status === "validated" ? "Pago confirmado" : "Pago rechazado");
    load();
  };

  const shareLink = (pid) =>
    `${window.location.origin}/pay/${carrete.share_id}/${pid}`;

  const toggleClose = async () => {
    const newStatus = carrete.status === "closed" ? "active" : "closed";
    await api.put(`/carretes/${id}`, { status: newStatus });
    toast.success(newStatus === "closed" ? "Carrete archivado" : "Carrete reactivado");
    load();
  };

  const duplicate = async () => {
    const res = await api.post(`/carretes/${id}/duplicate`);
    toast.success("Carrete duplicado");
    navigate(`/carretes/${res.data.id}`);
  };

  const onExportPDF = async () => {
    try {
      await exportCarretePDF(carrete, summary, user?.name);
      toast.success("PDF listo");
    } catch (e) {
      toast.error("Error al generar PDF");
    }
  };

  const onExportStory = async () => {
    if (!storyRef.current) return;
    setExportingStory(true);
    try {
      // make node visible briefly for canvas capture
      storyRef.current.style.position = "fixed";
      storyRef.current.style.left = "-9999px";
      storyRef.current.style.top = "0";
      storyRef.current.style.display = "block";
      await new Promise((r) => setTimeout(r, 50));
      await exportStoryImage(storyRef.current);
      toast.success("Imagen lista para tu story");
    } catch (e) {
      toast.error("No se pudo generar la imagen");
    } finally {
      storyRef.current.style.display = "none";
      setExportingStory(false);
    }
  };

  const whatsappMsg = (person) => {
    const lines = [];
    lines.push(`¡Hola ${person.participant_name}! 🧾`);
    lines.push(`Tu parte del carrete "${carrete.name}" es $${money(person.total)}.`);
    if (person.items?.length) {
      lines.push("");
      lines.push("Detalle:");
      person.items.slice(0, 8).forEach((it) => {
        lines.push(`• ${it.name}: $${money(it.amount)}`);
      });
      if (person.tip > 0) lines.push(`• Propina (${summary.tip_percent}%): $${money(person.tip)}`);
    }
    if (user?.bank_details) {
      lines.push("");
      lines.push("Datos para transferir:");
      lines.push(user.bank_details);
    }
    lines.push("");
    lines.push(`Confirma tu pago aquí: ${shareLink(person.participant_id)}`);
    return encodeURIComponent(lines.join("\n"));
  };

  if (loading || !carrete || !summary) {
    return (
      <AppShell>
        <div className="text-zinc-400">Cargando...</div>
      </AppShell>
    );
  }

  const paymentsByPid = {};
  (carrete.payments || []).forEach((p) => {
    paymentsByPid[p.participant_id] = p;
  });

  const hasPayments = (carrete.payments || []).length > 0;
  const locked = hasPayments && !editOverride;

  return (
    <AppShell>
      <button
        onClick={() => navigate("/dashboard")}
        className="mb-4 flex items-center gap-2 text-zinc-400 hover:text-white transition"
        data-testid="back-btn"
      >
        <ArrowLeft size={18} /> Volver
      </button>

      <div className="card-glass mb-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="label-small text-[#39FF14]">
              {carrete.status === "closed" ? "Carrete archivado" : "Carrete activo"}
            </p>
            <h1 className="font-display font-black text-2xl text-white">{carrete.name}</h1>
          </div>
          <button
            onClick={toggleClose}
            data-testid="toggle-close-btn"
            className={`h-9 px-3 rounded-xl text-xs font-bold flex items-center gap-1 transition-all ${
              carrete.status === "closed"
                ? "bg-[#39FF14] text-black"
                : "bg-white/5 border border-white/10 text-zinc-300 hover:border-white/20"
            }`}
          >
            {carrete.status === "closed" ? (
              <>
                <RotateCcw size={12} />
                Reabrir
              </>
            ) : (
              <>
                <Archive size={12} />
                Cerrar
              </>
            )}
          </button>
        </div>
        <div className="grid grid-cols-3 gap-3 mt-4">
          <div className="text-center glass rounded-xl py-2">
            <div className="text-[10px] text-zinc-400 uppercase tracking-wider">Personas</div>
            <div className="font-display font-black text-xl text-white">
              {carrete.participants.length}
            </div>
          </div>
          <div className="text-center glass rounded-xl py-2">
            <div className="text-[10px] text-zinc-400 uppercase tracking-wider">Ítems</div>
            <div className="font-display font-black text-xl text-white">
              {carrete.items.length}
            </div>
          </div>
          <div className="text-center glass rounded-xl py-2">
            <div className="text-[10px] text-zinc-400 uppercase tracking-wider">Total</div>
            <div className="font-display font-black text-xl neon-text">
              ${money(summary.grand_total)}
            </div>
          </div>
        </div>
      </div>

      {/* Festejado banner */}
      {carrete.participants.some((p) => p.is_birthday) && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-5 relative overflow-hidden rounded-2xl border border-[#BF40FF]/50 p-4 violet-glow"
          style={{
            background:
              "linear-gradient(135deg, rgba(191,64,255,0.18) 0%, rgba(0,0,0,0.6) 100%)",
          }}
          data-testid="festejado-banner"
        >
          <div className="flex items-center gap-3">
            <div className="text-3xl">🎂</div>
            <div className="flex-1 min-w-0">
              <div className="label-small text-[#BF40FF]">Festejado/a</div>
              <div className="font-display font-black text-white text-lg truncate">
                {carrete.participants
                  .filter((p) => p.is_birthday)
                  .map((p) => p.name)
                  .join(", ")}
              </div>
              <div className="text-xs text-zinc-300">
                Paga $0 — todo lo que consumió se reparte entre los demás
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Lock banner when payments have been reported */}
      {hasPayments && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`mb-5 rounded-2xl border p-4 ${
            locked
              ? "bg-[#FFB800]/10 border-[#FFB800]/50"
              : "bg-[#FF3366]/10 border-[#FF3366]/50"
          }`}
          data-testid="lock-banner"
        >
          <div className="flex items-center gap-3">
            {locked ? (
              <Lock size={20} className="text-[#FFB800] shrink-0" />
            ) : (
              <Unlock size={20} className="text-[#FF3366] shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <div className="font-display font-bold text-white text-sm">
                {locked ? "Carrete bloqueado" : "Modo edición activo"}
              </div>
              <div className="text-xs text-zinc-300 leading-relaxed">
                {locked
                  ? "Ya hay pagos reportados. Si modificas la cuenta, los montos cobrados pueden quedar descuadrados."
                  : "Cuidado: los cambios afectan pagos ya reportados. Los estados de pago se conservan."}
              </div>
            </div>
            <button
              onClick={() => setEditOverride((v) => !v)}
              data-testid="toggle-edit-override"
              className={`h-9 px-3 rounded-xl text-xs font-bold flex items-center gap-1 transition-all shrink-0 ${
                locked
                  ? "bg-[#FFB800] text-black hover:shadow-[0_0_15px_rgba(255,184,0,0.4)]"
                  : "bg-white/10 border border-white/20 text-white hover:bg-white/20"
              }`}
            >
              {locked ? (
                <>
                  <Edit2 size={12} />
                  Editar
                </>
              ) : (
                <>
                  <Lock size={12} />
                  Bloquear
                </>
              )}
            </button>
          </div>
        </motion.div>
      )}

      {/* Participants */}
      <section className="mb-5">
        <div className="flex items-center gap-2 mb-3">
          <Users size={16} className="text-[#39FF14]" />
          <h2 className="font-display font-bold text-white">Participantes</h2>
        </div>

        <form onSubmit={addParticipant} className={`flex gap-2 mb-3 ${locked ? "opacity-40 pointer-events-none" : ""}`}>
          <input
            data-testid="new-participant-input"
            className="input-field flex-1"
            placeholder="Nombre del participante"
            value={newParticipant}
            onChange={(e) => setNewParticipant(e.target.value)}
            disabled={locked}
          />
          <button
            type="submit"
            data-testid="add-participant-btn"
            disabled={locked}
            className="h-14 px-4 rounded-2xl bg-[#39FF14] text-black font-bold flex items-center justify-center hover:shadow-[0_0_20px_rgba(57,255,20,0.5)] transition disabled:opacity-40"
          >
            <Plus size={22} strokeWidth={3} />
          </button>
        </form>

        {carrete.participants.length === 0 && (
          <div className="text-center text-zinc-500 text-sm py-4 glass rounded-xl">
            Agrega al primer integrante del carrete
          </div>
        )}

        {carrete.participants.length > 0 && !carrete.participants.some((p) => p.is_birthday) && (
          <div className="text-[11px] text-zinc-500 mb-2 flex items-center gap-1">
            <Cake size={11} className="text-[#BF40FF]" />
            Tip: toca el ícono 👤 para marcar al festejado y excluirlo de su regalo.
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          {carrete.participants.map((p) => (
            <div
              key={p.id}
              data-testid={`participant-chip-${p.id}`}
              className={`group flex items-center gap-2 pl-3 pr-1.5 py-1.5 rounded-full border transition-all ${
                p.is_birthday
                  ? "bg-[#BF40FF]/20 border-[#BF40FF]/60"
                  : "bg-white/5 border-white/10"
              }`}
            >
              <button
                onClick={() => !locked && toggleBirthday(p)}
                title="Marcar como festejado"
                data-testid={`toggle-birthday-${p.id}`}
                className={`text-lg ${locked ? "cursor-not-allowed" : ""}`}
                disabled={locked}
              >
                {p.is_birthday ? "🎂" : "👤"}
              </button>
              <span className="text-white text-sm font-bold">{p.name}</span>
              <button
                onClick={() => removeParticipant(p.id)}
                className="w-6 h-6 rounded-full hover:bg-[#FF3366]/30 flex items-center justify-center text-zinc-500 hover:text-[#FF3366]"
                data-testid={`remove-participant-${p.id}`}
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* Items */}
      <section className="mb-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Receipt size={16} className="text-[#39FF14]" />
            <h2 className="font-display font-bold text-white">Productos</h2>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowOCR(true)}
              data-testid="open-ocr-btn"
              disabled={locked}
              className="h-10 px-3 rounded-xl bg-[#BF40FF]/20 border border-[#BF40FF]/40 text-[#BF40FF] font-bold text-xs flex items-center gap-1 hover:bg-[#BF40FF]/30 transition disabled:opacity-40"
            >
              <Camera size={14} />
              OCR
            </button>
            <button
              onClick={() => {
                setEditingItem(null);
                setShowItemModal(true);
              }}
              data-testid="add-item-btn"
              disabled={locked}
              className="h-10 px-3 rounded-xl bg-[#39FF14] text-black font-bold text-xs flex items-center gap-1 hover:shadow-[0_0_15px_rgba(57,255,20,0.5)] transition disabled:opacity-40"
            >
              <Plus size={14} strokeWidth={3} />
              Ítem
            </button>
          </div>
        </div>

        {carrete.items.length === 0 ? (
          <div className="text-center text-zinc-500 text-sm py-6 glass rounded-xl">
            Aún no hay productos
          </div>
        ) : (
          <div className="space-y-2">
            {carrete.items.map((it) => (
              <div
                key={it.id}
                data-testid={`item-card-${it.id}`}
                className="glass rounded-xl p-3 flex items-center gap-3"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    {it.is_birthday_item && <span>🎂</span>}
                    <div className="font-bold text-white truncate">{it.name}</div>
                  </div>
                  <div className="text-xs text-zinc-400">
                    {it.quantity > 1 && `x${it.quantity} · `}
                    {it.is_birthday_item
                      ? "repartido entre todos (excepto festejado)"
                      : `${it.consumer_ids.length} persona(s)`}
                  </div>
                </div>
                <div className="font-display font-black text-white">
                  ${money(it.price * (it.quantity || 1))}
                </div>
                <button
                  onClick={() => {
                    setEditingItem(it);
                    setShowItemModal(true);
                  }}
                  disabled={locked}
                  className="w-8 h-8 rounded-lg hover:bg-white/10 text-zinc-400 flex items-center justify-center disabled:opacity-30 disabled:cursor-not-allowed"
                  data-testid={`edit-item-${it.id}`}
                >
                  <Edit2 size={14} />
                </button>
                <button
                  onClick={() => deleteItem(it.id)}
                  className="w-8 h-8 rounded-lg hover:bg-[#FF3366]/20 text-zinc-500 hover:text-[#FF3366] flex items-center justify-center"
                  data-testid={`delete-item-${it.id}`}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Tip */}
      <section className="mb-5 card-glass">
        <div className="flex items-center justify-between mb-3">
          <div>
            <div className="label-small">Propina</div>
            <div className="font-display font-black text-2xl neon-text">
              {summary.tip_percent}%
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-zinc-400">Propina total</div>
            <div className="font-display font-bold text-white">${money(summary.grand_tip)}</div>
          </div>
        </div>
        <input
          data-testid="tip-slider"
          type="range"
          min={0}
          max={25}
          step={1}
          value={summary.tip_percent}
          onChange={(e) => setTipPercent(parseFloat(e.target.value))}
          disabled={locked}
          className="w-full accent-[#39FF14] disabled:opacity-40"
        />
        <div className="flex justify-between mt-2 text-xs text-zinc-500">
          <span>0%</span>
          <span>10%</span>
          <span>25%</span>
        </div>
      </section>

      {/* Summary per person */}
      <section className="mb-5">
        <div className="flex items-center gap-2 mb-3">
          <Share2 size={16} className="text-[#BF40FF]" />
          <h2 className="font-display font-bold text-white">La dolorosa por persona</h2>
        </div>
        {summary.per_person.length === 0 ? (
          <div className="text-center text-zinc-500 text-sm py-6 glass rounded-xl">
            Agrega participantes e ítems para calcular
          </div>
        ) : (
          <div className="space-y-2">
            {summary.per_person.map((person) => {
              const pay = paymentsByPid[person.participant_id];
              const isOpen = expandedPerson === person.participant_id;
              return (
                <motion.div
                  key={person.participant_id}
                  data-testid={`person-summary-${person.participant_id}`}
                  className={`glass rounded-2xl overflow-hidden ${
                    pay?.status === "validated" ? "border border-[#39FF14]/50" : ""
                  }`}
                >
                  <button
                    onClick={() =>
                      setExpandedPerson(isOpen ? null : person.participant_id)
                    }
                    className="w-full flex items-center gap-3 p-4 text-left"
                  >
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center font-display font-black text-lg ${
                        person.is_birthday
                          ? "bg-[#BF40FF] text-white"
                          : "bg-white/10 text-white"
                      }`}
                    >
                      {person.is_birthday ? "🎂" : person.participant_name[0]?.toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <div className="font-bold text-white truncate">
                          {person.participant_name}
                        </div>
                        {pay && (
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                              pay.status === "validated"
                                ? "bg-[#39FF14]/20 text-[#39FF14]"
                                : pay.status === "rejected"
                                ? "bg-[#FF3366]/20 text-[#FF3366]"
                                : "bg-[#FFB800]/20 text-[#FFB800]"
                            }`}
                          >
                            {pay.status === "validated"
                              ? "✓ pagado"
                              : pay.status === "rejected"
                              ? "rechazado"
                              : "pendiente"}
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-zinc-400">
                        {person.items.length} ítems · propina ${money(person.tip)}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-display font-black text-lg neon-text">
                        ${money(person.total)}
                      </div>
                    </div>
                    {isOpen ? (
                      <ChevronUp size={16} className="text-zinc-400" />
                    ) : (
                      <ChevronDown size={16} className="text-zinc-400" />
                    )}
                  </button>

                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      className="border-t border-white/10 p-4 space-y-3"
                    >
                      <div className="space-y-1 text-sm">
                        {person.items.map((it, i) => (
                          <div key={i} className="flex justify-between text-zinc-300">
                            <span className="truncate">{it.name}</span>
                            <span className="font-bold ml-2">${money(it.amount)}</span>
                          </div>
                        ))}
                        <div className="flex justify-between text-zinc-400 pt-2 border-t border-white/5">
                          <span>Subtotal</span>
                          <span>${money(person.subtotal)}</span>
                        </div>
                        <div className="flex justify-between text-zinc-400">
                          <span>Propina</span>
                          <span>${money(person.tip)}</span>
                        </div>
                      </div>

                      {pay && (
                        <div className="glass rounded-xl p-3 space-y-2">
                          <div className="text-xs text-zinc-400">Pago reportado</div>
                          <div className="flex justify-between text-sm">
                            <span className="text-white">Monto</span>
                            <span className="font-bold text-white">${money(pay.amount)}</span>
                          </div>
                          {pay.note && (
                            <div className="text-xs text-zinc-300 italic">"{pay.note}"</div>
                          )}
                          {pay.screenshot_path && (
                            <a
                              href={`${process.env.REACT_APP_BACKEND_URL}/api/files/${pay.screenshot_path.split("/").pop().split(".")[0]}`}
                              target="_blank"
                              rel="noreferrer"
                              className="text-[#39FF14] text-xs underline"
                            >
                              Ver comprobante
                            </a>
                          )}
                          {pay.status !== "validated" && (
                            <div className="flex gap-2 pt-2">
                              <button
                                onClick={() => validatePayment(pay.id, "validated")}
                                data-testid={`validate-payment-${pay.id}`}
                                className="flex-1 h-10 rounded-xl bg-[#39FF14] text-black font-bold text-xs flex items-center justify-center gap-1"
                              >
                                <Check size={14} /> Confirmar
                              </button>
                              <button
                                onClick={() => validatePayment(pay.id, "rejected")}
                                className="flex-1 h-10 rounded-xl bg-white/5 border border-white/10 text-[#FF3366] font-bold text-xs"
                              >
                                Rechazar
                              </button>
                            </div>
                          )}
                        </div>
                      )}

                      <div className="flex gap-2">
                        <a
                          href={`https://wa.me/?text=${whatsappMsg(person)}`}
                          target="_blank"
                          rel="noreferrer"
                          data-testid={`wa-btn-${person.participant_id}`}
                          className="flex-1 h-11 rounded-xl bg-[#39FF14] text-black font-bold text-xs flex items-center justify-center gap-1"
                        >
                          <MessageCircle size={14} /> WhatsApp
                        </a>
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(shareLink(person.participant_id));
                            toast.success("Link copiado");
                          }}
                          className="flex-1 h-11 rounded-xl bg-white/5 border border-white/10 text-white font-bold text-xs flex items-center justify-center gap-1"
                          data-testid={`copy-link-${person.participant_id}`}
                        >
                          <Link2 size={14} /> Copiar link
                        </button>
                      </div>
                    </motion.div>
                  )}
                </motion.div>
              );
            })}
          </div>
        )}
      </section>

      <button
        onClick={() => setShowShare((s) => !s)}
        className="btn-violet w-full"
        data-testid="share-carrete-btn"
      >
        <Share2 size={18} />
        {showShare ? "Ocultar resumen" : "Resumen general"}
      </button>
      {showShare && (
        <div className="card-glass mt-3 space-y-2">
          <div className="flex justify-between text-zinc-300">
            <span>Subtotal</span>
            <span className="font-bold">${money(summary.grand_subtotal)}</span>
          </div>
          <div className="flex justify-between text-zinc-300">
            <span>Propina {summary.tip_percent}%</span>
            <span className="font-bold">${money(summary.grand_tip)}</span>
          </div>
          <div className="flex justify-between pt-2 border-t border-white/10">
            <span className="font-display font-bold text-white">TOTAL</span>
            <span className="font-display font-black neon-text text-xl">
              ${money(summary.grand_total)}
            </span>
          </div>
        </div>
      )}

      {/* Export / Actions */}
      <div className="grid grid-cols-3 gap-2 mt-4">
        <button
          onClick={onExportPDF}
          data-testid="export-pdf-btn"
          className="h-14 rounded-2xl bg-white/5 border border-white/10 hover:border-[#39FF14]/40 flex flex-col items-center justify-center gap-1 transition"
        >
          <FileDown size={18} className="text-[#39FF14]" />
          <span className="text-[10px] font-bold text-white uppercase tracking-wider">PDF</span>
        </button>
        <button
          onClick={onExportStory}
          disabled={exportingStory}
          data-testid="export-story-btn"
          className="h-14 rounded-2xl bg-white/5 border border-white/10 hover:border-[#BF40FF]/40 flex flex-col items-center justify-center gap-1 transition disabled:opacity-60"
        >
          <Instagram size={18} className="text-[#BF40FF]" />
          <span className="text-[10px] font-bold text-white uppercase tracking-wider">
            {exportingStory ? "..." : "Story IG"}
          </span>
        </button>
        <button
          onClick={duplicate}
          data-testid="duplicate-btn"
          className="h-14 rounded-2xl bg-white/5 border border-white/10 hover:border-white/30 flex flex-col items-center justify-center gap-1 transition"
        >
          <CopyIcon size={18} className="text-white" />
          <span className="text-[10px] font-bold text-white uppercase tracking-wider">Duplicar</span>
        </button>
      </div>

      {/* Hidden IG Story canvas (1080x1920) */}
      <div
        ref={storyRef}
        style={{
          display: "none",
          width: "1080px",
          height: "1920px",
          background:
            "linear-gradient(160deg, #050505 0%, #0a0a0a 40%, #1a0a2a 100%)",
          color: "white",
          padding: "80px",
          boxSizing: "border-box",
          fontFamily: "'Unbounded', sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "40px" }}>
          <div
            style={{
              width: "16px",
              height: "16px",
              borderRadius: "50%",
              background: "#39FF14",
              boxShadow: "0 0 24px #39FF14",
            }}
          />
          <div
            style={{
              fontSize: "24px",
              fontWeight: 700,
              letterSpacing: "0.3em",
              color: "#A1A1AA",
            }}
          >
            LA DOLOROSA
          </div>
        </div>
        <div
          style={{
            fontSize: "80px",
            fontWeight: 900,
            lineHeight: 1,
            color: "#39FF14",
            textShadow: "0 0 40px rgba(57,255,20,0.6)",
            marginBottom: "20px",
          }}
        >
          {carrete.name}
        </div>
        <div style={{ fontSize: "32px", color: "#A1A1AA", marginBottom: "60px" }}>
          {carrete.participants.length} personas · {carrete.items.length} ítems
        </div>
        <div
          style={{
            background: "rgba(255,255,255,0.05)",
            border: "2px solid rgba(57,255,20,0.4)",
            borderRadius: "40px",
            padding: "60px",
            marginBottom: "60px",
          }}
        >
          <div style={{ fontSize: "28px", color: "#A1A1AA", textTransform: "uppercase", letterSpacing: "0.2em" }}>
            Total
          </div>
          <div
            style={{
              fontSize: "160px",
              fontWeight: 900,
              color: "#39FF14",
              textShadow: "0 0 60px rgba(57,255,20,0.7)",
              lineHeight: 1,
              marginTop: "20px",
            }}
          >
            ${money(summary.grand_total)}
          </div>
          <div style={{ fontSize: "32px", color: "#A1A1AA", marginTop: "20px" }}>
            Subtotal ${money(summary.grand_subtotal)} · Propina {summary.tip_percent}%
          </div>
        </div>
        <div style={{ fontSize: "28px", color: "#fff", marginBottom: "20px", fontWeight: 700 }}>
          Cuenta por persona
        </div>
        {summary.per_person.slice(0, 8).map((p, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "24px 0",
              borderBottom: "1px solid rgba(255,255,255,0.1)",
            }}
          >
            <div style={{ fontSize: "34px", color: "#fff" }}>
              {p.is_birthday ? "🎂 " : ""}
              {p.participant_name}
            </div>
            <div style={{ fontSize: "38px", fontWeight: 900, color: "#BF40FF" }}>
              ${money(p.total)}
            </div>
          </div>
        ))}
        <div
          style={{
            position: "absolute",
            bottom: "80px",
            left: "80px",
            right: "80px",
            textAlign: "center",
            color: "#71717A",
            fontSize: "22px",
            letterSpacing: "0.15em",
          }}
        >
          GENERADO CON LA DOLOROSA
        </div>
      </div>

      <ItemAssignmentModal
        open={showItemModal}
        onClose={() => {
          setShowItemModal(false);
          setEditingItem(null);
        }}
        onSave={saveItem}
        participants={carrete.participants}
        initial={editingItem || undefined}
      />
      <OCRModal
        open={showOCR}
        onClose={() => setShowOCR(false)}
        onItemsParsed={onOCRItems}
      />

      <BottomNav />
    </AppShell>
  );
}
