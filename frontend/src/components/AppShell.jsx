import React from "react";

export default function AppShell({ children, title, subtitle, right }) {
  return (
    <div className="min-h-screen bg-neon-grid">
      <div className="max-w-md mx-auto px-6 pt-8 pb-28 relative">
        {(title || right) && (
          <header className="flex items-start justify-between mb-8">
            <div>
              {subtitle && (
                <p className="label-small text-[#39FF14]">{subtitle}</p>
              )}
              {title && (
                <h1 className="font-display font-black text-3xl text-white leading-tight">
                  {title}
                </h1>
              )}
            </div>
            {right}
          </header>
        )}
        {children}
      </div>
    </div>
  );
}
