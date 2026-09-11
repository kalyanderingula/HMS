const API = "/api/v1";

document.documentElement.style.display = "none";

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
    const badgeEl = document.getElementById("receptionist-badge");
    if (badgeEl) {
        badgeEl.textContent = `${localStorage.getItem("hms_name") || "Sarah Jenkins"} (${parsedRoles.join(', ').replace(/_/g, ' ')})`;
    }
})();

function logout() {
    localStorage.clear();
    window.location.href = "/";
}

let patientsCache = [];
let patientMastersCache = null;
let doctorsCache = [];
let inpatientsCache = [];
let liveQueueCache = [];
let liveQueueFilter = "queued";

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
    if (page === "doctors") loadDoctorRoster();
    if (page === "queue") loadLiveQueue();
    if (page === "patients") { showView("patient-list-view"); loadPatients(); }
    if (page === "register") { loadPatientFormMasters(); }
    if (page === "inpatient") loadInpatients();
    if (page === "visitors") loadVisitorPasses();
}

function showView(viewId) {
    const el = document.getElementById(viewId);
    if (!el) return;
    const parent = el.parentElement;
    parent.querySelectorAll(":scope > div").forEach(d => d.classList.add("hidden"));
    el.classList.remove("hidden");
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add("hidden");
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
    const r = await fetch(`${API}${url}`, { headers: { "Authorization": `Bearer ${localStorage.getItem("hms_token")}` } });
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || "Error fetching data"); }
    return r.json();
}

async function post(url, data) {
    const r = await fetch(`${API}${url}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${localStorage.getItem("hms_token")}` },
        body: JSON.stringify(data)
    });
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || "Error submitting data"); }
    return r.json();
}

async function put(url) {
    const r = await fetch(`${API}${url}`, { method: "PUT", headers: { "Authorization": `Bearer ${localStorage.getItem("hms_token")}` } });
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || "Error updating status"); }
    return r.json();
}

// ============ 1. DASHBOARD & RECENT ACTIVITY ============
async function loadDashboard() {
    try {
        const activityBody = document.getElementById("recent-activity-list");
        const activityTitle = activityBody.closest(".card").querySelector("h3");
        activityTitle.textContent = "🕒 Live Front Desk Activity Stream";
        document.getElementById("activity-stream-reset")?.remove();
        const summary = await get("/receptionist/dashboard-summary");
        document.getElementById("stat-total-patients").textContent = summary.total_patients_today;
        document.getElementById("stat-total-apts").textContent = summary.total_appointments_today;
        document.getElementById("stat-checked-in").textContent = summary.checked_in_today;
        document.getElementById("stat-active-docs").textContent = summary.active_doctors_count;
        document.getElementById("stat-waiting-queue").textContent = summary.waiting_tokens_count;

        // Render Recent Activity Stream
        const actEl = document.getElementById("recent-activity-list");
        if (summary.recent_activities && summary.recent_activities.length > 0) {
            actEl.innerHTML = summary.recent_activities.map(a => `
                <div style="display:flex;justify-content:space-between;align-items:center;padding:12px;background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;">
                    <div>
                        <strong style="color:#1e293b;">${a.title}</strong>
                        <div style="font-size:12px;color:#64748b;margin-top:2px;">${a.description}</div>
                    </div>
                    <div style="text-align:right;">
                        <span class="badge ${a.activity_type === 'registration' ? 'badge-active' : 'badge-opd'}">${a.badge}</span>
                        <div style="font-size:11px;color:#94a3b8;margin-top:4px;">${new Date(a.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                    </div>
                </div>
            `).join("");
        } else {
            actEl.innerHTML = `<p style="color:#64748b;font-size:13px;">No recent front desk activities recorded yet today.</p>`;
        }

        // Cache patients
        patientsCache = await get("/patients/");
    } catch (err) {
        console.error("Dashboard load error:", err);
    }
}

