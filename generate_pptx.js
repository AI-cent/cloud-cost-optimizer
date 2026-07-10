// generate_pptx.js — Cloud Cost Optimizer Presentation (9 slides)
// Uses PptxGenJS. Run with: node generate_pptx.js
"use strict";

const PptxGenJS = require("/sessions/festive-relaxed-fermi/mnt/outputs/lib/node_modules/pptxgenjs");
const path = require("path");

const OUT = "/sessions/festive-relaxed-fermi/mnt/cloud-cost-optimizer/PRESENTATION.pptx";

// ── Palette ──────────────────────────────────────────────────────────────────
const C = {
  dark:   "232F3E",
  orange: "FF9900",
  green:  "1A9C3E",
  red:    "D13212",
  yellow: "F0A30A",
  bg:     "F2F3F3",
  white:  "FFFFFF",
  grey:   "888888",
  ltgrey: "CCCCCC",
  dkgrey: "555555",
};

const W = 10, H = 5.625; // LAYOUT_16x9 inches

function makeShadow() {
  return { type: "outer", color: "000000", blur: 5, offset: 2, angle: 45, opacity: 0.13 };
}

// ── Per-slide chrome: orange bottom bar + slide number + watermark ───────────
function addChrome(slide, slideNum) {
  // Orange bottom bar
  slide.addShape("rect", {
    x: 0, y: H - 0.12, w: W, h: 0.12,
    fill: { color: C.orange }, line: { color: C.orange, width: 0 },
  });
  // Slide number
  slide.addText(String(slideNum), {
    x: W - 0.4, y: H - 0.28, w: 0.3, h: 0.2,
    fontSize: 9, color: C.grey, align: "right", margin: 0,
  });
  // Watermark
  slide.addText("Cloud Cost Optimizer", {
    x: W - 2.2, y: 0.06, w: 2.1, h: 0.22,
    fontSize: 8, color: C.ltgrey, align: "right", margin: 0,
  });
}

// ── Section heading strip (for content slides) ────────────────────────────────
function addTitle(slide, text) {
  slide.addText(text, {
    x: 0.4, y: 0.22, w: 9.2, h: 0.55,
    fontSize: 26, fontFace: "Calibri", bold: true,
    color: C.dark, align: "left", margin: 0,
  });
  // subtle divider
  slide.addShape("rect", {
    x: 0.4, y: 0.82, w: 9.2, h: 0.03,
    fill: { color: C.ltgrey }, line: { color: C.ltgrey, width: 0 },
  });
}

