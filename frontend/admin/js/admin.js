const API = "";

const key = () =>
    sessionStorage.getItem("careerpilot_admin_key") || "";

let roles = [];
let skills = [];
let users = [];
let selectedRoleId = null;

const $ = id => document.getElementById(id);


/* =========================================================
   AUTH
========================================================= */

function authHeaders(json = false) {

    const h = {
        "X-Admin-Key": key()
    };

    if (json) {
        h["Content-Type"] = "application/json";
    }

    return h;
}


/* =========================================================
   API HELPER
========================================================= */

async function api(path, opt = {}) {

    const res = await fetch(API + path, {
        ...opt,

        headers: {
            ...authHeaders(!!opt.body),
            ...(opt.headers || {})
        }
    });

    let d = {};

    try {
        d = await res.json();
    } catch {}

    if (!res.ok) {
        throw new Error(d.detail || "Request failed");
    }

    return d;
}


/* =========================================================
   TOAST
========================================================= */

function toast(text, error = false) {

    const x = $("toast");

    if (!x) return;

    x.textContent = text;

    x.className = "show" + (error ? " error" : "");

    setTimeout(() => {
        x.className = "";
    }, 2500);
}


/* =========================================================
   ESCAPE HTML
========================================================= */

function esc(v) {

    return String(v ?? "").replace(
        /[&<>"']/g,

        m => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        }[m])
    );
}


/* =========================================================
   MAIN LOAD
========================================================= */

async function load() {

    if (!key()) {

        location.href = "login.html";

        return;
    }


    try {

        /*
         * Load roles, skills and users together
         */

        const [r, s, u] = await Promise.all([

            api("/admin/roles"),

            api("/admin/skills"),

            api("/admin/users")

        ]);


        roles = r.roles || [];

        skills = s.skills || [];

        users = u.users || [];


        /*
         * Update statistics
         */

        $("userCount").textContent = users.length;

        $("roleCount").textContent = roles.length;

        $("skillCount").textContent = skills.length;


        /*
         * Render everything
         */

        renderUsers();

        renderRoles();

        renderSkills();

        fillSelectors();


        /*
         * Select first role automatically
         */

        if (!selectedRoleId && roles.length) {

            selectedRoleId = roles[0].id;
        }


        if (selectedRoleId) {

            $("roleSelector").value = selectedRoleId;

            await loadRoleSkills();

        } else {

            $("roleSkillsList").innerHTML =
                '<div class="role-desc">No roles available.</div>';

        }


    } catch (e) {

        toast(e.message, true);


        if (
            e.message
                .toLowerCase()
                .includes("admin")
        ) {

            setTimeout(() => {

                location.href = "login.html";

            }, 700);
        }
    }
}


/* =========================================================
   USERS
========================================================= */

function renderUsers() {

    const container = $("usersList");

    if (!container) return;


    if (!users.length) {

        container.innerHTML = `
            <div class="role-desc">
                No registered users found.
            </div>
        `;

        return;
    }


    container.innerHTML = `

        <div class="users-table-wrap">

            <table class="users-table">

                <thead>

                    <tr>

                        <th>ID</th>

                        <th>NAME</th>

                        <th>EMAIL</th>

                        <th>ROLE</th>

                        <th>REGISTERED</th>

                        <th>ACTION</th>

                    </tr>

                </thead>


                <tbody>

                    ${users.map(user => `

                        <tr>

                            <td>
                                #${esc(user.id)}
                            </td>


                            <td>

                                <div class="user-name">

                                    ${esc(user.name)}

                                </div>

                            </td>


                            <td>

                                <div class="user-email">

                                    ${esc(user.email)}

                                </div>

                            </td>


                            <td>

                                <select
                                    class="user-role-select"
                                    onchange="changeUserRole(${user.id}, this.value)"
                                >

                                    <option
                                        value="user"
                                        ${user.role === "user" ? "selected" : ""}
                                    >
                                        User
                                    </option>

                                    <option
                                        value="admin"
                                        ${user.role === "admin" ? "selected" : ""}
                                    >
                                        Admin
                                    </option>

                                </select>

                            </td>


                            <td>

                                <span class="user-date">

                                    ${formatDate(user.created_at)}

                                </span>

                            </td>


                            <td>

                                <button
                                    class="danger"
                                    onclick="deleteUser(${user.id})"
                                >
                                    Delete
                                </button>

                            </td>

                        </tr>

                    `).join("")}

                </tbody>

            </table>

        </div>
    `;
}


/* =========================================================
   FORMAT DATE
========================================================= */

function formatDate(value) {

    if (!value) {

        return "—";
    }


    try {

        const date = new Date(value);

        if (isNaN(date.getTime())) {

            return value;
        }


        return date.toLocaleDateString(
            "en-IN",
            {
                day: "2-digit",
                month: "short",
                year: "numeric"
            }
        );

    } catch {

        return value;
    }
}


