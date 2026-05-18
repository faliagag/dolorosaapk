import React from "react";
import { Link, useLocation } from "react-router-dom";
import { Home, User, LogOut } from "lucide-react";
import { useAuth } from "@/lib/auth";

export default function BottomNav() {
  const location = useLocation();
  const { logout } = useAuth();
  const active = location.pathname;

  const Item = ({ to, icon: Icon, label, testId }) => {
    const isActive = active === to || active.startsWith(to + "/");
    return (
      <Link
        to={to}
        data-testid={testId}
        className={`flex-1 flex flex-col items-center justify-center gap-1 py-2 transition-all ${
          isActive ? "text-[#39FF14]" : "text-zinc-500 hover:text-white"
        }`}
      >
        <Icon size={22} strokeWidth={isActive ? 2.5 : 2} />
        <span className="text-[10px] font-bold uppercase tracking-wider">{label}</span>
      </Link>
    );
  };

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 flex items-center max-w-md mx-auto border-t border-white/10"
      style={{ background: "rgba(0,0,0,0.75)", backdropFilter: "blur(24px)" }}
    >
      <Item to="/dashboard" icon={Home} label="Carretes" testId="nav-dashboard" />
      <Item to="/profile" icon={User} label="Perfil" testId="nav-profile" />
      <button
        onClick={logout}
        data-testid="nav-logout"
        className="flex-1 flex flex-col items-center justify-center gap-1 py-2 text-zinc-500 hover:text-[#FF3366] transition-all"
      >
        <LogOut size={22} />
        <span className="text-[10px] font-bold uppercase tracking-wider">Salir</span>
      </button>
    </nav>
  );
}
