/* CareerPilot AI - shared admin menu (added to every admin sub-page) */
(function () {
    const links = [
        ["dashboard.html", "🏠 Dashboard"],
        ["users.html", "👥 Users"],
        ["resume.html", "📄 Resumes"],
        ["coach.html", "🤖 AI Coach"],
        ["skill-gap.html", "🎯 Skill Gap"],
        ["roadmaps.html", "🗺️ Roadmaps"],
        ["job-matching.html", "💼 Job Matching"],
        ["reports.html", "📊 Reports"]
    ];
    const current = location.pathname.split("/").pop() || "dashboard.html";

    const bar = document.createElement("nav");
    bar.style.cssText =
        "position:fixed;top:0;left:0;right:0;z-index:9999;display:flex;gap:6px;" +
        "align-items:center;flex-wrap:wrap;padding:9px 16px;background:#090c18;" +
        "border-bottom:1px solid rgba(255,255,255,.12);font-family:Arial,sans-serif;";

    const brand = document.createElement("strong");
    brand.textContent = "✦ CareerPilot Admin";
    brand.style.cssText = "color:#c4b5fd;margin-right:12px;font-size:14px;";
    bar.appendChild(brand);

    links.forEach(([file, label]) => {
        const a = document.createElement("a");
        a.href = file;
        a.textContent = label;
        const active = file === current;
        a.style.cssText =
            "padding:6px 10px;border-radius:9px;font-size:12.5px;text-decoration:none;white-space:nowrap;" +
            "color:" + (active ? "#fff" : "#a5adc6") + ";" +
            "background:" + (active ? "#7c3aed" : "transparent") + ";";
        bar.appendChild(a);
    });

    document.body.insertBefore(bar, document.body.firstChild);
    const fit = () => { document.body.style.paddingTop = (bar.offsetHeight + 6) + "px"; };
    fit();
    window.addEventListener("resize", fit);
})();
