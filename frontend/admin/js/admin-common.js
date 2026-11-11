/* CareerPilot AI - shared helpers for admin pages (simple version) */
const CP = (() => {
    const API = "";   // <-- change to your deployed backend URL (only here)
    const key = localStorage.getItem("careerpilot_admin_key") || "";
    if (!key) window.location.href = "login.html";

    const esc = v => String(v ?? "").replace(/[&<>"']/g, c =>
        ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
    const day = v => String(v ?? "").slice(0, 10);
    const short = (v, n = 70) => { v = String(v ?? "").replace(/\s+/g, " "); return v.length > n ? v.slice(0, n) + "…" : v; };
    const parseList = v => { try { const x = typeof v === "string" ? JSON.parse(v) : v; return Array.isArray(x) ? x : []; } catch { return []; } };
    const skillName = s => (s && typeof s === "object") ? (s.name || s.skill_name || "") : String(s || "");
    const names = v => parseList(v).map(skillName).filter(Boolean);

    async function call(method, path, body) {
        const res = await fetch(API + path, {
            method,
            headers: { "Content-Type": "application/json", "x-admin-key": key },
            body: body ? JSON.stringify(body) : undefined
        });
        if (res.status === 403) {
            localStorage.removeItem("careerpilot_admin_key");
            window.location.href = "login.html";
            throw new Error("Please sign in again.");
        }
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Server error (" + res.status + ")");
        return data;
    }
    const get = path => call("GET", path);
    const del = path => call("DELETE", path);
    const post = (path, body) => call("POST", path, body);

    function say(msg, type) {
        const el = document.getElementById("status");
        if (!el) return;
        el.className = "status show " + (type || "info");
        el.textContent = msg;
        if (type === "ok") setTimeout(() => { el.className = "status"; }, 3500);
    }

    /* stats: [["Label", value], ...] -> cards */
    function stats(list) {
        document.getElementById("stats").innerHTML = list.map(([l, v]) =>
            '<div class="stat"><div class="stat-label">' + esc(l) + '</div><div class="stat-number">' + esc(v) + "</div></div>").join("");
    }

    /* rows: [{id, cells:[text or {html}]}]. Adds View / Delete buttons unless opts.noActions */
    function table(headers, rows, opts = {}) {
        const cols = headers.length + (opts.noActions ? 0 : 1);
        const head = "<tr>" + headers.map(h => "<th>" + esc(h) + "</th>").join("") + (opts.noActions ? "" : "<th>Actions</th>") + "</tr>";
        const body = rows.length ? rows.map(r =>
            "<tr>" + r.cells.map(c => "<td>" + (c && typeof c === "object" && "html" in c ? c.html : esc(c)) + "</td>").join("") +
            (opts.noActions ? "" : '<td><div class="actions"><button class="secondary" data-act="view" data-id="' + r.id + '" type="button">View</button>' +
                (opts.noDelete ? "" : '<button class="danger" data-act="del" data-id="' + r.id + '" type="button">Delete</button>') +
                "</div></td>") + "</tr>").join("")
            : '<tr><td colspan="' + cols + '" class="empty">' + esc(opts.empty || "No records found.") + "</td></tr>";
        return '<div class="table-wrap"><table><thead>' + head + "</thead><tbody>" + body + "</tbody></table></div>";
    }

    /* put table into container and connect the buttons */
    function show(container, headers, rows, handlers, opts) {
        container.innerHTML = table(headers, rows, opts);
        container.querySelectorAll("[data-act]").forEach(b => b.onclick = () => {
            const h = b.dataset.act === "view" ? handlers.view : handlers.del;
            if (h) h(b.dataset.id);
        });
    }

    /* popup */
    function modal(title, html) {
        let m = document.getElementById("cpModal");
        if (!m) {
            m = document.createElement("div");
            m.id = "cpModal"; m.className = "modal";
            m.innerHTML = '<div class="modal-card"><h2 id="cpModalTitle"></h2><div id="cpModalBody"></div>' +
                '<div style="margin-top:14px"><button class="secondary" id="cpModalClose" type="button">Close</button></div></div>';
            document.body.appendChild(m);
            m.onclick = e => { if (e.target === m) m.classList.remove("open"); };
            m.querySelector("#cpModalClose").onclick = () => m.classList.remove("open");
        }
        m.querySelector("#cpModalTitle").textContent = title;
        m.querySelector("#cpModalBody").innerHTML = html;
        m.classList.add("open");
    }
    const closeModal = () => document.getElementById("cpModal")?.classList.remove("open");

    const kv = rows => '<div class="table-wrap"><table class="kv"><tbody>' +
        rows.map(([k, v]) => "<tr><td>" + esc(k) + "</td><td>" + esc(v) + "</td></tr>").join("") + "</tbody></table></div>";
    const chips = (list, cls) => list.length ? '<div class="chips">' + list.map(n => '<span class="chip ' + (cls || "") + '">' + esc(n) + "</span>").join("") + "</div>"
        : '<div class="sub-text" style="margin:8px 0 16px">None</div>';
    const person = (n, e) => ({ html: '<div class="name">' + esc(n || "User") + '</div><div class="sub-text">' + esc(e || "") + "</div>" });

    /* search box: filters `items` with getText(item) */
    function search(inputId, items, getText, draw) {
        const input = document.getElementById(inputId);
        const run = () => { const t = input.value.trim().toLowerCase(); draw(items().filter(i => !t || getText(i).toLowerCase().includes(t))); };
        input.oninput = run; return run;
    }


    /* download a CSV file (opens in Excel). Cells that start with = + @ are made safe. */
    function csv(name, headers, rows) {
        const q = v => {
            let t = String(v ?? "");
            if (/^[=+@]|^-[^\d\s]/.test(t)) t = "'" + t;
            return '"' + t.replace(/"/g, '""') + '"';
        };
        const text = [headers, ...rows].map(r => r.map(q).join(",")).join("\r\n");
        const a = document.createElement("a");
        a.href = URL.createObjectURL(new Blob(["\ufeff" + text], { type: "text/csv;charset=utf-8" }));
        a.download = name + "-" + new Date().toISOString().slice(0, 10) + ".csv";
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    }

    return { API, esc, day, short, parseList, skillName, names, get, del, post, say, stats, table, show, modal, closeModal, kv, chips, person, search, csv };
})();