// ============ QUICK SEARCH & LIVE ACTIONS ============
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
        resultsContainer.innerHTML = `
            <div style="background:#fef2f2;border:1px solid #fecaca;padding:12px;border-radius:6px;color:#991b1b;display:flex;justify-content:space-between;align-items:center;">
                <span>No patient found matching "<strong>${query}</strong>"</span>
                <button class="btn-sm btn-primary" onclick="goToRegister()">+ Quick Register</button>
            </div>
        `;
        return;
    }

    resultsContainer.innerHTML = `
        <div style="background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;overflow:hidden;">
            ${matches.map(p => `
                <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-bottom:1px solid #e2e8f0;">
                    <div>
                        <strong>${p.first_name} ${p.last_name}</strong> (${p.gender_name || '-'}, DOB: ${p.date_of_birth || '-'})
                        <div style="font-size:12px;color:#64748b;margin-top:2px;">MRN: <strong style="color:var(--primary,#2563eb);">${p.mrn}</strong> | Phone: ${p.phone || '-'} | Blood Group: <span class="badge badge-active">${p.blood_group_name || '-'}</span></div>
                    </div>
                    <div style="display:flex;gap:8px;">
                        <button class="btn-sm btn-primary" onclick="openDirectBooking('${p.patient_id}')">🎟️ Book OPD Token</button>
                        <button class="btn-sm btn-view" onclick="viewPatientProfileDirect('${p.patient_id}')">Open Profile</button>
                    </div>
                </div>
            `).join("")}
        </div>
    `;
}

// ============ 2. OPD DOCTOR ROSTER ============
async function loadDoctorRoster() {
    try {
        doctorsCache = await get("/receptionist/doctors/availability");
        const grid = document.getElementById("doctor-roster-grid");
        if (!doctorsCache || !doctorsCache.length) {
            grid.innerHTML = `<p style="color:#64748b;">No doctors currently on roster.</p>`;
            return;
        }

        grid.innerHTML = doctorsCache.map(d => `
            <div class="card" style="padding:20px;background:#fff;border-radius:10px;border:1px solid #e2e8f0;box-shadow:var(--shadow);">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div>
                        <h3 style="margin:0;color:#1e293b;font-size:17px;">${d.doctor_name}</h3>
                        <span class="badge-opd" style="margin-top:6px;display:inline-block;">${d.specialization_name}</span>
                    </div>
                    <span class="badge badge-active">${d.status}</span>
                </div>
                
                <div style="margin:16px 0;font-size:13px;color:#475569;line-height:1.6;">
                    <div>📍 <strong>Room:</strong> <span style="color:#059669;font-weight:700;">${d.room_number}</span></div>
                    <div>🕒 <strong>Shift:</strong> ${d.shift_timings}</div>
                    <div>💵 <strong>Fee:</strong> $${d.consultation_fee.toFixed(2)}</div>
                    <div>🎟️ <strong>Active Queue:</strong> ${d.waiting_queue_count} waiting (${d.tokens_issued_today} issued)</div>
                </div>

                <button class="btn btn-primary btn-full" onclick="openBookingModal('${d.doctor_id}', '${d.doctor_name}', '${d.specialization_name}', '${d.room_number}')">
                    + Book Consultation Token
                </button>
            </div>
        `).join("");
    } catch (err) {
        showToast(err.message, "error");
    }
}

// ============ OPD BOOKING MODAL ============
async function openBookingModal(doctorId, doctorName, specName, roomNo) {
    document.getElementById("book-doctor-id").value = doctorId;
    document.getElementById("book-doc-name").textContent = doctorName;
    document.getElementById("book-doc-spec").textContent = `${specName} | ${roomNo}`;

    // Load Patient Dropdown
    if (!patientsCache || !patientsCache.length) {
        patientsCache = await get("/patients/");
    }

    const selectEl = document.getElementById("book-patient-select");
    selectEl.innerHTML = `<option value="">-- Choose Registered Patient --</option>` +
        patientsCache.map(p => `<option value="${p.patient_id}">${p.first_name} ${p.last_name} (MRN: ${p.mrn}) - ${p.phone || ''}</option>`).join("");

    document.getElementById("booking-modal").classList.remove("hidden");
}

