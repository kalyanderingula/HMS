const API = "http://localhost:8000/api/v1";

// Auth check for Receptionist & Admin roles
(function checkAuth() {
    const token = localStorage.getItem("hms_token");
    const roles = localStorage.getItem("hms_roles");
    if (!token || !roles) {
        window.location.href = "/";
        return;
    }
    const parsedRoles = JSON.parse(roles);
    if (!parsedRoles.some(r => ['receptionist', 'admin', 'super_admin'].includes(r))) {
        window.location.href = "/";
        return;
    }
    const usernameEl = document.querySelector(".sidebar-header p");
    if (usernameEl) usernameEl.textContent = `${localStorage.getItem("hms_name") || "Reception Desk"} (${parsedRoles.join(', ').replace(/_/g, ' ')})`;
})();

function logout() {
    localStorage.clear();
    window.location.href = "/";
}

let patientsCache = [];
let patientMastersCache = null;

// ============ NAVIGATION ============
document.querySelectorAll(".nav-links a").forEach(link => {
    link.addEventListener("click", (e) => {
        e.preventDefault();
        const page = link.dataset.page;
        if (!page) return;
        navigateTo(page);
    });
});

function navigateTo(page) {
    document.querySelectorAll(".nav-links a").forEach(l => l.classList.remove("active"));
    const activeLink = document.querySelector(`.nav-links a[data-page="${page}"]`);
    if (activeLink) activeLink.classList.add("active");

    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    const targetPage = document.getElementById(`page-${page}`);
    if (targetPage) targetPage.classList.add("active");

    loadPage(page);
}

function loadPage(page) {
    if (page === "dashboard") loadDashboard();
    if (page === "patients") { showView("patient-list-view"); loadPatients(); }
    if (page === "register") { loadPatientFormMasters(); }
}

function showView(viewId) {
    const el = document.getElementById(viewId);
    if (!el) return;
    const parent = el.parentElement;
    parent.querySelectorAll(":scope > div").forEach(d => d.classList.add("hidden"));
    el.classList.remove("hidden");
}

function goToRegister() {
    navigateTo("register");
}

function goToPatients() {
    navigateTo("patients");
}

// ============ HTTP HELPERS ============
function showToast(msg, type = "success") {
    const t = document.getElementById("toast");
    t.textContent = msg;
    t.className = `toast ${type} show`;
    setTimeout(() => t.classList.remove("show"), 3500);
}

async function get(url) {
    const r = await fetch(`${API}${url}`);
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || "Error fetching data"); }
    return r.json();
}

