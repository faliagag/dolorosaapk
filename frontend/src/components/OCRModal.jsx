import React, { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Upload, Loader2, Sparkles, Wand2 } from "lucide-react";
import Tesseract from "tesseract.js";
import { api } from "@/lib/api";

// Preprocess image: grayscale + contrast boost + binary threshold
// Returns a canvas element ready for Tesseract
function preprocessImage(file) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      URL.revokeObjectURL(url);
      // Upscale small images to help OCR
      const maxW = 1800;
      const scale = img.width < 800 ? 2.5 : img.width > maxW ? maxW / img.width : 1;
      const w = Math.round(img.width * scale);
      const h = Math.round(img.height * scale);

      const canvas = document.createElement("canvas");
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext("2d");
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = "high";
      ctx.drawImage(img, 0, 0, w, h);

      const imageData = ctx.getImageData(0, 0, w, h);
      const data = imageData.data;

      // First pass: grayscale + compute average luminance
      let sum = 0;
      const gray = new Uint8ClampedArray(w * h);
      for (let i = 0, g = 0; i < data.length; i += 4, g++) {
        const lum = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
        gray[g] = lum;
        sum += lum;
      }
      const avg = sum / gray.length;
      // Threshold slightly below average to preserve dark ink
      const threshold = avg * 0.88;

      // Second pass: contrast boost + binary threshold
      for (let i = 0, g = 0; i < data.length; i += 4, g++) {
        // Apply slight contrast boost
        let v = gray[g];
        v = (v - 128) * 1.4 + 128;
        v = Math.max(0, Math.min(255, v));
        // Binary threshold
        const bin = v < threshold ? 0 : 255;
        data[i] = bin;
        data[i + 1] = bin;
        data[i + 2] = bin;
      }
      ctx.putImageData(imageData, 0, 0);
      resolve(canvas);
    };
    img.onerror = (e) => reject(e);
    img.src = url;
  });
}

// Parse receipt text → list of { name, price, quantity }
function parseReceipt(text) {
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 1);

  const items = [];
  // Price regex: captures number at end of line. Supports $1.500, 1.500, 1500, 1.500,00, etc.
  const priceRe = /\$?\s*(\d{1,3}(?:[.,]\d{3})+|\d{2,7})(?:[.,]\d{1,2})?\s*$/;
  // Qty at start: digit(s) followed by whitespace and a letter (no x/* required)
  const qtyRe = /^(\d{1,2})\s+(?=[A-Za-zÁÉÍÓÚÜÑáéíóúüñ])/;

  const skipWords = [
    "total", "subtotal", "sub-total", "propina", "tip", "iva", "neto",
    "cambio", "efectivo", "vuelto", "transferencia", "pago", "tarjeta",
    "debito", "débito", "credito", "crédito", "servicio", "cuenta",
    "cliente", "mesa", "garzon", "garzón", "factura", "boleta", "folio",
    "rut", "fecha", "hora", "direccion", "dirección", "telefono", "teléfono",
    "gracias", "saldo", "monto", "valor", "descuento", "impuesto",
    "personas", "pre-cuenta", "precuenta", "comprobante", "valido", "válido",
    "sugerida", "software", "gastronomico", "gastronómico",
  ];

  // Header-like prefix patterns (line starts with these)
  const headerPrefix = /^(mesa|id|#|fecha|personas|garz|garzon|garzón|folio|ruc|rut|dir|tel|cliente|hora)[:\s]/i;

  for (const raw of lines) {
    // Skip obvious header lines
    if (headerPrefix.test(raw)) continue;

    const m = raw.match(priceRe);
    if (!m) continue;

    // Name = everything before the matched price
    let name = raw.slice(0, raw.lastIndexOf(m[0])).replace(/[\-\*·\s]+$/, "").trim();

    // Parse optional qty marker at start
    let quantity = 1;
    const qm = name.match(qtyRe);
    if (qm) {
      const q = parseInt(qm[1]);
      if (q >= 1 && q <= 50) {
        quantity = q;
        name = name.replace(qtyRe, "").trim();
      }
    }

    if (!name || name.length < 2) continue;

    const lower = name.toLowerCase();
    if (skipWords.some((w) => lower.includes(w))) continue;
    if (/^\d+$/.test(name.replace(/\s/g, ""))) continue;
    // Skip lines that look like "XXX: yyy" headers
    if (/^[^:]{1,14}:\s/.test(name)) continue;

    // Normalize price: remove thousands separators, keep integer part
    const priceStr = m[1].replace(/[.,]/g, "");
    const price = parseFloat(priceStr);
    if (!price || price < 100 || price > 9999999) continue;

    name = name.replace(/[\*·\.]{2,}/g, " ").replace(/\s+/g, " ").trim();
    if (name.length > 45) name = name.slice(0, 45);

    items.push({ name, price, quantity });
  }
  return items;
}