function openDirectBooking(patientId) {
    if (!doctorsCache || !doctorsCache.length) {
        get("/receptionist/doctors/availability").then(docs => {
            doctorsCache = docs;
            if (docs.length) {
                openBookingModal(docs[0].doctor_id, docs[0].doctor_name, docs[0].specialization_name, docs[0].room_number);
                document.getElementById("book-patient-select").value = patientId;
            }
        });
    } else {
        openBookingModal(doctorsCache[0].doctor_id, doctorsCache[0].doctor_name, doctorsCache[0].specialization_name, doctorsCache[0].room_number);
        document.getElementById("book-patient-select").value = patientId;
    }
}

async function submitOPDBooking(e) {
    e.preventDefault();
    const form = document.getElementById("opd-booking-form");
    const fd = new FormData(form);

    const payload = {
        patient_id: fd.get("patient_id"),
        doctor_id: fd.get("doctor_id"),
        appointment_type: fd.get("appointment_type") || "Walk-in",
        appointment_date: fd.get("appointment_date") || null,
        time_slot: fd.get("time_slot") || "Immediate",
        chief_complaint: fd.get("chief_complaint") || null,
        consultation_fee: 600.0,
        payment_method: fd.get("payment_method") || "Cash"
    };

    try {
        const slip = await post("/receptionist/appointments/book", payload);
        closeModal("booking-modal");
        showPrintableSlip(slip);
        showToast(`Token ${slip.token_number} generated for ${slip.patient_name}!`);
    } catch (err) {
        showToast(err.message, "error");
    }
}

function showPrintableSlip(slip) {
    document.getElementById("slip-token-number").textContent = slip.token_number;
    document.getElementById("slip-room-number").textContent = slip.room_number;
    document.getElementById("slip-patient-name").textContent = slip.patient_name;
    document.getElementById("slip-mrn").textContent = slip.mrn;
    document.getElementById("slip-doctor-name").textContent = slip.doctor_name;
    document.getElementById("slip-specialization").textContent = slip.specialization_name;
    document.getElementById("slip-apt-num").textContent = slip.appointment_number;
    document.getElementById("slip-fee").textContent = `$${parseFloat(slip.consultation_fee).toFixed(2)} (${slip.payment_method})`;
    document.getElementById("slip-issued-at").textContent = `Issued: ${new Date(slip.issued_at).toLocaleString()}`;

    document.getElementById("slip-modal").classList.remove("hidden");
}

// ============ 3. LIVE TOKEN QUEUE ============
async function loadLiveQueue() {
    try {
        const qData = await get("/receptionist/queue/live");
        liveQueueCache = qData.tokens || [];
        const waiting = liveQueueCache.filter(t => t.status === "waiting");
        document.getElementById("queue-stat-total").textContent = Math.max(waiting.length - 1, 0);
        document.getElementById("queue-stat-waiting").textContent = waiting.length ? 1 : 0;
        document.getElementById("queue-stat-incons").textContent = liveQueueCache.filter(t => ["called", "in_consultation"].includes(t.status)).length;
        document.getElementById("queue-stat-completed").textContent = qData.completed_count;
        renderLiveQueue();
    } catch (err) {
        showToast(err.message, "error");
    }
}

function filterLiveQueue(filter) {
    liveQueueFilter = filter;
    document.querySelectorAll("[data-queue-filter]").forEach(card => card.classList.toggle("queue-filter-active", card.dataset.queueFilter === filter));
    renderLiveQueue();
}

