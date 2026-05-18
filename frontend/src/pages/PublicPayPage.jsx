import React, { useEffect, useState, useRef } from "react";
import { useParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Upload,
  Check,
  Clock,
  Copy,
  Receipt,
  Sparkles,
  XCircle,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import axios from "axios";
import { API } from "@/lib/api";

const money = (n) =>
  new Intl.NumberFormat("es-CL", { maximumFractionDigits: 0 }).format(
    Math.round(n || 0)
  );

export default function PublicPayPage() {
  const { shareId, participantId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [note, setNote] = useState("");
  const [file, setFile] = useState(null);
  const [filePreview, setFilePreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);

  const load = async () => {
    try {
      const res = await axios.get(
        `${API}/public/carretes/${shareId}/participants/${participantId}`
      );
      setData(res.data);
    } catch (e) {
      setErr("No encontramos tu cuenta. Pídele al capitán el link correcto.");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
    // eslint-disable-next-line
  }, [shareId, participantId]);

  const pickFile = (f) => {
    if (!f) return;
    setFile(f);
    setFilePreview(URL.createObjectURL(f));
  };

  const reportPay = async (e) => {
    e.preventDefault();
    if (!data) return;
    setUploading(true);
    try {
      let storagePath = null;
      if (file) {
        const fd = new FormData();
        fd.append("file", file);
        const up = await axios.post(`${API}/upload`, fd);
        storagePath = up.data.storage_path;
      }
      await axios.post(
        `${API}/public/carretes/${shareId}/participants/${participantId}/pay`,
        {
          participant_id: participantId,
          amount: data.bill.total,
          screenshot_path: storagePath,
          note,
        }
      );
      toast.success("Pago informado al capitán");
      setFile(null);
      setFilePreview(null);
      setNote("");
      load();
    } catch (e) {
      toast.error("No pudimos enviar el pago");
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-neon-grid flex items-center justify-center">
        <Loader2 size={28} className="text-[#39FF14] animate-spin" />
      </div>
    );
  }
  if (err || !data) {
    return (
      <div className="min-h-screen bg-neon-grid flex items-center justify-center px-6">
        <div className="card-glass text-center max-w-sm" data-testid="public-error">
          <XCircle size={40} className="text-[#FF3366] mx-auto mb-2" />
          <div className="text-white font-bold">{err || "Error"}</div>
        </div>
      </div>
    );
  }

  const pay = data.payment;
  const bill = data.bill;

  return (
    <div className="min-h-screen bg-neon-grid">
      <div className="max-w-md mx-auto px-6 pt-8 pb-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-6"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full glass mb-4">
            <Sparkles size={12} className="text-[#39FF14]" />
            <span className="text-[10px] font-bold tracking-[0.22em] uppercase text-white/80">
              La Dolorosa
            </span>
          </div>
          <p className="text-zinc-400 text-sm">Te cobra {data.captain_name}</p>
          <h1 className="font-display font-black text-3xl text-white">{data.carrete_name}</h1>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="card-glass mb-5 text-center"
          data-testid="public-bill-card"
        >
          <div className="label-small text-[#BF40FF]">Hola {bill.participant_name}</div>
          <div className="text-zinc-400 text-sm mt-1">Tu parte del carrete es</div>
          <div className="font-display font-black text-5xl neon-text mt-3 mb-2">
            ${money(bill.total)}
          </div>
          <div className="flex justify-center gap-4 text-xs text-zinc-400">
            <span>Subtotal ${money(bill.subtotal)}</span>
            <span className="text-zinc-600">·</span>
            <span>Propina ${money(bill.tip)}</span>
          </div>
        </motion.div>

        <div className="card-glass mb-5">
          <div className="flex items-center gap-2 mb-3">
            <Receipt size={16} className="text-[#39FF14]" />
            <div className="font-display font-bold text-white text-sm">Detalle de tu cuenta</div>
          </div>
          <div className="space-y-2 text-sm">
            {bill.items.map((it, i) => (
              <div
                key={i}
                className="flex justify-between text-zinc-200"
                data-testid={`public-item-${i}`}
              >
                <span className="truncate pr-2">
                  {it.name}
                  {it.shared_with > 1 && (
                    <span className="text-[10px] text-zinc-500 ml-1">
                      /{it.shared_with}
                    </span>
                  )}
                </span>
                <span className="font-bold">${money(it.amount)}</span>
              </div>
            ))}
          </div>
        </div>

        {data.captain_bank_details && (
          <div className="card-glass mb-5">
            <div className="flex items-center justify-between mb-2">
              <div className="font-display font-bold text-white text-sm">Datos para transferir</div>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(data.captain_bank_details);
                  toast.success("Copiado");
                }}
                className="text-xs text-[#39FF14] font-bold flex items-center gap-1"
                data-testid="copy-bank-btn"
              >
                <Copy size={12} /> Copiar
              </button>
            </div>
            <pre className="text-zinc-200 text-sm whitespace-pre-wrap font-mono leading-relaxed">
              {data.captain_bank_details}
            </pre>
          </div>
        )}

        {pay && pay.status === "validated" ? (
          <div className="card-glass text-center border border-[#39FF14]/40" data-testid="pay-validated">
            <Check size={36} className="text-[#39FF14] mx-auto mb-2" />
            <div className="font-display font-bold text-xl text-white">¡Pago confirmado!</div>
            <div className="text-sm text-zinc-400 mt-1">
              {data.captain_name} validó tu pago. Buen carrete. 🎉
            </div>
          </div>
        ) : (
          <form onSubmit={reportPay} className="card-glass space-y-4" data-testid="pay-form">
            <div className="flex items-center gap-2">
              {pay?.status === "pending" ? (
                <>
                  <Clock size={16} className="text-[#FFB800]" />
                  <div className="font-display font-bold text-white text-sm">
                    Esperando validación
                  </div>
                </>
              ) : pay?.status === "rejected" ? (
                <>
                  <XCircle size={16} className="text-[#FF3366]" />
                  <div className="font-display font-bold text-white text-sm">
                    Rechazado, reintenta
                  </div>
                </>
              ) : (
                <>
                  <Upload size={16} className="text-[#39FF14]" />
                  <div className="font-display font-bold text-white text-sm">Informar pago</div>
                </>
              )}
            </div>

            <div>
              <label className="label-small">Comprobante (opcional)</label>
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => pickFile(e.target.files?.[0])}
                data-testid="screenshot-input"
              />
              {filePreview ? (
                <div className="relative rounded-xl overflow-hidden border border-white/10">
                  <img src={filePreview} alt="preview" className="w-full max-h-48 object-cover" />
                  <button
                    type="button"
                    onClick={() => {
                      setFile(null);
                      setFilePreview(null);
                    }}
                    className="absolute top-2 right-2 w-8 h-8 rounded-full bg-black/70 flex items-center justify-center text-white"
                  >
                    ×
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => fileRef.current?.click()}
                  className="btn-secondary w-full"
                  data-testid="pick-screenshot-btn"
                >
                  <Upload size={18} /> Subir pantallazo
                </button>
              )}
            </div>

            <div>
              <label className="label-small">Mensaje al capitán (opcional)</label>
              <input
                className="input-field"
                placeholder="Ya transferí, revisa por favor"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                data-testid="pay-note-input"
              />
            </div>

            <button
              type="submit"
              className="btn-primary w-full"
              disabled={uploading}
              data-testid="report-pay-btn"
            >
              <Check size={18} />
              {uploading ? "Enviando..." : "Informar pago"}
            </button>
          </form>
        )}

        <div className="mt-8 text-center text-xs text-zinc-600">
          Vista privada · solo tú ves tu cuenta.
        </div>
      </div>
    </div>
  );
}