/* =========================================================
   CHANGE USER ROLE
========================================================= */

async function changeUserRole(userId, role) {

    try {

        await api(
            `/admin/users/${userId}/role`,
            {
                method: "PUT",

                body: JSON.stringify({
                    role: role
                })
            }
        );


        toast("User role updated");


        /*
         * Refresh users
         */

        await loadUsersOnly();

    } catch (e) {

        toast(e.message, true);

        /*
         * Reload old value if update fails
         */

        await loadUsersOnly();
    }
}


/* =========================================================
   DELETE USER
========================================================= */

async function deleteUser(userId) {

    const user = users.find(
        x => Number(x.id) === Number(userId)
    );


    if (!user) return;


    /*
     * Prevent accidental deletion
     */

    if (
        !confirm(
            `Delete user "${user.name}"?\n\nThis action cannot be undone.`
        )
    ) {

        return;
    }


    try {

        await api(
            `/admin/users/${userId}`,
            {
                method: "DELETE"
            }
        );


        toast("User deleted");


        await loadUsersOnly();

    } catch (e) {

        toast(e.message, true);
    }
}


/* =========================================================
   LOAD USERS ONLY
========================================================= */

async function loadUsersOnly() {

    try {

        const u = await api("/admin/users");

        users = u.users || [];


        $("userCount").textContent =
            users.length;


        renderUsers();

    } catch (e) {

        toast(e.message, true);
    }
}


/* =========================================================
   REFRESH USERS BUTTON
========================================================= */

const refreshUsersBtn =
    $("refreshUsersBtn");


if (refreshUsersBtn) {

    refreshUsersBtn.onclick = async () => {

        await loadUsersOnly();

        toast("Users refreshed");

    };
}


/* =========================================================
   ROLES
========================================================= */

function renderRoles() {

    $("rolesList").innerHTML =

        roles.length

        ?

        roles.map(r => `

            <div class="role-row">

                <div>

                    <div class="role-name">

                        ${esc(r.name)}

                    </div>


                    <div class="role-desc">

                        ${esc(
                            r.description ||
                            "No description"
                        )}

                    </div>


                    <div class="role-desc">

                        ${r.skill_count || 0}
                        required skills

                    </div>

                </div>


                <div class="actions">

                    <button
                        class="secondary"
                        onclick="editRole(${r.id})"
                    >
                        Edit
                    </button>


                    <button
                        class="danger"
                        onclick="deleteRole(${r.id})"
                    >
                        Delete
                    </button>

                </div>

            </div>

        `).join("")

        :

        '<div class="role-desc">No job roles.</div>';
}


/* =========================================================
   SKILLS
========================================================= */

function renderSkills() {

    $("skillsList").innerHTML =

        skills.length

        ?

        skills.map(s => `

            <div class="skill-row">

                <div>

                    <div class="skill-name">

                        ${esc(s.name)}

                    </div>


                    <div class="skill-cat">

                        ${esc(
                            s.category ||
                            "General"
                        )}

                    </div>

                </div>

            </div>

        `).join("")

        :

        '<div class="role-desc">No master skills.</div>';
}


/* =========================================================
   SELECTORS
========================================================= */

function fillSelectors() {

    $("roleSelector").innerHTML =

        roles.map(r => `

            <option value="${r.id}">

                ${esc(r.name)}

            </option>

        `).join("");


    $("skillSelector").innerHTML =

        skills.map(s => `

            <option value="${s.id}">

                ${esc(s.name)}

            </option>

        `).join("");
}


/* =========================================================
   ROLE SKILLS
========================================================= */

async function loadRoleSkills() {

    selectedRoleId =
        Number($("roleSelector").value);


    if (!selectedRoleId) {

        $("selectedCount").textContent = "—";

        return;
    }


    const d =
        await api(
            `/admin/roles/${selectedRoleId}/skills`
        );


    const list =
        d.skills || [];


    $("selectedCount").textContent =
        list.length;


    $("roleSkillsList").innerHTML =

        list.length

        ?

        list.map(s => `

            <div class="skill-row">

                <div>

                    <div class="skill-name">

                        ${esc(s.name)}

                    </div>


                    <div class="skill-cat">

                        ${esc(
                            s.category ||
                            "General"
                        )}

                    </div>

                </div>


                <div
                    style="
                        display:flex;
                        gap:10px;
                        align-items:center
                    "
                >

                    <span class="importance">

                        ${s.importance}

                    </span>


                    <button
                        class="danger"
                        onclick="
                            removeSkill(
                                ${selectedRoleId},
                                ${s.id}
                            )
                        "
                    >
                        Remove
                    </button>

                </div>

            </div>

        `).join("")

        :

        '<div class="role-desc">No requirements assigned to this role.</div>';
}