function renderLiveQueue() {
        const tbody = document.getElementById("queue-table-body");
        const waiting = liveQueueCache.filter(t => t.status === "waiting");
        let tokens = liveQueueCache;
        if (liveQueueFilter === "queued") tokens = waiting.slice(1);
        if (liveQueueFilter === "next") tokens = waiting.slice(0, 1);
        if (liveQueueFilter === "in_consultation") tokens = liveQueueCache.filter(t => ["called", "in_consultation"].includes(t.status));
        if (liveQueueFilter === "completed") tokens = liveQueueCache.filter(t => t.status === "completed");
        if (!tokens.length) {
            tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:24px;color:#64748b;">No active tokens in today's queue.</td></tr>`;
            return;
        }

        tbody.innerHTML = tokens.map(t => {
            let statusBadge = `<span class="badge-waiting">⏳ Waiting</span>`;
            if (t.status === "called") statusBadge = `<span class="badge-called">📢 Called</span>`;
            if (t.status === "in_consultation") statusBadge = `<span class="badge-opd">🩺 In Consultation</span>`;
            if (t.status === "completed") statusBadge = `<span class="badge-completed">✅ Completed</span>`;

            return `
                <tr>
                    <td><strong style="font-size:16px;color:#1e40af;">${t.token_number}</strong></td>
                    <td><strong>${t.patient_name}</strong></td>
                    <td><span style="font-size:12px;color:#64748b;">${t.mrn}</span></td>
                    <td>${t.doctor_name}</td>
                    <td><strong style="color:#059669;">${t.room_number}</strong></td>
                    <td><span class="badge-walkin">${t.token_type}</span></td>
                    <td>${new Date(t.issued_at).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</td>
                    <td>${statusBadge}</td>
                    <td>
                        ${t.status === 'waiting' ? `<span style="color:#64748b;font-size:12px;font-weight:600;">Waiting for doctor</span>` : ''}
                        ${t.status === 'called' ? `<span style="color:#1d4ed8;font-size:12px;font-weight:600;">Called by doctor</span>` : ''}
                        ${t.status === 'in_consultation' ? `<span style="color:#7c3aed;font-size:12px;font-weight:600;">With doctor</span>` : ''}
                        ${t.status === 'completed' ? `<span style="color:#059669;font-size:12px;font-weight:600;">Done</span>` : ''}
                    </td>
                </tr>
            `;
        }).join("");
}

// ============ 4. PATIENT DIRECTORY ============
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
            <td style="white-space:nowrap;">
                <button class="btn-sm btn-primary" onclick="openDirectBooking('${p.patient_id}')">🎟️ OPD Token</button>
                <button class="btn-sm btn-view" onclick="viewPatientProfile('${p.patient_id}')">Profile</button>
            </td>
        </tr>
    `).join("");
}

// ============ 5. PATIENT REGISTRATION & DUPLICATE CHECK ============
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

async function checkDuplicatesLive() {
    const phone = document.getElementById("reg-phone").value.trim();
    const fname = document.getElementById("reg-fname").value.trim();
    const lname = document.getElementById("reg-lname").value.trim();
    const dob = document.getElementById("reg-dob").value;

    if (!phone && (!fname || !lname)) return;

    try {
        const res = await post("/receptionist/patients/check-duplicate", {
            phone: phone || null,
            first_name: fname || null,
            last_name: lname || null,
            date_of_birth: dob || null
        });

        const banner = document.getElementById("duplicate-warning-banner");
        if (res.is_duplicate && res.matches.length > 0) {
            banner.innerHTML = `
                <strong style="color:#b45309;">⚠️ Possible Duplicate Patient Detected:</strong>
                <ul style="margin:6px 0 0 16px;color:#78350f;font-size:13px;">
                    ${res.matches.map(m => `
                        <li><strong>${m.full_name}</strong> (MRN: ${m.mrn}, Phone: ${m.phone || '-'}, DOB: ${m.date_of_birth}) — <em>${m.match_reason}</em> 
                        <a href="#" onclick="viewPatientProfileDirect('${m.patient_id}')" style="color:#2563eb;font-weight:600;margin-left:6px;">View Existing Profile</a></li>
                    `).join("")}
                </ul>
            `;
            banner.classList.remove("hidden");
        } else {
            banner.classList.add("hidden");
        }
    } catch (err) {
        console.error("Duplicate check error:", err);
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
        showToast(`Patient ${created.first_name} registered with MRN ${created.mrn}!`);
        form.reset();
        document.getElementById("duplicate-warning-banner").classList.add("hidden");
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
                <div style="display:flex;gap:10px;">
                    <button class="btn btn-primary" onclick="openDirectBooking('${p.patient_id}')">🎟️ Book OPD Token</button>
                    <span class="badge ${p.status_name === 'Active' ? 'badge-active' : 'badge-inactive'}" style="font-size:14px;padding:6px 14px;">${p.status_name || 'Active'}</span>
                </div>
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
                    <p style="margin:6px 0;color:#64748b;font-size:12px;">Registered: ${new Date(p.created_at).toLocaleDateString()}</p>
                </div>
            </div>
        `;
        showView("patient-detail-view");
    } catch (err) {
        showToast(err.message, "error");
    }
}