export default function OCRModal({ open, onClose, onItemsParsed }) {
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState("");
  const [previewUrl, setPreviewUrl] = useState(null);
  const [detected, setDetected] = useState([]);
  const [rawText, setRawText] = useState("");
  const [showRaw, setShowRaw] = useState(false);
  const fileInputRef = useRef(null);

  const reset = () => {
    setProcessing(false);
    setProgress(0);
    setStatus("");
    setPreviewUrl(null);
    setDetected([]);
    setRawText("");
    setShowRaw(false);
  };

  const handleFile = async (file) => {
    if (!file) return;
    reset();
    setPreviewUrl(URL.createObjectURL(file));
    setProcessing(true);
    setStatus("Procesando imagen...");
    try {
      const canvas = await preprocessImage(file);
      setStatus("Leyendo texto...");
      const { data } = await Tesseract.recognize(canvas, "spa+eng", {
        logger: (m) => {
          if (m.status === "recognizing text" && m.progress !== undefined) {
            setProgress(Math.round(m.progress * 100));
          }
        },
        // Page Segmentation Mode: assume a single uniform block of text
        // Character whitelist for receipts
        tessedit_pageseg_mode: "6",
        preserve_interword_spaces: "1",
      });
      setRawText(data.text || "");
      const items = parseReceipt(data.text || "");
      setDetected(items);
      setStatus(items.length > 0 ? "" : "No detectamos ítems. Prueba con 'Escanear con IA' o mira el texto crudo.");
    } catch (e) {
      console.error(e);
      setStatus("Error al leer la imagen");
    } finally {
      setProcessing(false);
    }
  };

  const handleAIScan = async (file) => {
    if (!file) return;
    reset();
    setPreviewUrl(URL.createObjectURL(file));
    setProcessing(true);
    setStatus("Analizando con IA...");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await api.post("/ocr/scan", fd, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 60000,
      });
      const items = res.data.items || [];
      setDetected(items);
      setStatus(items.length > 0 ? "" : "La IA no detectó ítems. Intenta con mejor luz o encuadre.");
    } catch (e) {
      console.error(e);
      setStatus("Error al escanear con IA");
    } finally {
      setProcessing(false);
    }
  };

  const confirm = () => {
    onItemsParsed(detected);
    reset();
    onClose();
  };

  const close = () => {
    reset();
    onClose();
  };

  if (!open) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-end sm:items-center justify-center"
        onClick={close}
      >
        <motion.div
          initial={{ y: 80, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 80, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          data-testid="ocr-modal"
          className="w-full sm:max-w-md bg-[#0A0A0A] border border-[#BF40FF]/30 rounded-t-3xl sm:rounded-3xl p-6 max-h-[92vh] overflow-y-auto"
        >
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2">
              <div className="w-9 h-9 rounded-xl bg-[#BF40FF]/20 flex items-center justify-center">
                <Sparkles size={16} className="text-[#BF40FF]" />
              </div>
              <h2 className="font-display font-bold text-lg text-white">Escáner de boleta</h2>
            </div>
            <button onClick={close} className="w-9 h-9 rounded-full hover:bg-white/10 flex items-center justify-center">
              <X size={18} className="text-white" />
            </button>
          </div>

          {!previewUrl && (
            <div className="space-y-3">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                onChange={(e) => handleAIScan(e.target.files?.[0])}
                data-testid="ocr-ai-camera-input"
              />
              <button
                className="w-full h-14 rounded-2xl flex items-center justify-center gap-2 font-bold text-base transition-all relative overflow-hidden"
                style={{
                  background: "linear-gradient(135deg, #BF40FF 0%, #39FF14 120%)",
                  color: "#000",
                  fontFamily: "Unbounded, sans-serif",
                  boxShadow: "0 0 25px rgba(191,64,255,0.45)",
                }}
                onClick={() => fileInputRef.current?.click()}
                data-testid="ocr-ai-btn"
              >
                <Wand2 size={20} />
                Escanear con IA
                <span className="absolute top-1.5 right-2 text-[9px] font-black bg-black/40 text-white px-1.5 py-0.5 rounded-full">
                  RECOMENDADO
                </span>
              </button>
              <input
                type="file"
                accept="image/*"
                className="hidden"
                id="ocr-classic-upload"
                onChange={(e) => handleFile(e.target.files?.[0])}
                data-testid="ocr-upload-input"
              />
              <label htmlFor="ocr-classic-upload" className="btn-secondary w-full cursor-pointer">
                <Upload size={18} />
                OCR clásico (offline)
              </label>
              <div className="mt-3 glass rounded-xl p-3">
                <div className="text-[11px] font-bold text-[#39FF14] uppercase tracking-wider mb-1">
                  Tips para mejor lectura
                </div>
                <ul className="text-[11px] text-zinc-400 space-y-0.5 leading-relaxed">
                  <li>• Apoya la boleta sobre una superficie plana</li>
                  <li>• Buena luz, sin sombras ni brillos</li>
                  <li>• Encuadra que se vea toda la boleta y recto</li>
                  <li>• Si OCR clásico falla, usa "Escanear con IA"</li>
                </ul>
              </div>
            </div>
          )}

          {previewUrl && (
            <div className="space-y-4">
              <div className="relative rounded-2xl overflow-hidden border border-white/10">
                <img src={previewUrl} alt="receipt" className="w-full max-h-56 object-cover" />
                {processing && (
                  <div className="absolute inset-0 bg-black/75 flex flex-col items-center justify-center">
                    <Loader2 size={30} className="text-[#39FF14] animate-spin mb-2" />
                    <div className="text-white font-bold text-sm">{status || "Leyendo..."}</div>
                    {progress > 0 && (
                      <div className="text-zinc-400 text-xs mt-1">{progress}%</div>
                    )}
                  </div>
                )}
              </div>

              {!processing && (
                <>
                  <div className="flex items-center justify-between">
                    <div className="label-small">Ítems detectados ({detected.length})</div>
                    {rawText && (
                      <button
                        onClick={() => setShowRaw((v) => !v)}
                        className="text-[10px] text-zinc-400 hover:text-white underline"
                        data-testid="toggle-raw-ocr"
                      >
                        {showRaw ? "Ocultar" : "Ver"} texto crudo
                      </button>
                    )}
                  </div>
                  {showRaw && rawText && (
                    <pre className="glass rounded-xl p-3 text-[10px] text-zinc-300 whitespace-pre-wrap max-h-32 overflow-y-auto font-mono">
                      {rawText}
                    </pre>
                  )}
                  {detected.length === 0 ? (
                    <div className="text-center text-zinc-400 text-sm py-6 glass rounded-xl">
                      {status || "No se detectaron ítems. Agrégalos manualmente o reintenta con mejor luz."}
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-52 overflow-y-auto" data-testid="ocr-items-list">
                      {detected.map((it, i) => (
                        <div key={i} className="flex items-center gap-2 p-3 glass rounded-xl">
                          <input
                            className="input-field flex-1 h-10"
                            style={{ height: "2.5rem", fontSize: "0.95rem" }}
                            value={it.name}
                            onChange={(e) => {
                              const next = [...detected];
                              next[i] = { ...next[i], name: e.target.value };
                              setDetected(next);
                            }}
                          />
                          <input
                            type="number"
                            className="input-field w-24 h-10"
                            style={{ height: "2.5rem", fontSize: "0.95rem" }}
                            value={it.price}
                            onChange={(e) => {
                              const next = [...detected];
                              next[i] = { ...next[i], price: parseFloat(e.target.value) || 0 };
                              setDetected(next);
                            }}
                          />
                          <button
                            onClick={() => setDetected((d) => d.filter((_, idx) => idx !== i))}
                            className="w-8 h-8 rounded-lg hover:bg-[#FF3366]/20 text-[#FF3366] flex items-center justify-center"
                          >
                            <X size={14} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="flex gap-3">
                    <button onClick={reset} className="btn-secondary flex-1">
                      Otra foto
                    </button>
                    <button
                      onClick={confirm}
                      disabled={detected.length === 0}
                      data-testid="ocr-confirm-btn"
                      className="btn-primary flex-1"
                    >
                      Agregar {detected.length}
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
