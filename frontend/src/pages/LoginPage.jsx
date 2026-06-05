import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, LogIn, Mail, Lock, User, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

function formatErr(detail) {
  if (!detail) return "Ocurrió un error";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(" · ");
  }
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export default function LoginPage() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState("choice"); // choice | login | register
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);

  const handleGoogleLogin = () => {
    // Redirige al backend que inicia el flujo OAuth con Google
    const backendUrl = process.env.REACT_APP_BACKEND_URL || "";
    window.location.href = `${backendUrl}/api/auth/google`;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const endpoint = mode === "register" ? "/auth/register" : "/auth/login";
      const payload =
        mode === "register" ? { email, password, name } : { email, password };
      const res = await api.post(endpoint, payload);
      setUser(res.data);
      toast.success(mode === "register" ? "¡Cuenta creada!" : "¡Bienvenido de vuelta!");
      navigate("/dashboard", { replace: true });
    } catch (err) {
      toast.error(formatErr(err.response?.data?.detail) || "Error de conexión");
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setEmail("");
    setPassword("");
    setName("");
  };

  return (
    <div className="min-h-screen relative overflow-hidden bg-neon-grid flex items-center justify-center px-6 py-10">
      <div
        className="absolute inset-0 opacity-50"
        style={{
          backgroundImage:
            "url('https://static.prod-images.emergentagent.com/jobs/2fb2929b-f27e-40ca-8f7f-ae20d075fef7/images/564de222d7b677795f983fbcef941d490c7de5420dd875450c8af67d9e90d00a.png')",
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      />
      <div className="absolute inset-0 bg-black/55" />

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative z-10 w-full max-w-md"
      >
        <div className="mb-8 text-center">
          <motion.div
            initial={{ scale: 0.8 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: "spring" }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass mb-5"
          >
            <Sparkles size={14} className="text-[#39FF14]" />
            <span className="text-xs font-bold tracking-[0.25em] uppercase text-white/80">
              Cobrar sin dramas
            </span>
          </motion.div>

          <h1 className="font-display font-black text-5xl sm:text-6xl leading-[0.95] text-white mb-3">
            La
            <br />
            <span className="neon-text">Dolorosa</span>
          </h1>

          <p className="text-zinc-300 text-sm max-w-xs mx-auto leading-relaxed">
            Divide cuentas del carrete al toque.
          </p>
        </div>

        <AnimatePresence mode="wait">
          {mode === "choice" && (
            <motion.div
              key="choice"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="card-glass space-y-3"
            >
              <button
                data-testid="google-login-btn"
                onClick={handleGoogleLogin}
                className="btn-primary w-full"
              >
                <LogIn size={20} />
                Entrar con Google
              </button>

              <div className="flex items-center gap-3 py-1">
                <div className="flex-1 h-px bg-white/10" />
                <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-[0.2em]">
                  o
                </span>
                <div className="flex-1 h-px bg-white/10" />
              </div>

              <button
                onClick={() => {
                  resetForm();
                  setMode("login");
                }}
                data-testid="show-login-btn"
                className="btn-secondary w-full"
              >
                <Mail size={18} />
                Entrar con email
              </button>

              <button
                onClick={() => {
                  resetForm();
                  setMode("register");
                }}
                data-testid="show-register-btn"
                className="w-full h-12 rounded-2xl text-white text-sm font-bold hover:text-[#39FF14] transition flex items-center justify-center gap-1"
              >
                Crear cuenta nueva
                <ArrowRight size={14} />
              </button>

              <p className="text-xs text-zinc-500 text-center leading-relaxed mt-2">
                Al continuar aceptas que eres el Capitán del grupo.
                <br />
                Con gran poder viene la gran dolorosa.
              </p>
            </motion.div>
          )}

          {(mode === "login" || mode === "register") && (
            <motion.form
              key={mode}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              onSubmit={handleSubmit}
              className="card-glass space-y-3"
            >
              <div className="flex items-center gap-2 mb-1">
                <div
                  className={`w-9 h-9 rounded-xl flex items-center justify-center ${
                    mode === "register" ? "bg-[#BF40FF]/20" : "bg-[#39FF14]/15"
                  }`}
                >
                  {mode === "register" ? (
                    <User size={16} className="text-[#BF40FF]" />
                  ) : (
                    <LogIn size={16} className="text-[#39FF14]" />
                  )}
                </div>
                <div>
                  <div className="font-display font-bold text-white text-base">
                    {mode === "register" ? "Crear cuenta" : "Entrar"}
                  </div>
                  <div className="text-[11px] text-zinc-400">
                    {mode === "register"
                      ? "Se el próximo Capitán de tu grupo."
                      : "Bienvenido de vuelta."}
                  </div>
                </div>
              </div>

              {mode === "register" && (
                <div>
                  <label className="label-small">Nombre</label>
                  <div className="relative">
                    <User
                      size={16}
                      className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500"
                    />
                    <input
                      data-testid="auth-name-input"
                      className="input-field pl-11"
                      placeholder="Tu nombre"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                      autoComplete="name"
                      minLength={2}
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="label-small">Email</label>
                <div className="relative">
                  <Mail
                    size={16}
                    className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500"
                  />
                  <input
                    data-testid="auth-email-input"
                    type="email"
                    className="input-field pl-11"
                    placeholder="tu@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                  />
                </div>
              </div>

              <div>
                <label className="label-small">Contraseña</label>
                <div className="relative">
                  <Lock
                    size={16}
                    className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500"
                  />
                  <input
                    data-testid="auth-password-input"
                    type="password"
                    className="input-field pl-11"
                    placeholder="Mínimo 6 caracteres"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={6}
                    autoComplete={mode === "register" ? "new-password" : "current-password"}
                  />
                </div>
              </div>

              <button
                type="submit"
                data-testid="auth-submit-btn"
                className="btn-primary w-full"
                disabled={loading}
              >
                {loading ? "..." : mode === "register" ? "Crear cuenta" : "Entrar"}
              </button>

              <button
                type="button"
                onClick={() => setMode(mode === "login" ? "register" : "login")}
                data-testid="toggle-auth-mode"
                className="w-full text-xs text-zinc-400 hover:text-[#39FF14] py-1 transition"
              >
                {mode === "login"
                  ? "¿No tienes cuenta? Créala aquí"
                  : "¿Ya tienes cuenta? Entra aquí"}
              </button>

              <button
                type="button"
                onClick={() => {
                  resetForm();
                  setMode("choice");
                }}
                className="w-full text-[10px] text-zinc-500 hover:text-white py-1 transition"
              >
                ← Otras opciones
              </button>
            </motion.form>
          )}
        </AnimatePresence>

        <div className="mt-8 flex items-center justify-center gap-6 text-xs text-zinc-500">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-[#39FF14] pulse-neon" />
            <span>OCR con IA</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-[#BF40FF]" />
            <span>Link WhatsApp</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-white/60" />
            <span>Festejado</span>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