/* =========================================================
   ROLE SELECTOR
========================================================= */

$("roleSelector").onchange =
    loadRoleSkills;


/* =========================================================
   ADD ROLE
========================================================= */

$("addRoleBtn").onclick = () =>
    openRole();


/* =========================================================
   ADD SKILL
========================================================= */

$("addSkillBtn").onclick = () =>
    $("skillModal").classList.add("open");


/* =========================================================
   CLOSE MODALS
========================================================= */

document
    .querySelectorAll("[data-close]")
    .forEach(b => {

        b.onclick = () => {

            $(b.dataset.close)
                .classList
                .remove("open");

        };

    });


/* =========================================================
   ROLE FORM
========================================================= */

$("roleForm").onsubmit = async e => {

    e.preventDefault();


    const id =
        $("roleId").value;


    const body = {

        name:
            $("roleName")
                .value
                .trim(),

        description:
            $("roleDescription")
                .value
                .trim()

    };


    try {

        await api(

            id
                ? `/admin/roles/${id}`
                : "/admin/roles",

            {

                method:
                    id
                        ? "PUT"
                        : "POST",

                body:
                    JSON.stringify(body)

            }

        );


        $("roleModal")
            .classList
            .remove("open");


        toast(
            id
                ? "Role updated"
                : "Role created"
        );


        selectedRoleId = null;


        await load();

    } catch (e) {

        toast(
            e.message,
            true
        );
    }
};


/* =========================================================
   SKILL FORM
========================================================= */

$("skillForm").onsubmit = async e => {

    e.preventDefault();


    try {

        await api(

            "/admin/skills",

            {

                method: "POST",

                body:
                    JSON.stringify({

                        name:
                            $("skillName")
                                .value
                                .trim(),

                        category:
                            $("skillCategory")
                                .value
                                .trim()

                    })

            }

        );


        $("skillModal")
            .classList
            .remove("open");


        e.target.reset();


        toast("Skill created");


        await load();

    } catch (e) {

        toast(
            e.message,
            true
        );
    }
};


/* =========================================================
   ASSIGN ROLE SKILL
========================================================= */

$("assignBtn").onclick = async () => {

    if (!selectedRoleId) return;


    try {

        await api(

            `/admin/roles/${selectedRoleId}/skills`,

            {

                method: "POST",

                body:
                    JSON.stringify({

                        skill_id:
                            Number(
                                $("skillSelector")
                                    .value
                            ),

                        importance:
                            Math.max(
                                0,
                                Math.min(
                                    100,
                                    Number(
                                        $("importance")
                                            .value
                                    ) || 0
                                )
                            )

                    })

            }

        );


        toast(
            "Requirement saved"
        );


        await loadRoleSkills();

    } catch (e) {

        toast(
            e.message,
            true
        );
    }
};


/* =========================================================
   OPEN ROLE
========================================================= */

function openRole(r = null) {

    $("roleTitle").textContent =

        r
            ? "Edit Job Role"
            : "Add Job Role";


    $("roleId").value =
        r
            ? r.id
            : "";


    $("roleName").value =
        r
            ? r.name
            : "";


    $("roleDescription").value =
        r
            ? r.description || ""
            : "";


    $("roleModal")
        .classList
        .add("open");
}


/* =========================================================
   EDIT ROLE
========================================================= */

function editRole(id) {

    const r =
        roles.find(
            x => x.id === id
        );


    if (r) {

        openRole(r);
    }
}


/* =========================================================
   DELETE ROLE
========================================================= */

async function deleteRole(id) {

    const r =
        roles.find(
            x => x.id === id
        );


    if (
        !r ||
        !confirm(
            `Delete "${r.name}"?`
        )
    ) {

        return;
    }


    try {

        await api(

            `/admin/roles/${id}`,

            {
                method: "DELETE"
            }

        );


        toast(
            "Role deleted"
        );


        selectedRoleId = null;


        await load();

    } catch (e) {

        toast(
            e.message,
            true
        );
    }
}


/* =========================================================
   REMOVE ROLE SKILL
========================================================= */

async function removeSkill(
    roleId,
    skillId
) {

    if (
        !confirm(
            "Remove this requirement?"
        )
    ) {

        return;
    }


    try {

        await api(

            `/admin/roles/${roleId}/skills/${skillId}`,

            {
                method: "DELETE"
            }

        );


        toast(
            "Requirement removed"
        );


        await loadRoleSkills();

    } catch (e) {

        toast(
            e.message,
            true
        );
    }
}


/* =========================================================
   LOGOUT
========================================================= */

$("logoutBtn").onclick = e => {

    e.preventDefault();


    sessionStorage.removeItem(
        "careerpilot_admin_key"
    );


    sessionStorage.removeItem(
        "careerpilot_admin_name"
    );


    location.href =
        "login.html";
};


/* =========================================================
   START
========================================================= */

load();