// ============ 6. INPATIENT / BED ENQUIRY ============
async function loadInpatients() {
    try {
        inpatientsCache = await get("/receptionist/enquiry/inpatient");
        renderInpatientTable(inpatientsCache);
    } catch (err) {
        showToast(err.message, "error");
    }
}

function searchInpatients(query) {
    const q = (query || "").toLowerCase().trim();
    if (!q) {
        renderInpatientTable(inpatientsCache);
        return;
    }
    const filtered = inpatientsCache.filter(i =>
        i.patient_name.toLowerCase().includes(q) ||
        i.mrn.toLowerCase().includes(q) ||
        i.ward_name.toLowerCase().includes(q) ||
        i.room_number.toLowerCase().includes(q)
    );
    renderInpatientTable(filtered);
}

function renderInpatientTable(inpatients) {
    const tbody = document.getElementById("inpatient-table-body");
    if (!inpatients || !inpatients.length) {
        tbody.innerHTML = `<tr><td colspan="11" style="text-align:center;padding:24px;color:#64748b;">No admitted inpatients found.</td></tr>`;
        return;
    }

    tbody.innerHTML = inpatients.map(i => `
        <tr>
            <td><strong>${i.admission_number}</strong></td>
            <td><strong>${i.patient_name}</strong></td>
            <td><span style="color:#1e40af;font-weight:600;">${i.mrn}</span></td>
            <td>${i.ward_name}</td>
            <td>${i.floor_number}</td>
            <td><strong style="color:#059669;">${i.room_number}</strong></td>
            <td><span class="badge-opd">${i.bed_number}</span></td>
            <td>${i.attending_doctor}</td>
            <td>${new Date(i.admission_date).toLocaleDateString()}</td>
            <td><span class="badge badge-active">${i.admission_status}</span></td>
            <td>
                <button class="btn-sm btn-primary" onclick="openVisitorPassModalForPatient('${i.patient_name}', '${i.mrn}', '${i.ward_name} - ${i.room_number}')">
                    🪪 Visitor Pass
                </button>
            </td>
        </tr>
    `).join("");
}

function openVisitorPassModalForPatient(patientName, mrn, wardRoom) {
    navigateTo("visitors");
    document.getElementById("vp-patient").value = `${patientName} (${mrn})`;
    document.getElementById("vp-ward").value = wardRoom;
}

