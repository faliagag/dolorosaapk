import jsPDF from "jspdf";
import html2canvas from "html2canvas";

const money = (n) =>
  new Intl.NumberFormat("es-CL", { maximumFractionDigits: 0 }).format(
    Math.round(n || 0)
  );

export async function exportCarretePDF(carrete, summary, captainName) {
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const W = doc.internal.pageSize.getWidth();
  let y = 48;

  // Header
  doc.setFillColor(5, 5, 5);
  doc.rect(0, 0, W, 120, "F");
  doc.setTextColor(57, 255, 20);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.text("LA DOLOROSA", 48, 48);
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(22);
  doc.text(carrete.name, 48, 78);
  doc.setTextColor(160, 160, 170);
  doc.setFontSize(10);
  doc.setFont("helvetica", "normal");
  doc.text(`Capitán: ${captainName || "—"}`, 48, 98);
  doc.text(
    `Generado: ${new Date().toLocaleString("es-CL")}`,
    W - 48,
    98,
    { align: "right" }
  );

  y = 160;
  // Totals
  doc.setTextColor(0, 0, 0);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.text("Resumen general", 48, y);
  y += 22;
  doc.setFontSize(10);
  doc.setFont("helvetica", "normal");
  doc.text(`Subtotal: $${money(summary.grand_subtotal)}`, 48, y);
  y += 16;
  doc.text(
    `Propina (${summary.tip_percent}%): $${money(summary.grand_tip)}`,
    48,
    y
  );
  y += 16;
  doc.setFont("helvetica", "bold");
  doc.setFontSize(14);
  doc.text(`TOTAL: $${money(summary.grand_total)}`, 48, y);
  y += 30;

  // Per person
  doc.setFontSize(12);
  doc.text("Cuenta por persona", 48, y);
  y += 18;
  doc.setFontSize(10);
  doc.setFont("helvetica", "normal");

  summary.per_person.forEach((p) => {
    if (y > 770) {
      doc.addPage();
      y = 48;
    }
    doc.setFont("helvetica", "bold");
    doc.text(
      `${p.is_birthday ? "🎂 " : ""}${p.participant_name}`,
      48,
      y
    );
    doc.text(`$${money(p.total)}`, W - 48, y, { align: "right" });
    y += 14;
    doc.setFont("helvetica", "normal");
    doc.setTextColor(100, 100, 110);
    p.items.forEach((it) => {
      if (y > 780) {
        doc.addPage();
        y = 48;
      }
      doc.text(`  • ${it.name}`, 56, y);
      doc.text(`$${money(it.amount)}`, W - 48, y, { align: "right" });
      y += 12;
    });
    doc.text(`  Subtotal $${money(p.subtotal)} · Propina $${money(p.tip)}`, 56, y);
    y += 20;
    doc.setTextColor(0, 0, 0);
  });

  doc.save(`dolorosa-${carrete.name.replace(/\s+/g, "-")}.pdf`);
}

// Generate Instagram story image (1080x1920)
export async function exportStoryImage(node) {
  const canvas = await html2canvas(node, {
    backgroundColor: "#050505",
    scale: 2,
    useCORS: true,
  });
  const url = canvas.toDataURL("image/png");
  const link = document.createElement("a");
  link.href = url;
  link.download = "dolorosa-story.png";
  link.click();
}
