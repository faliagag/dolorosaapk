import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Download, X, Share } from "lucide-react";

// Detects iOS Safari where PWA install is via "Share → Add to Home Screen"
function isIOS() {
  return /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
}

function isStandalone() {
  return (
    window.matchMedia?.("(display-mode: standalone)").matches ||
    window.navigator.standalone === true
  );
}

const DISMISS_KEY = "ladolorosa_install_dismissed_at";

export default function InstallPrompt() {
  const [deferred, setDeferred] = useState(null);
  const [open, setOpen] = useState(false);
  const [showIOS, setShowIOS] = useState(false);

  useEffect(() => {
    if (isStandalone()) return;
    // Rate-limit: dismissed within last 7 days?
    const dismissed = parseInt(localStorage.getItem(DISMISS_KEY) || "0");
    if (dismissed && Date.now() - dismissed < 7 * 24 * 60 * 60 * 1000) return;

    const onPrompt = (e) => {
      e.preventDefault();
      setDeferred(e);
      setTimeout(() => setOpen(true), 2500);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);

    // iOS doesn't fire beforeinstallprompt — show custom hint after delay
    if (isIOS() && !isStandalone()) {
      setTimeout(() => {
        setShowIOS(true);
        setOpen(true);
      }, 3500);
    }

    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, []);

  const install = async () => {
    if (!deferred) return;
    deferred.prompt();
    await deferred.userChoice;
    setDeferred(null);
    close();
  };

  const close = () => {
    setOpen(false);
    localStorage.setItem(DISMISS_KEY, String(Date.now()));
  };

  if (!open) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 30 }}
        transition={{ type: "spring", damping: 22 }}
        data-testid="install-prompt"
        className="fixed bottom-24 left-4 right-4 max-w-md mx-auto z-[60]"
      >
        <div
          className="card-glass !p-4 flex items-center gap-3"
          style={{
            background: "rgba(10,10,10,0.92)",
            borderColor: "rgba(57,255,20,0.35)",
            boxShadow: "0 20px 60px rgba(0,0,0,0.6), 0 0 25px rgba(57,255,20,0.12)",
          }}
        >
          <div className="w-11 h-11 rounded-xl bg-[#39FF14] flex items-center justify-center shrink-0">
            <Download size={20} className="text-black" strokeWidth={3} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-display font-bold text-white text-sm">
              Instala La Dolorosa
            </div>
            <div className="text-[11px] text-zinc-400 leading-snug">
              {showIOS ? (
                <span className="flex items-center gap-1 flex-wrap">
                  Toca <Share size={11} className="inline text-[#39FF14]" /> y luego
                  "Añadir a pantalla de inicio"
                </span>
              ) : (
                "Úsala como app nativa en tu home screen."
              )}
            </div>
          </div>
          {!showIOS && deferred && (
            <button
              onClick={install}
              data-testid="install-btn"
              className="h-10 px-4 rounded-xl bg-[#39FF14] text-black font-bold text-sm hover:shadow-[0_0_15px_rgba(57,255,20,0.55)] transition whitespace-nowrap"
            >
              Instalar
            </button>
          )}
          <button
            onClick={close}
            data-testid="dismiss-install"
            className="w-8 h-8 rounded-full hover:bg-white/10 flex items-center justify-center shrink-0"
            aria-label="Cerrar"
          >
            <X size={16} className="text-zinc-400" />
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