// ============ 7. VISITOR PASS MANAGEMENT ============
async function loadVisitorPasses() {
    try {
        const passes = await get("/receptionist/visitors/today");
        const tbody = document.getElementById("visitor-passes-body");
        if (!passes || !passes.length) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:20px;color:#64748b;">No visitor passes issued today.</td></tr>`;
            return;
        }

        tbody.innerHTML = passes.map(vp => `
            <tr>
                <td><strong style="color:#1e40af;">${vp.pass_number}</strong></td>
                <td><strong>${vp.visitor_name}</strong><br><small style="color:#64748b;">${vp.visitor_phone}</small></td>
                <td>${vp.patient_name}</td>
                <td>${vp.ward_or_room}</td>
                <td>${new Date(vp.valid_until).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</td>
                <td><span class="badge badge-active">${vp.status}</span></td>
            </tr>
        `).join("");
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function issueVisitorPass(e) {
    e.preventDefault();
    const form = document.getElementById("visitor-pass-form");
    const fd = new FormData(form);

    const payload = {
        patient_mrn_or_name: fd.get("patient_mrn_or_name"),
        visitor_name: fd.get("visitor_name"),
        visitor_phone: fd.get("visitor_phone"),
        relationship: fd.get("relationship"),
        id_proof_number: fd.get("id_proof_number") || null,
        ward_or_room: fd.get("ward_or_room") || "General Inpatient Ward",
        valid_hours: parseInt(fd.get("valid_hours") || 4)
    };

    try {
        const vp = await post("/receptionist/visitors/issue-pass", payload);
        showToast(`Visitor Badge ${vp.pass_number} issued for ${vp.visitor_name}!`);
        form.reset();
        loadVisitorPasses();
    } catch (err) {
        showToast(err.message, "error");
    }
}

// Initial load only after server-side JWT role validation.
async function initReceptionistPortal() {
    let me;
    try {
        me = await get("/auth/me");
    } catch (error) {
        localStorage.clear();
        window.location.replace("/");
        return;
    }
    if (!me.roles.some(r => ["receptionist","admin","super_admin"].includes(r))) {
        document.documentElement.style.display = "";
        document.body.innerHTML = '<main><h1>403 · Access denied</h1><p>This account cannot access Reception.</p><a href="/">Choose another portal</a></main>';
        return;
    }
    document.documentElement.style.display = "";
    try {
        await loadDashboard();
    } catch (error) {
        showToast(error.message || "Unable to load the dashboard", "error");
    }
}

function dashboardEscape(value) {
    return String(value ?? "-").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[char]);
}

async function openDashboardDetails(metric) {
    const body = document.getElementById("recent-activity-list");
    const section = body.closest(".card");
    const title = section.querySelector("h3");
    let reset = document.getElementById("activity-stream-reset");
    if (!reset) {
        reset = document.createElement("button");
        reset.id = "activity-stream-reset";
        reset.type = "button";
        reset.className = "btn btn-secondary";
        reset.textContent = "Show all activity";
        reset.onclick = loadDashboard;
        title.insertAdjacentElement("afterend", reset);
    }
    body.innerHTML = '<p style="padding:24px;color:#64748b;">Loading records...</p>';
    title.textContent = "🕒 Loading dashboard details...";
    section.scrollIntoView({behavior:"smooth",block:"start"});
    try {
        const detail = await get(`/receptionist/dashboard-details/${encodeURIComponent(metric)}`);
        title.textContent = `🕒 ${detail.title} · ${detail.count} record${detail.count === 1 ? "" : "s"}`;
        if (!detail.rows.length) {
            body.innerHTML = '<p style="padding:24px;text-align:center;color:#64748b;">No matching records for today.</p>';
            return;
        }
        body.innerHTML = `<div class="table-container" style="width:100%;overflow:auto"><table><thead><tr>${detail.columns.map(column => `<th>${dashboardEscape(column.label)}</th>`).join("")}</tr></thead><tbody>${detail.rows.map(row => `<tr>${detail.columns.map(column => `<td>${dashboardEscape(row[column.key])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
    } catch (error) {
        body.innerHTML = `<p style="padding:24px;color:#dc2626;">${dashboardEscape(error.message)}</p>`;
    }
}

document.querySelectorAll("[data-dashboard-metric]").forEach(card => {
    card.addEventListener("click", () => openDashboardDetails(card.dataset.dashboardMetric));
});
initReceptionistPortal();