async function post(url, data) {
    const r = await fetch(`${API}${url}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    });
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || "Error submitting data"); }
    return r.json();
}

// ============ DASHBOARD & QUICK SEARCH ============
async function loadDashboard() {
    try {
        patientsCache = await get("/patients/");
        document.getElementById("stat-total-patients").textContent = patientsCache.length || 0;
        
        // Count today's patients
        const todayStr = new Date().toISOString().split("T")[0];
        const todayCount = patientsCache.filter(p => p.created_at && p.created_at.startsWith(todayStr)).length;
        document.getElementById("stat-today-patients").textContent = todayCount;
    } catch (err) {
        console.error("Dashboard stats error:", err);
    }
}

function quickSearch(query) {
    const resultsContainer = document.getElementById("quick-search-results");
    const q = (query || "").toLowerCase().trim();
    if (!q) {
        resultsContainer.innerHTML = "";
        return;
    }
    const matches = patientsCache.filter(p =>
        (p.mrn || "").toLowerCase().includes(q) ||
        (p.patient_code || "").toLowerCase().includes(q) ||
        (p.first_name || "").toLowerCase().includes(q) ||
        (p.last_name || "").toLowerCase().includes(q) ||
        (p.phone || "").toLowerCase().includes(q)
    ).slice(0, 5);

    if (!matches.length) {
        resultsContainer.innerHTML = `<p style="color:#64748b;padding:8px 0;">No matching patients found. <a href="#" onclick="goToRegister()" style="color:var(--primary,#2563eb);font-weight:600;">Register new patient</a></p>`;
        return;
    }

    resultsContainer.innerHTML = `
        <div style="background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;overflow:hidden;">
            ${matches.map(p => `
                <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 16px;border-bottom:1px solid #e2e8f0;">
                    <div>
                        <strong>${p.first_name} ${p.last_name}</strong> (${p.gender_name || '-'}, ${p.date_of_birth || '-'})
                        <div style="font-size:12px;color:#64748b;">MRN: <strong style="color:var(--primary,#2563eb);">${p.mrn}</strong> | Phone: ${p.phone || '-'}</div>
                    </div>
                    <button class="btn-sm btn-view" onclick="viewPatientProfileDirect('${p.patient_id}')">Open Profile</button>
                </div>
            `).join("")}
        </div>
    `;
}

// ============ PATIENT DIRECTORY ============
async function loadPatients() {
    try {
        patientsCache = await get("/patients/");
        renderPatientTable(patientsCache);
    } catch (err) {
        showToast(err.message, "error");
    }
}

function searchPatients() {
    const query = (document.getElementById("patient-search-input").value || "").toLowerCase().trim();
    if (!query) {
        renderPatientTable(patientsCache);
        return;
    }
    const filtered = patientsCache.filter(p =>
        (p.mrn || "").toLowerCase().includes(query) ||
        (p.patient_code || "").toLowerCase().includes(query) ||
        (p.first_name || "").toLowerCase().includes(query) ||
        (p.last_name || "").toLowerCase().includes(query) ||
        (p.phone || "").toLowerCase().includes(query) ||
        (p.city || "").toLowerCase().includes(query)
    );
    renderPatientTable(filtered);
}

function renderPatientTable(patients) {
    const tbody = document.getElementById("patient-table-body");
    if (!patients || !patients.length) {
        tbody.innerHTML = `<tr class="empty-row"><td colspan="9" style="text-align:center;padding:24px;">No patients found. Click "+ Register New Patient" to add one.</td></tr>`;
        return;
    }
    tbody.innerHTML = patients.map(p => `
        <tr>
            <td><strong>${p.mrn}</strong><br><small style="color:#64748b;">${p.patient_code}</small></td>
            <td><strong>${p.first_name} ${p.middle_name ? p.middle_name + ' ' : ''}${p.last_name}</strong></td>
            <td>${p.gender_name || "-"}</td>
            <td>${p.date_of_birth || "-"}</td>
            <td><span class="badge badge-active">${p.blood_group_name || "-"}</span></td>
            <td>${p.phone || "-"}</td>
            <td>${p.city || "-"}</td>
            <td><span class="badge ${p.status_name === 'Active' ? 'badge-active' : 'badge-inactive'}">${p.status_name || 'Active'}</span></td>
            <td>
                <button class="btn-sm btn-view" onclick="viewPatientProfile('${p.patient_id}')">Profile Details</button>
            </td>
        </tr>
    `).join("");
}

// ============ REGISTER PATIENT ============
async function loadPatientFormMasters() {
    try {
        if (!patientMastersCache) {
            patientMastersCache = await get("/patients/masters");
        }
        const genderSel = document.getElementById("patient-add-gender");
        genderSel.innerHTML = `<option value="">Select Gender</option>` + patientMastersCache.genders.map(g => `<option value="${g.id}">${g.name}</option>`).join("");

        const bgSel = document.getElementById("patient-add-blood-group");
        bgSel.innerHTML = `<option value="">Select Blood Group</option>` + patientMastersCache.blood_groups.map(bg => `<option value="${bg.id}">${bg.name}</option>`).join("");

        const msSel = document.getElementById("patient-add-marital-status");
        msSel.innerHTML = `<option value="">Select Marital Status</option>` + patientMastersCache.marital_statuses.map(ms => `<option value="${ms.id}">${ms.name}</option>`).join("");
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function createPatient(e) {
    e.preventDefault();
    const form = document.getElementById("patient-add-form");
    const fd = new FormData(form);
    const data = {
        first_name: fd.get("first_name"),
        middle_name: fd.get("middle_name") || null,
        last_name: fd.get("last_name"),
        date_of_birth: fd.get("date_of_birth"),
        gender_id: parseInt(fd.get("gender_id")),
        blood_group_id: fd.get("blood_group_id") ? parseInt(fd.get("blood_group_id")) : null,
        marital_status_id: fd.get("marital_status_id") ? parseInt(fd.get("marital_status_id")) : null,
        phone: fd.get("phone"),
        email: fd.get("email") || null,
        address_line1: fd.get("address_line1") || null,
        city: fd.get("city") || null,
        state: fd.get("state") || null,
        postal_code: fd.get("postal_code") || null,
        emergency_contact_name: fd.get("emergency_contact_name") || null,
        emergency_contact_relation: fd.get("emergency_contact_relation") || null,
        emergency_contact_phone: fd.get("emergency_contact_phone") || null
    };

    try {
        const created = await post("/patients/", data);
        showToast(`Patient ${created.first_name} registered successfully with MRN ${created.mrn}!`);
        form.reset();
        navigateTo("patients");
    } catch (err) {
        showToast(err.message, "error");
    }
}

// ============ PROFILE DETAILS ============
async function viewPatientProfileDirect(patientId) {
    navigateTo("patients");
    await viewPatientProfile(patientId);
}

async function viewPatientProfile(patientId) {
    try {
        const p = await get(`/patients/${patientId}`);
        const card = document.getElementById("patient-profile-card");
        
        const primaryPhone = (p.contacts && p.contacts.find(c => c.contact_type === 'phone'))?.contact_value || p.phone || "-";
        const email = (p.contacts && p.contacts.find(c => c.contact_type === 'email'))?.contact_value || p.email || "-";
        const address = p.addresses && p.addresses.length > 0 ? `${p.addresses[0].line1}, ${p.addresses[0].city || ''}, ${p.addresses[0].state || ''} ${p.addresses[0].postal_code || ''}` : "-";
        const emg = p.emergency_contacts && p.emergency_contacts.length > 0 ? `${p.emergency_contacts[0].full_name} (${p.emergency_contacts[0].relationship || 'Relative'}) - ${p.emergency_contacts[0].phone || '-'}` : "None Listed";

        card.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #e2e8f0;padding-bottom:16px;margin-bottom:20px;">
                <div>
                    <h2 style="margin:0;color:#1e293b;">${p.first_name} ${p.middle_name ? p.middle_name + ' ' : ''}${p.last_name}</h2>
                    <p style="margin:4px 0 0;color:#64748b;">MRN: <strong style="color:var(--primary,#2563eb);">${p.mrn}</strong> | Patient Code: ${p.patient_code}</p>
                </div>
                <span class="badge ${p.status_name === 'Active' ? 'badge-active' : 'badge-inactive'}" style="font-size:14px;padding:6px 14px;">${p.status_name || 'Active'}</span>
            </div>

            <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(240px, 1fr));gap:20px;margin-bottom:24px;">
                <div style="background:#f8fafc;padding:16px;border-radius:8px;border:1px solid #e2e8f0;">
                    <h4 style="margin:0 0 10px;color:#475569;">Demographics</h4>
                    <p style="margin:6px 0;"><strong>Date of Birth:</strong> ${p.date_of_birth}</p>
                    <p style="margin:6px 0;"><strong>Gender:</strong> ${p.gender_name || '-'}</p>
                    <p style="margin:6px 0;"><strong>Blood Group:</strong> <span class="badge badge-active">${p.blood_group_name || '-'}</span></p>
                    <p style="margin:6px 0;"><strong>Marital Status:</strong> ${p.marital_status_name || '-'}</p>
                </div>

                <div style="background:#f8fafc;padding:16px;border-radius:8px;border:1px solid #e2e8f0;">
                    <h4 style="margin:0 0 10px;color:#475569;">Contact Info</h4>
                    <p style="margin:6px 0;"><strong>Primary Phone:</strong> ${primaryPhone}</p>
                    <p style="margin:6px 0;"><strong>Email:</strong> ${email}</p>
                    <p style="margin:6px 0;"><strong>Address:</strong> ${address}</p>
                </div>

                <div style="background:#f8fafc;padding:16px;border-radius:8px;border:1px solid #e2e8f0;">
                    <h4 style="margin:0 0 10px;color:#475569;">Emergency Contact</h4>
                    <p style="margin:6px 0;">${emg}</p>
                    <p style="margin:6px 0;color:#64748b;font-size:12px;">Registered On: ${new Date(p.created_at).toLocaleDateString()}</p>
                </div>
            </div>
        `;
        showView("patient-detail-view");
    } catch (err) {
        showToast(err.message, "error");
    }
}

// Initial load
loadDashboard();
