const API = "http://localhost:8000/api/v1";

const ROLE_META = {
    super_admin:          { label: "Super Admin",        icon: "🛡️",  page: "/admin" },
    admin:                { label: "Admin",               icon: "⚙️",  page: "/admin" },
    hr_manager:           { label: "HR Manager",          icon: "👥",  page: "/admin" },
    doctor:               { label: "Doctor",              icon: "🩺",  page: "/doctor" },
    surgeon:              { label: "Surgeon",             icon: "🔬",  page: "/doctor" },
    telemedicine_doctor:  { label: "Telemedicine Doctor", icon: "💻",  page: "/doctor" },
    nurse:                { label: "Nurse",               icon: "💉",  page: "/admin" },
    icu_staff:            { label: "ICU Staff",           icon: "🏥",  page: "/admin" },
    receptionist:         { label: "Receptionist",        icon: "🗂️",  page: "/admin" },
    pharmacist:           { label: "Pharmacist",          icon: "💊",  page: "/admin" },
    lab_technician:       { label: "Lab Technician",      icon: "🧪",  page: "/admin" },
    radiologist:          { label: "Radiologist",         icon: "🩻",  page: "/admin" },
    accountant:           { label: "Accountant",          icon: "💰",  page: "/admin" },
    insurance_officer:    { label: "Insurance Officer",   icon: "📋",  page: "/admin" },
    ambulance_staff:      { label: "Ambulance Staff",     icon: "🚑",  page: "/admin" },
    blood_bank_technician:{ label: "Blood Bank Tech",     icon: "🩸",  page: "/admin" },
    dietitian:            { label: "Dietitian",           icon: "🥗",  page: "/admin" },
    physiotherapist:      { label: "Physiotherapist",     icon: "🏋️",  page: "/admin" },
    housekeeping_staff:   { label: "Housekeeping",        icon: "🧹",  page: "/admin" },
    inventory_manager:    { label: "Inventory Manager",   icon: "📦",  page: "/admin" },
    mortuary_staff:       { label: "Mortuary Staff",      icon: "🏛️",  page: "/admin" },
    crm_manager:          { label: "CRM Manager",         icon: "📊",  page: "/admin" },
    emergency_staff:      { label: "Emergency Staff",     icon: "🚨",  page: "/admin" },
    visitor_desk:         { label: "Visitor Desk",        icon: "🪪",  page: "/admin" },
};

// Check if already logged in
(function checkAuth() {
    const token = localStorage.getItem("hms_token");
    const roles = localStorage.getItem("hms_roles");
    if (token && roles) {
        showRoleSelection(JSON.parse(roles));
    }
})();

function showError(msg) {
    const el = document.getElementById("error-msg");
    el.textContent = msg;
    el.classList.remove("hidden");
}

function hideError() {
    document.getElementById("error-msg").classList.add("hidden");
}

async function handleLogin(e) {
    e.preventDefault();
    hideError();
    const form = e.target;
    const data = { username: form.username.value, password: form.password.value };

    try {
        const res = await fetch(`${API}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });

        if (!res.ok) {
            const err = await res.json();
            showError(err.detail || "Login failed");
            return;
        }

        const result = await res.json();
        localStorage.setItem("hms_token", result.token);
        localStorage.setItem("hms_roles", JSON.stringify(result.roles));
        localStorage.setItem("hms_username", result.employee_number);
        localStorage.setItem("hms_name", result.name);
        localStorage.setItem("hms_user_id", result.user_id);
        localStorage.setItem("hms_employee_id", result.employee_id || "");
        localStorage.setItem("hms_must_change_password", result.must_change_password ? "true" : "false");

        showRoleSelection(result.roles);
    } catch (err) {
        showError("Connection error. Is the server running?");
    }
}

function showRoleSelection(roles) {
    // If only one role, redirect directly
    if (roles.length === 1) {
        goToRole(roles[0]);
        return;
    }

    document.getElementById("login-form-container").classList.add("hidden");
    hideError();

    const container = document.getElementById("role-select-container");
    const cardsEl = document.getElementById("role-cards");

    cardsEl.innerHTML = roles.map(role => {
        const meta = ROLE_META[role] || { label: role, icon: "👤", page: "/admin" };
        return `
            <div class="role-card" onclick="goToRole('${role}')">
                <div class="role-icon">${meta.icon}</div>
                <div class="role-info">
                    <strong>${meta.label}</strong>
                    <span>Click to enter as ${meta.label}</span>
                </div>
            </div>
        `;
    }).join("");

    container.classList.remove("hidden");
}

function goToRole(role) {
    const meta = ROLE_META[role] || { page: "/admin" };
    localStorage.setItem("hms_active_role", role);
    window.location.href = meta.page;
}