// ─────────────────────────────────────────────────────────────────────────────
async function build() {
  const pres = new PptxGenJS();
  pres.layout = "LAYOUT_16x9";
  pres.title  = "Cloud Cost Optimizer & Remediation Engine";
  pres.author = "Lead Architect Mode";

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 1 — Title
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.dark };

    // Large title
    s.addText("Cloud Cost Optimizer\n& Remediation Engine", {
      x: 0.6, y: 0.9, w: 8.8, h: 1.8,
      fontSize: 38, fontFace: "Calibri", bold: true,
      color: C.white, align: "center", valign: "middle",
    });

    // Orange subtitle band
    s.addShape("rect", {
      x: 1.5, y: 2.85, w: 7, h: 0.52,
      fill: { color: C.orange }, line: { color: C.orange, width: 0 },
    });
    s.addText("AWS FinOps  |  Agentic AI Architect", {
      x: 1.5, y: 2.85, w: 7, h: 0.52,
      fontSize: 16, fontFace: "Calibri", bold: true,
      color: C.dark, align: "center", valign: "middle", margin: 0,
    });


    addChrome(s, 1);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 2 — Problem Statement
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "The Hidden Cost of Cloud Waste");

    const bullets = [
      "Companies waste 30–35% of cloud budget on orphaned resources",
      "Unattached disks, idle VMs, forgotten IPs accumulate silently",
      "Manual identification is slow, error-prone, and costly",
      "No single view to detect, quantify, and act on waste",
    ];

    s.addText(
      bullets.map((t, i) => ({
        text: t,
        options: { bullet: true, breakLine: i < bullets.length - 1, paraSpaceAfter: 10 },
      })),
      {
        x: 0.6, y: 1.1, w: 5.8, h: 3.5,
        fontSize: 16, fontFace: "Calibri", color: C.dark, valign: "top",
      }
    );

    // Right-side stat card
    s.addShape("rect", {
      x: 7.0, y: 1.1, w: 2.6, h: 3.5,
      fill: { color: C.dark },
      shadow: makeShadow(),
    });
    s.addText([
      { text: "30–35%", options: { breakLine: true, fontSize: 36, bold: true, color: C.orange } },
      { text: "of cloud budget\nwasted on orphans", options: { breakLine: true, fontSize: 13, color: C.white } },
      { text: "\n$20K–$50K", options: { breakLine: true, fontSize: 24, bold: true, color: C.yellow } },
      { text: "per year\npreventable waste", options: { fontSize: 13, color: C.white } },
    ], {
      x: 7.0, y: 1.1, w: 2.6, h: 3.5,
      align: "center", valign: "middle",
    });

    addChrome(s, 2);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 3 — Solution Architecture
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Cloud Cost Optimizer & Remediation Engine");

    // Flow diagram boxes
    const flow = [
      { label: "CSV Upload",        x: 0.3 },
      { label: "Parse &\nValidate", x: 2.2 },
      { label: "Detect\n(5 Rules)", x: 4.1 },
      { label: "Dashboard\n+ Charts",x: 6.0 },
    ];
    const BY = 1.05, BH = 0.85, BW = 1.7;
    flow.forEach((b, i) => {
      s.addShape("rect", {
        x: b.x, y: BY, w: BW, h: BH,
        fill: { color: C.dark }, line: { color: C.orange, width: 1.5 },
        shadow: makeShadow(),
      });
      s.addText(b.label, {
        x: b.x, y: BY, w: BW, h: BH,
        fontSize: 11, fontFace: "Calibri", bold: true, color: C.white,
        align: "center", valign: "middle",
      });
      if (i < flow.length - 1) {
        s.addShape("line", {
          x: b.x + BW, y: BY + BH / 2, w: 0.5, h: 0,
          line: { color: C.orange, width: 2 },
        });
      }
    });

    // Split into two paths from Dashboard
    const PX = 6.0 + BW; // x after Dashboard box = 7.7
    // Arrow down-left to Admin path
    s.addShape("line", { x: PX, y: BY + BH / 2, w: 0.25, h: 0, line: { color: C.orange, width: 2 } });

    // Admin path box
    s.addShape("rect", {
      x: 7.95, y: 0.95, w: 1.9, h: 0.75,
      fill: { color: C.orange }, shadow: makeShadow(),
    });
    s.addText("Admin: Auto-Remediate\nvia AWS API", {
      x: 7.95, y: 0.95, w: 1.9, h: 0.75,
      fontSize: 10, fontFace: "Calibri", bold: true, color: C.dark,
      align: "center", valign: "middle",
    });

    // Viewer path box
    s.addShape("rect", {
      x: 7.95, y: 1.85, w: 1.9, h: 0.75,
      fill: { color: C.dkgrey }, shadow: makeShadow(),
    });
    s.addText("Viewer: Copy CLI\nRun in Terminal", {
      x: 7.95, y: 1.85, w: 1.9, h: 0.75,
      fontSize: 10, fontFace: "Calibri", bold: true, color: C.white,
      align: "center", valign: "middle",
    });

    // Split arrow — all lines orange to match main flow
    s.addShape("line", {
      x: PX + 0.25, y: BY + BH / 2, w: 0, h: -0.4,
      line: { color: C.orange, width: 1.5 },
    });
    s.addShape("line", {
      x: PX + 0.25, y: BY + BH / 2, w: 0, h: 0.58,
      line: { color: C.orange, width: 1.5 },
    });
    s.addShape("line", {
      x: PX + 0.25, y: BY + 0.1, w: 0.55, h: 0,
      line: { color: C.orange, width: 1.5 },
    });
    s.addShape("line", {
      x: PX + 0.25, y: BY + BH - 0.18, w: 0.55, h: 0,
      line: { color: C.orange, width: 1.5 },
    });

    // Stack label
    s.addShape("rect", {
      x: 0.3, y: 3.0, w: 9.4, h: 0.52,
      fill: { color: "EDF2F4" }, line: { color: C.ltgrey, width: 1 },
    });
    s.addText("Stack:  FastAPI  +  SQLite + SQLAlchemy  +  JWT Auth  +  AWS API  +  Chart.js 4.4", {
      x: 0.3, y: 3.0, w: 9.4, h: 0.52,
      fontSize: 11, fontFace: "Courier New", color: C.dark,
      align: "center", valign: "middle",
    });

    // Detection rules table — fits within slide (leaves room for footer)
    const rows = [
      [{ text: "Rule", options: { bold: true, color: C.white, fill: { color: C.dark } } },
       { text: "Resource Type", options: { bold: true, color: C.white, fill: { color: C.dark } } },
       { text: "Condition", options: { bold: true, color: C.white, fill: { color: C.dark } } },
       { text: "Severity", options: { bold: true, color: C.white, fill: { color: C.dark } } }],
      ["unattached_ebs",  "EBS Volume",    "Status = available",         "High"],
      ["idle_ec2",        "EC2 Instance",  "No activity > 30 days",      "Critical"],
      ["orphaned_eip",    "Elastic IP",    "Status = unassociated",       "Medium"],
      ["idle_alb",        "Load Balancer", "Status = idle",               "High"],
      ["old_snapshot",    "Snapshot",      "Created > 90 days ago",       "Low"],
    ];
    s.addTable(rows, {
      x: 0.3, y: 3.62, w: 9.4, h: 1.75,
      colW: [2.0, 2.0, 3.4, 2.0],
      fontSize: 10, fontFace: "Calibri", color: C.dark,
      border: { pt: 0.5, color: C.ltgrey },
      fill: { color: C.white },
    });

    addChrome(s, 3);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 4 — Dashboard Mockup (Admin View)
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Admin Dashboard — Full Control");

    // Sidebar
    const SBW = 1.8;
    s.addShape("rect", {
      x: 0, y: 0.9, w: SBW, h: H - 1.0,
      fill: { color: C.dark },
    });
    s.addText("☁ Cost Optimizer", {
      x: 0.05, y: 0.95, w: SBW - 0.1, h: 0.42,
      fontSize: 10, fontFace: "Calibri", bold: true, color: C.orange,
      align: "center", valign: "middle",
    });
    ["Dashboard", "Users", "Settings"].forEach((nav, i) => {
      s.addText(nav, {
        x: 0.12, y: 1.5 + i * 0.38, w: SBW - 0.2, h: 0.32,
        fontSize: 10, fontFace: "Calibri", color: i === 0 ? C.orange : C.ltgrey,
        align: "left", valign: "middle",
      });
    });
    // Upload CSV drag-drop zone
    s.addShape("rect", {
      x: 0.12, y: 2.68, w: SBW - 0.22, h: 0.72,
      fill: { color: "1A2A38" }, line: { color: C.orange, width: 1, dashType: "dash" },
    });
    s.addText("⬆ Upload CSV\nDrag & Drop", {
      x: 0.12, y: 2.68, w: SBW - 0.22, h: 0.72,
      fontSize: 8, color: C.ltgrey, align: "center", valign: "middle",
    });
    // Admin badge
    s.addShape("rect", {
      x: 0.18, y: H - 0.65, w: 0.55, h: 0.22,
      fill: { color: C.green },
    });
    s.addText("Admin", {
      x: 0.18, y: H - 0.65, w: 0.55, h: 0.22,
      fontSize: 7, color: C.white, bold: true, align: "center", valign: "middle", margin: 0,
    });
    s.addText("admin", {
      x: 0.78, y: H - 0.65, w: 0.9, h: 0.22,
      fontSize: 8, color: C.ltgrey, align: "left", valign: "middle", margin: 0,
    });

    // 4 Summary cards
    const CX = SBW + 0.15;
    const cards = [
      { label: "Total Waste",   val: "$1,844.50", sub: "/ month" },
      { label: "Orphaned",      val: "10",        sub: "resources" },
      { label: "Pending",       val: "10",        sub: "remediations" },
      { label: "Top Waster",    val: "EC2",       sub: "Instance" },
    ];
    const CW = (W - CX - 0.2) / 4 - 0.1;
    cards.forEach((c, i) => {
      const cx = CX + i * (CW + 0.1);
      s.addShape("rect", {
        x: cx, y: 0.95, w: CW, h: 0.85,
        fill: { color: C.white },
        line: { color: C.orange, width: 1.5 },
        shadow: makeShadow(),
      });
      s.addText([
        { text: c.label + "\n", options: { fontSize: 8, color: C.grey, breakLine: true } },
        { text: c.val,          options: { fontSize: 15, bold: true, color: C.dark, breakLine: true } },
        { text: c.sub,          options: { fontSize: 8, color: C.grey } },
      ], { x: cx, y: 0.95, w: CW, h: 0.85, align: "center", valign: "middle" });
    });

    // Bar chart (native)
    const barCX = CX;
    s.addChart(pres.ChartType.bar, [{
      name: "Monthly Waste ($)",
      labels: ["EC2", "EBS", "ALB", "EIP", "Snapshot"],
      values: [780, 420, 380, 180, 84],
    }], {
      x: barCX, y: 1.9, w: 3.8, h: 1.55,
      barDir: "col",
      chartColors: [C.orange, C.red, C.yellow, C.green, "6C8EBF"],
      chartArea: { fill: { color: C.white }, roundedCorners: false },
      catAxisLabelColor: C.dkgrey,
      valAxisLabelColor: C.dkgrey,
      valGridLine: { color: "E2E8F0", size: 0.5 },
      catGridLine: { style: "none" },
      showValue: true,
      dataLabelColor: C.dark,
      showLegend: false,
      showTitle: true,
      title: "Waste by Service ($)",
      titleFontSize: 10,
      titleColor: C.dark,
    });

    // Pie chart (native)
    s.addChart(pres.ChartType.doughnut, [{
      name: "By Severity",
      labels: ["Critical", "High", "Medium", "Low"],
      values: [2, 4, 2, 2],
    }], {
      x: barCX + 4.0, y: 1.9, w: 2.5, h: 1.55,
      chartColors: [C.red, C.orange, C.yellow, C.green],
      chartArea: { fill: { color: C.white } },
      showLegend: true,
      legendPos: "r",
      legendFontSize: 8,
      showTitle: true,
      title: "Findings by Severity",
      titleFontSize: 10,
      titleColor: C.dark,
      dataLabelColor: C.white,
      showLabel: false,
      showPercent: false,
    });

    // Findings table (mini) — Admin sees Remediate + Copy CLI
    const rows = [
      [{ text: "Resource ID", options: { bold: true, color: C.white, fill: { color: C.dark } } },
       { text: "Type", options: { bold: true, color: C.white, fill: { color: C.dark } } },
       { text: "Severity", options: { bold: true, color: C.white, fill: { color: C.dark } } },
       { text: "Waste/mo", options: { bold: true, color: C.white, fill: { color: C.dark } } },
       { text: "Remediate", options: { bold: true, color: C.white, fill: { color: C.dark } } },
       { text: "Copy CLI", options: { bold: true, color: C.white, fill: { color: C.dark } } }],
      ["i-0a1b2c3d4e5f6789a", "EC2 Instance",  "Critical", "$780.00",
       { text: "Remediate", options: { bold: true, color: C.white, fill: { color: C.orange } } },
       { text: "Copy CLI",  options: { bold: true, color: C.white, fill: { color: C.dark } } }],
      ["vol-0a1b2c3d4e5f6789", "EBS Volume",    "High",     "$210.00",
       { text: "Remediate", options: { bold: true, color: C.white, fill: { color: C.orange } } },
       { text: "Copy CLI",  options: { bold: true, color: C.white, fill: { color: C.dark } } }],
      ["arn:aws:...:legacy-auth-alb", "Load Balancer", "High", "$190.00",
       { text: "Remediate", options: { bold: true, color: C.white, fill: { color: C.orange } } },
       { text: "Copy CLI",  options: { bold: true, color: C.white, fill: { color: C.dark } } }],
    ];
    s.addTable(rows, {
      x: CX, y: 3.55, w: W - CX - 0.15, h: 1.4,
      colW: [1.9, 1.2, 0.85, 0.75, 1.0, 0.9],
      fontSize: 8, fontFace: "Calibri", color: C.dark,
      border: { pt: 0.5, color: C.ltgrey },
      fill: { color: C.white },
    });

    // Caption
    s.addText("Admin: Upload CSV · Ingest · Remediate via AWS API · Copy CLI command", {
      x: CX, y: H - 0.32, w: W - CX - 0.2, h: 0.2,
      fontSize: 7.5, fontFace: "Calibri", color: C.grey, italic: true,
    });

    addChrome(s, 4);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 5 — Dashboard Mockup (Viewer View)
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Viewer Dashboard — Read Only");

    const SBW = 1.8;
    s.addShape("rect", {
      x: 0, y: 0.9, w: SBW, h: H - 1.0,
      fill: { color: C.dark },
    });
    s.addText("☁ Cost Optimizer", {
      x: 0.05, y: 0.95, w: SBW - 0.1, h: 0.42,
      fontSize: 10, fontFace: "Calibri", bold: true, color: C.orange,
      align: "center", valign: "middle",
    });
    // Viewer sees only Dashboard nav (no Users tab)
    s.addText("Dashboard", {
      x: 0.12, y: 1.5, w: SBW - 0.2, h: 0.32,
      fontSize: 10, fontFace: "Calibri", color: C.orange,
      align: "left", valign: "middle",
    });
    // Upload CSV drag-drop zone
    s.addShape("rect", {
      x: 0.12, y: 1.9, w: SBW - 0.22, h: 0.72,
      fill: { color: "1A2A38" }, line: { color: C.ltgrey, width: 1, dashType: "dash" },
    });
    s.addText("⬆ Upload CSV\nDrag & Drop", {
      x: 0.12, y: 1.9, w: SBW - 0.22, h: 0.72,
      fontSize: 8, color: C.ltgrey, align: "center", valign: "middle",
    });

    // Viewer badge (grey)
    s.addShape("rect", {
      x: 0.18, y: H - 0.65, w: 0.55, h: 0.22,
      fill: { color: C.dkgrey },
    });
    s.addText("Viewer", {
      x: 0.18, y: H - 0.65, w: 0.55, h: 0.22,
      fontSize: 7, color: C.white, bold: true, align: "center", valign: "middle", margin: 0,
    });
    s.addText("viewer1", {
      x: 0.78, y: H - 0.65, w: 0.9, h: 0.22,
      fontSize: 8, color: C.ltgrey, align: "left", valign: "middle", margin: 0,
    });

    const CX = SBW + 0.15;
    const CW = (W - CX - 0.2) / 4 - 0.1;
    const cards = [
      { label: "Total Waste",   val: "$1,844.50", sub: "/ month" },
      { label: "Orphaned",      val: "10",        sub: "resources" },
      { label: "Pending",       val: "10",        sub: "remediations" },
      { label: "Top Waster",    val: "EC2",       sub: "Instance" },
    ];
    cards.forEach((c, i) => {
      const cx = CX + i * (CW + 0.1);
      s.addShape("rect", {
        x: cx, y: 0.95, w: CW, h: 0.85,
        fill: { color: C.white },
        line: { color: C.ltgrey, width: 1 },
        shadow: makeShadow(),
      });
      s.addText([
        { text: c.label + "\n", options: { fontSize: 8, color: C.grey, breakLine: true } },
        { text: c.val,          options: { fontSize: 15, bold: true, color: C.dark, breakLine: true } },
        { text: c.sub,          options: { fontSize: 8, color: C.grey } },
      ], { x: cx, y: 0.95, w: CW, h: 0.85, align: "center", valign: "middle" });
    });

    // Grey info banner
    s.addShape("rect", {
      x: CX, y: 1.88, w: W - CX - 0.15, h: 0.32,
      fill: { color: "E8E8E8" }, line: { color: C.ltgrey, width: 1 },
    });
    s.addText("ℹ  Viewer Access — Contact Admin to perform remediation", {
      x: CX, y: 1.88, w: W - CX - 0.15, h: 0.32,
      fontSize: 9, color: C.dkgrey, align: "center", valign: "middle",
    });

    // Findings table with Copy CLI
    const rows = [
      [{ text: "Resource ID", options: { bold: true, color: C.white, fill: { color: C.dark } } },
       { text: "Type", options: { bold: true, color: C.white, fill: { color: C.dark } } },
       { text: "Severity", options: { bold: true, color: C.white, fill: { color: C.dark } } },
       { text: "Waste/mo", options: { bold: true, color: C.white, fill: { color: C.dark } } },
       { text: "Action", options: { bold: true, color: C.white, fill: { color: C.dark } } }],
      ["i-0a1b2c3d4e5f6789a", "EC2 Instance",  "Critical", "$780.00",
       { text: "Copy CLI", options: { bold: true, color: C.white, fill: { color: C.dark } } }],
      ["vol-0a1b2c3d4e5f6789", "EBS Volume",    "High",     "$210.00",
       { text: "Copy CLI", options: { bold: true, color: C.white, fill: { color: C.dark } } }],
      ["arn:aws:...:legacy-auth-alb", "Load Balancer", "High", "$190.00",
       { text: "Copy CLI", options: { bold: true, color: C.white, fill: { color: C.dark } } }],
    ];
    s.addTable(rows, {
      x: CX, y: 2.28, w: W - CX - 0.15, h: 2.65,
      colW: [2.4, 1.4, 1.0, 0.85, 1.0],
      fontSize: 8, fontFace: "Calibri", color: C.dark,
      border: { pt: 0.5, color: C.ltgrey },
      fill: { color: C.white },
    });

    s.addText("Viewer: Upload CSV · Ingest · Copy CLI command — no remediation access", {
      x: CX, y: H - 0.32, w: W - CX - 0.2, h: 0.2,
      fontSize: 7.5, fontFace: "Calibri", color: C.grey, italic: true,
    });

    addChrome(s, 5);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 6 — Remediation Flow (two paths)
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Two Paths to Remediation");

    const steps_admin = [
      "Click Remediate",
      "User Confirmation Popup",
      "Call AWS API",
      "Execute Remediation in AWS",
      "Resource Decommissioned",
      "Email Alert Sent",
      "Row turns green ✓",
    ];
    const steps_viewer = [
      "Click Copy CLI",
      "Paste in Terminal",
      "Run AWS CLI Command",
      "Resource Decommissioned",
      "Report back to Admin",
    ];

    const BW = 3.4, BH = 0.38, GAP = 0.05;

    // Left header
    s.addShape("rect", {
      x: 0.4, y: 0.92, w: BW, h: 0.42,
      fill: { color: C.orange },
    });
    s.addText("Admin User", {
      x: 0.4, y: 0.92, w: BW, h: 0.42,
      fontSize: 13, bold: true, color: C.dark, align: "center", valign: "middle",
    });

    steps_admin.forEach((t, i) => {
      const sy = 1.42 + i * (BH + GAP);
      s.addShape("rect", {
        x: 0.4, y: sy, w: BW, h: BH,
        fill: { color: i % 2 === 0 ? C.white : "F0F4F8" },
        line: { color: C.ltgrey, width: 0.75 },
        shadow: makeShadow(),
      });
      s.addText(t, {
        x: 0.4, y: sy, w: BW, h: BH,
        fontSize: 10, color: C.dark, align: "center", valign: "middle",
      });
      if (i < steps_admin.length - 1) {
        s.addShape("line", {
          x: 0.4 + BW / 2 - 0.01, y: sy + BH, w: 0, h: GAP + 0.02,
          line: { color: C.orange, width: 1.5 },
        });
      }
    });
    s.addText("One-click — no terminal needed", {
      x: 0.4, y: 1.42 + steps_admin.length * (BH + GAP) + 0.04,
      w: BW, h: 0.24,
      fontSize: 9, italic: true, color: C.green, align: "center",
    });

    // Divider
    s.addShape("line", {
      x: W / 2, y: 0.92, w: 0, h: H - 1.1,
      line: { color: C.dkgrey, width: 1.5, dashType: "dash" },
    });

    // Right header
    const RX = W / 2 + 0.2;
    s.addShape("rect", {
      x: RX, y: 0.92, w: BW, h: 0.42,
      fill: { color: C.dkgrey },
    });
    s.addText("Viewer User", {
      x: RX, y: 0.92, w: BW, h: 0.42,
      fontSize: 13, bold: true, color: C.white, align: "center", valign: "middle",
    });

    steps_viewer.forEach((t, i) => {
      const sy = 1.42 + i * (BH + GAP);
      s.addShape("rect", {
        x: RX, y: sy, w: BW, h: BH,
        fill: { color: i % 2 === 0 ? C.white : "F0F4F8" },
        line: { color: C.ltgrey, width: 0.75 },
        shadow: makeShadow(),
      });
      s.addText(t, {
        x: RX, y: sy, w: BW, h: BH,
        fontSize: 10, color: C.dark, align: "center", valign: "middle",
      });
      if (i < steps_viewer.length - 1) {
        s.addShape("line", {
          x: RX + BW / 2, y: sy + BH, w: 0, h: GAP + 0.02,
          line: { color: C.dkgrey, width: 1.5 },
        });
      }
    });
    s.addText("Full control — viewer approves each action", {
      x: RX, y: 1.42 + steps_viewer.length * (BH + GAP) + 0.04,
      w: BW, h: 0.24,
      fontSize: 9, italic: true, color: C.dkgrey, align: "center",
    });

    addChrome(s, 6);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 7 — Email Notification Mockup
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Automated Email Alert on Remediation");

    const EX = 1.0, EW = 8.0;

    // Email header
    s.addShape("rect", { x: EX, y: 0.95, w: EW, h: 0.72, fill: { color: C.dark } });
    s.addText([
      { text: "From: ", options: { bold: true, color: C.orange } },
      { text: "cloudoptimizer@company.com     ", options: { color: C.white } },
      { text: "To: ", options: { bold: true, color: C.orange } },
      { text: "admin@company.com", options: { color: C.white, breakLine: true } },
      { text: "Subject: ", options: { bold: true, color: C.orange } },
      { text: "☁ Cloud Cost Optimizer — Resource Remediated", options: { color: C.white } },
    ], { x: EX + 0.18, y: 0.95, w: EW - 0.3, h: 0.72, fontSize: 9.5, valign: "middle" });

    // Email body
    s.addShape("rect", {
      x: EX, y: 1.68, w: EW, h: 3.02,
      fill: { color: C.white }, line: { color: C.ltgrey, width: 1 },
    });

    const bodyLines = [
      { text: "Hello Admin,\n\n", options: { fontSize: 10, color: C.dark, breakLine: false } },
      { text: "A resource has been successfully remediated.\n\n", options: { fontSize: 10, color: C.dark, breakLine: false } },
      { text: "Resource Details:\n", options: { fontSize: 10, bold: true, color: C.dark, breakLine: false } },
      { text: "━".repeat(38) + "\n", options: { fontSize: 9, color: C.ltgrey, fontFace: "Courier New", breakLine: false } },
      { text: "Resource ID:     i-0a1b2c3d4e5f6789\n", options: { fontSize: 9, color: C.dkgrey, fontFace: "Courier New", breakLine: false } },
      { text: "Resource Name:   ec2-analytics-worker-old\n", options: { fontSize: 9, color: C.dkgrey, fontFace: "Courier New", breakLine: false } },
      { text: "Resource Type:   EC2 Instance\n", options: { fontSize: 9, color: C.dkgrey, fontFace: "Courier New", breakLine: false } },
      { text: "Region:          us-east-1\n", options: { fontSize: 9, color: C.dkgrey, fontFace: "Courier New", breakLine: false } },
      { text: "Action Taken:    Instance Stopped\n", options: { fontSize: 9, color: C.dkgrey, fontFace: "Courier New", breakLine: false } },
      { text: "Monthly Savings: $658.00 / month\n", options: { fontSize: 9, bold: true, color: C.green, fontFace: "Courier New", breakLine: false } },
      { text: "━".repeat(38) + "\n", options: { fontSize: 9, color: C.ltgrey, fontFace: "Courier New", breakLine: false } },
      { text: "Remediated By:   admin (Admin Role)\n", options: { fontSize: 9, color: C.dkgrey, fontFace: "Courier New", breakLine: false } },
      { text: "Remediated At:   2025-07-09 14:32:07 UTC\n\n", options: { fontSize: 9, color: C.dkgrey, fontFace: "Courier New", breakLine: false } },
      { text: "This is an automated notification from Cloud Cost Optimizer.", options: { fontSize: 9, italic: true, color: C.grey } },
    ];
    s.addText(bodyLines, {
      x: EX + 0.25, y: 1.72, w: EW - 0.5, h: 2.9,
      valign: "top",
    });

    // Footer
    s.addShape("rect", { x: EX, y: 4.70, w: EW, h: 0.32, fill: { color: C.orange } });
    s.addText("Cloud Cost Optimizer  |  AWS FinOps  |  Powered by FastAPI + AWS API", {
      x: EX, y: 4.70, w: EW, h: 0.32,
      fontSize: 8.5, bold: true, color: C.dark, align: "center", valign: "middle",
    });

    addChrome(s, 7);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 8 — Technical Highlights
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTitle(s, "Production-Ready Engineering Practices");

    const left = [
      "JWT auth + bcrypt password hashing",
      "Role-based access: Admin vs Viewer",
      "Admin: one-click AWS API remediation",
      "Viewer: CLI command copy only",
      "Email alerts via SMTP notifications",
      "CSV drag-drop upload + auto refresh",
      "AWS color theme throughout",
    ];
    const right = [
      "Responsive layout — zero scroll",
      "Exception handling across all modules",
      "Input validation + sanitization",
      "Security: no hardcoded secrets",
      "Rate limiting on login (5/min/IP)",
      "Structured logging to Database & app.log",
      "AWS API ready for live remediation",
    ];

    const CARD_H = H - 1.22; // cards fill slide height to footer
    // Left card
    s.addShape("rect", {
      x: 0.4, y: 0.97, w: 4.4, h: CARD_H,
      fill: { color: C.white }, shadow: makeShadow(),
    });
    s.addShape("rect", {
      x: 0.4, y: 0.97, w: 4.4, h: 0.42,
      fill: { color: C.dark },
    });
    s.addText("Security & Access", {
      x: 0.4, y: 0.97, w: 4.4, h: 0.42,
      fontSize: 12, bold: true, color: C.orange, align: "center", valign: "middle",
    });
    s.addText(
      left.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < left.length - 1, paraSpaceAfter: 8 } })),
      { x: 0.55, y: 1.44, w: 4.1, h: CARD_H - 0.5, fontSize: 12, color: C.dark, valign: "top" }
    );

    // Right card
    s.addShape("rect", {
      x: 5.2, y: 0.97, w: 4.4, h: CARD_H,
      fill: { color: C.white }, shadow: makeShadow(),
    });
    s.addShape("rect", {
      x: 5.2, y: 0.97, w: 4.4, h: 0.42,
      fill: { color: C.dark },
    });
    s.addText("Reliability & Ops", {
      x: 5.2, y: 0.97, w: 4.4, h: 0.42,
      fontSize: 12, bold: true, color: C.orange, align: "center", valign: "middle",
    });
    s.addText(
      right.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < right.length - 1, paraSpaceAfter: 8 } })),
      { x: 5.35, y: 1.44, w: 4.1, h: CARD_H - 0.5, fontSize: 12, color: C.dark, valign: "top" }
    );

    addChrome(s, 8);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SLIDE 9 — What's Next
  // ══════════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.background = { color: C.dark };

    // Title on dark bg
    s.addText("From MVP to Production", {
      x: 0.5, y: 0.2, w: 9.0, h: 0.6,
      fontSize: 26, fontFace: "Calibri", bold: true,
      color: C.white, align: "left", margin: 0,
    });
    // Subtle divider
    s.addShape("rect", {
      x: 0.5, y: 0.82, w: 9.0, h: 0.03,
      fill: { color: C.orange },
    });

    const items = [
      "AWS SSO replacing local JWT — IAM groups map to Admin / Viewer roles",
      "Real-time Cost Explorer API replacing manual CSV upload",
      "Live AWS API with real credentials in production (DEMO_MODE=false)",
      "AWS Organizations multi-account support — single dashboard",
      "Slack + Teams webhook alerts for Critical findings",
      "Docker + Kubernetes deployment with Terraform module",
      "Scheduled automated daily / weekly scans via EventBridge",
      "Cost forecasting with 30 / 60 / 90-day trend analysis",
      "Multi-cloud: add Azure Cost Management API as second source",
    ];

    // Two-column layout
    const mid = Math.ceil(items.length / 2);
    const leftItems  = items.slice(0, mid);
    const rightItems = items.slice(mid);

    s.addText(
      leftItems.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < leftItems.length - 1, paraSpaceAfter: 7 } })),
      { x: 0.5, y: 0.95, w: 4.5, h: 4.4, fontSize: 11, color: C.white, valign: "top" }
    );
    s.addText(
      rightItems.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < rightItems.length - 1, paraSpaceAfter: 7 } })),
      { x: 5.2, y: 0.95, w: 4.5, h: 4.4, fontSize: 11, color: C.white, valign: "top" }
    );

    // Bottom tagline
    s.addText("Built in Lead Architect Mode — architecture by human, code by AI, 0 manual edits  |  ~4h 10m  |  30+ prompts", {
      x: 0.5, y: H - 0.35, w: 9.0, h: 0.22,
      fontSize: 8, color: C.grey, italic: true, align: "center",
    });

    addChrome(s, 9);
  }

  // ── Write file ─────────────────────────────────────────────────────────────
  await pres.writeFile({ fileName: OUT });
  console.log("PRESENTATION.pptx created — 9 slides");
}

build().catch(err => { console.error(err); process.exit(1); });
