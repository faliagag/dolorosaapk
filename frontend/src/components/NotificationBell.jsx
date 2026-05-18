import React, { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bell, X, Clock } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";

const money = (n) =>
  new Intl.NumberFormat("es-CL", { maximumFractionDigits: 0 }).format(
    Math.round(n || 0)
  );

export default function NotificationBell() {
  const [data, setData] = useState({ pending_count: 0, items: [] });
  const [open, setOpen] = useState(false);
  const prevCount = useRef(0);
  const navigate = useNavigate();

  const load = async () => {
    try {
      const res = await api.get("/notifications");
      if (res.data.pending_count > prevCount.current && prevCount.current > 0) {
        try {
          // Browser notification (best effort)
          if ("Notification" in window && Notification.permission === "granted") {
            new Notification("La Dolorosa", {
              body: `Nuevo pago reportado: $${money(
                res.data.items[0]?.amount
              )} de ${res.data.items[0]?.participant_name}`,
            });
          }
        } catch {}
      }
      prevCount.current = res.data.pending_count;
      setData(res.data);
    } catch {}
  };

  useEffect(() => {
    load();
    const iv = setInterval(load, 20000);
    // Request permission on first mount
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission().catch(() => {});
    }
    return () => clearInterval(iv);
  }, []);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        data-testid="notification-bell"
        className="relative w-12 h-12 rounded-full glass flex items-center justify-center hover:border-[#39FF14]/40 transition"
      >
        <Bell size={18} className="text-white" />
        {data.pending_count > 0 && (
          <span className="absolute -top-1 -right-1 min-w-5 h-5 px-1.5 rounded-full bg-[#FF3366] text-white text-[10px] font-black flex items-center justify-center pulse-neon">
            {data.pending_count}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-end sm:items-center justify-center"
            onClick={() => setOpen(false)}
          >
            <motion.div
              initial={{ y: 40, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 40, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              data-testid="notifications-panel"
              className="w-full sm:max-w-md bg-[#0A0A0A] border border-white/10 rounded-t-3xl sm:rounded-3xl p-6 max-h-[85vh] overflow-y-auto"
            >
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-display font-bold text-lg text-white">
                  Pagos pendientes
                </h2>
                <button
                  onClick={() => setOpen(false)}
                  className="w-9 h-9 rounded-full hover:bg-white/10 flex items-center justify-center"
                >
                  <X size={18} className="text-white" />
                </button>
              </div>

              {data.items.length === 0 ? (
                <div className="text-center py-10 text-zinc-500 text-sm">
                  Todo al día. Los Capitanes perezosos lo agradecen.
                </div>
              ) : (
                <div className="space-y-2">
                  {data.items.map((n) => (
                    <button
                      key={n.payment_id}
                      onClick={() => {
                        setOpen(false);
                        navigate(`/carretes/${n.carrete_id}`);
                      }}
                      data-testid={`notif-${n.payment_id}`}
                      className="w-full glass rounded-xl p-3 text-left hover:border-[#39FF14]/30 transition"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="font-bold text-white truncate">
                            {n.participant_name}
                          </div>
                          <div className="text-xs text-zinc-400 truncate">
                            {n.carrete_name}
                          </div>
                          {n.note && (
                            <div className="text-xs text-zinc-300 italic truncate mt-1">
                              "{n.note}"
                            </div>
                          )}
                        </div>
                        <div className="text-right ml-2">
                          <div className="font-display font-black text-[#39FF14]">
                            ${money(n.amount)}
                          </div>
                          <div className="flex items-center gap-1 text-[10px] text-[#FFB800] justify-end">
                            <Clock size={10} />
                            pendiente
                          </div>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
