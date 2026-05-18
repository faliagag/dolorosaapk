import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Check, Users } from "lucide-react";

export default function ItemAssignmentModal({ open, onClose, onSave, participants, initial = { name: "", price: "", quantity: 1, consumer_ids: [], is_birthday_item: false } }) {
  const [name, setName] = useState(initial.name || "");
  const [price, setPrice] = useState(initial.price || "");
  const [quantity, setQuantity] = useState(initial.quantity || 1);
  const [consumerIds, setConsumerIds] = useState(initial.consumer_ids || []);
  const [isBirthdayItem, setIsBirthdayItem] = useState(initial.is_birthday_item || false);

  useEffect(() => {
    if (open) {
      setName(initial.name || "");
      setPrice(initial.price || "");
      setQuantity(initial.quantity || 1);
      setConsumerIds(initial.consumer_ids || []);
      setIsBirthdayItem(initial.is_birthday_item || false);
    }
    // eslint-disable-next-line
  }, [open]);

  if (!open) return null;

  const toggleAll = () => {
    if (consumerIds.length === participants.length) setConsumerIds([]);
    else setConsumerIds(participants.map((p) => p.id));
  };
  const toggle = (id) => {
    setConsumerIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const handleSave = () => {
    if (!name.trim() || !price) return;
    onSave({
      name: name.trim(),
      price: parseFloat(price),
      quantity: parseInt(quantity) || 1,
      consumer_ids: isBirthdayItem ? [] : consumerIds,
      is_birthday_item: isBirthdayItem,
    });
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-end sm:items-center justify-center"
        onClick={onClose}
      >
        <motion.div
          initial={{ y: 60, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 60, opacity: 0 }}
          transition={{ type: "spring", damping: 25 }}
          onClick={(e) => e.stopPropagation()}
          data-testid="item-assignment-modal"
          className="w-full sm:max-w-md bg-[#0A0A0A] border border-white/10 rounded-t-3xl sm:rounded-3xl p-6 max-h-[92vh] overflow-y-auto"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display font-bold text-xl text-white">
              {initial?.id ? "Editar ítem" : "Nuevo ítem"}
            </h2>
            <button onClick={onClose} className="w-9 h-9 rounded-full hover:bg-white/10 flex items-center justify-center">
              <X size={18} className="text-white" />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="label-small">Producto</label>
              <input
                data-testid="item-name-input"
                className="input-field"
                placeholder="Ej: Cerveza, Pizza"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label-small">Precio</label>
                <input
                  data-testid="item-price-input"
                  type="number"
                  min="0"
                  step="any"
                  className="input-field"
                  placeholder="0"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                />
              </div>
              <div>
                <label className="label-small">Cantidad</label>
                <input
                  data-testid="item-quantity-input"
                  type="number"
                  min="1"
                  className="input-field"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                />
              </div>
            </div>

            <button
              type="button"
              data-testid="toggle-birthday-item"
              onClick={() => setIsBirthdayItem((v) => !v)}
              className={`w-full rounded-2xl p-4 border transition-all text-left flex items-center gap-3 ${
                isBirthdayItem
                  ? "bg-[#BF40FF]/20 border-[#BF40FF] violet-glow"
                  : "bg-white/5 border-white/10 hover:border-white/20"
              }`}
            >
              <div className="text-2xl">🎂</div>
              <div className="flex-1">
                <div className="font-bold text-white text-sm">Regalo al festejado</div>
                <div className="text-xs text-zinc-400">Se reparte entre todos, excepto el festejado</div>
              </div>
              <div
                className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${
                  isBirthdayItem ? "bg-[#BF40FF] border-[#BF40FF]" : "border-white/30"
                }`}
              >
                {isBirthdayItem && <Check size={14} className="text-white" />}
              </div>
            </button>

            {!isBirthdayItem && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="label-small">¿Quiénes consumieron?</label>
                  <button
                    type="button"
                    onClick={toggleAll}
                    data-testid="toggle-all-btn"
                    className="text-xs font-bold text-[#39FF14] hover:underline"
                  >
                    {consumerIds.length === participants.length ? "Ninguno" : "Todos"}
                  </button>
                </div>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {participants.length === 0 && (
                    <div className="text-center text-zinc-500 text-sm py-4 glass rounded-xl">
                      Agrega participantes primero
                    </div>
                  )}
                  {participants.map((p) => {
                    const selected = consumerIds.includes(p.id);
                    return (
                      <button
                        key={p.id}
                        type="button"
                        data-testid={`consumer-toggle-${p.id}`}
                        onClick={() => toggle(p.id)}
                        className={`w-full flex items-center gap-3 p-3 rounded-xl border transition-all ${
                          selected
                            ? "bg-[#39FF14]/15 border-[#39FF14]"
                            : "bg-white/5 border-white/10"
                        }`}
                      >
                        <div
                          className={`w-6 h-6 rounded-md border-2 flex items-center justify-center ${
                            selected ? "bg-[#39FF14] border-[#39FF14]" : "border-white/20"
                          }`}
                        >
                          {selected && <Check size={14} className="text-black" strokeWidth={3} />}
                        </div>
                        <div className="flex-1 text-left">
                          <div className="text-white font-bold">{p.name}</div>
                        </div>
                        {p.is_birthday && <span className="text-lg">🎂</span>}
                      </button>
                    );
                  })}
                </div>
                {consumerIds.length > 0 && (
                  <div className="mt-2 flex items-center gap-2 text-xs text-zinc-400">
                    <Users size={12} />
                    Se divide entre {consumerIds.length} persona(s)
                  </div>
                )}
              </div>
            )}

            <button
              data-testid="save-item-btn"
              onClick={handleSave}
              disabled={!name.trim() || !price || (!isBirthdayItem && consumerIds.length === 0)}
              className="btn-primary w-full mt-2"
            >
              Guardar ítem
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
