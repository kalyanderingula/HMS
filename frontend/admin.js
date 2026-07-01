const API = "http://localhost:8000/api/v1";

// Auth check
(function checkAuth() {
    const token = localStorage.getItem("hms_token");
    const roles = localStorage.getItem("hms_roles");
    if (!token || !roles) {
        window.location.href = "/";
        return;
    }
    const parsedRoles = JSON.parse(roles);
    if (!parsedRoles.some(r => ['super_admin', 'admin', 'hr_manager', 'doctor', 'surgeon', 'nurse', 'receptionist', 'pharmacist', 'lab_technician', 'radiologist', 'accountant'].includes(r))) {
        window.location.href = "/";
        return;
    }
    const usernameEl = document.querySelector(".sidebar-header p");
    if (usernameEl) usernameEl.textContent = `${localStorage.getItem("hms_name")} (${parsedRoles.join(', ').replace(/_/g, ' ')})`;
})();

function logout() {
    localStorage.clear();
    window.location.href = "/";
}

let departmentsCache = [];
let subDepartmentsCache = [];
let employeesCache = [];

// ============ NAVIGATION ============
document.querySelectorAll(".nav-links a").forEach(link => {
    link.addEventListener("click", (e) => {
        e.preventDefault();
        const page = link.dataset.page;
        document.querySelectorAll(".nav-links a").forEach(l => l.classList.remove("active"));
        link.classList.add("active");
        document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
        document.getElementById(`page-${page}`).classList.add("active");
        loadPage(page);
    });
});

function loadPage(page) {
    if (page === "dashboard") loadDashboard();
    if (page === "departments") { showView("dept-list-view"); loadDepartments(); }
    if (page === "sub-departments") { showView("sub-dept-list-view"); loadSubDepartments(); }
    if (page === "employees") { showView("emp-list-view"); loadEmployees(); }
    if (page === "documents") { showView("doc-search-view"); document.getElementById("doc-search-input").value = ""; document.getElementById("doc-search-results").innerHTML = ""; }
}

function showView(viewId) {
    const parent = document.getElementById(viewId).parentElement;
    parent.querySelectorAll(":scope > div").forEach(d => d.classList.add("hidden"));
    document.getElementById(viewId).classList.remove("hidden");
}

// ============ HELPERS ============
function showToast(msg, type = "success") {
    const t = document.getElementById("toast");
    t.textContent = msg;
    t.className = `toast ${type} show`;
    setTimeout(() => t.classList.remove("show"), 3000);
}

function openModal(id) {
    document.getElementById(id).classList.add("active");
    if (id === "doc-modal") populateSelect("doc-employee", employeesCache.map(e => ({ id: e.employee_id, label: `${e.employee_number} - ${e.first_name} ${e.last_name || ""}` })));
}

function closeModal(id) { document.getElementById(id).classList.remove("active"); }

async function get(url) { const r = await fetch(`${API}${url}`); return r.json(); }

async function post(url, data) {
    const r = await fetch(`${API}${url}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || "Error"); }
    return r.json();
}

async function put(url, data) {
    const r = await fetch(`${API}${url}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || "Error"); }
    return r.json();
}

async function postForm(url, formData) {
    const r = await fetch(`${API}${url}`, { method: "POST", body: formData });
    if (!r.ok) { const e = await r.json(); throw new Error(e.detail || "Error"); }
    return r.json();
}

function populateSelect(id, items, selectedVal = "") {
    const s = document.getElementById(id);
    s.innerHTML = `<option value="">Select</option>` + items.map(i => `<option value="${i.id}" ${i.id === selectedVal ? 'selected' : ''}>${i.label}</option>`).join("");
}

function formData(formId) {
    const form = document.getElementById(formId);
    const data = {};
    new FormData(form).forEach((v, k) => { data[k] = v || null; });
    return { form, data };
}

// ============ DASHBOARD ============
async function loadDashboard() {
    document.getElementById("stat-departments").textContent = departmentsCache.length;
    document.getElementById("stat-sub-departments").textContent = subDepartmentsCache.length;
    document.getElementById("stat-employees").textContent = employeesCache.length;
}

// ============ DEPARTMENTS ============
async function loadDepartments() {
    if (!departmentsCache.length) departmentsCache = await get("/departments/");
    const tbody = document.getElementById("dept-table-body");
    if (!departmentsCache.length) { tbody.innerHTML = `<tr class="empty-row"><td colspan="5">No departments found</td></tr>`; return; }
    tbody.innerHTML = departmentsCache.map(d => `
        <tr>
            <td><strong>${d.department_code}</strong></td>
            <td>${d.department_name}</td>
            <td>${d.schema_name || "-"}</td>
            <td><span class="badge ${d.is_active ? 'badge-active' : 'badge-inactive'}">${d.is_active ? 'Active' : 'Inactive'}</span></td>
            <td><button class="btn-sm btn-view" onclick="viewDepartment('${d.department_id}')">View / Edit</button></td>
        </tr>
    `).join("");
}

async function createDepartment(e) {
    e.preventDefault();
    const { form, data } = formData("dept-add-form");
    try { await post("/departments/", data); showToast("Department created!"); form.reset(); showView("dept-list-view"); loadDepartments(); }
    catch (err) { showToast(err.message, "error"); }
}

async function viewDepartment(id) {
    const d = await get(`/departments/${id}`);
    const form = document.getElementById("dept-edit-form");
    form.department_id.value = d.department_id;
    form.department_code.value = d.department_code;
    form.department_name.value = d.department_name;
    form.schema_name.value = d.schema_name || "";
    form.description.value = d.description || "";
    form.is_active.value = String(d.is_active);
    showView("dept-detail-view");
}

async function updateDepartment(e) {
    e.preventDefault();
    const form = document.getElementById("dept-edit-form");
    const id = form.department_id.value;
    const data = {
        department_name: form.department_name.value,
        schema_name: form.schema_name.value || null,
        description: form.description.value || null,
        is_active: form.is_active.value === "true",
    };
    try { await put(`/departments/${id}`, data); showToast("Department updated!"); showView("dept-list-view"); loadDepartments(); }
    catch (err) { showToast(err.message, "error"); }
}

// ============ SUB-DEPARTMENTS ============
async function loadSubDepartments() {
    if (!departmentsCache.length) departmentsCache = await get("/departments/");
    populateFilterDropdown();
    populateSelect("sub-dept-parent-add", departmentsCache.map(d => ({ id: d.department_id, label: `${d.department_code} - ${d.department_name}` })));

    const filterId = document.getElementById("filter-department").value;
    const url = filterId ? `/sub-departments/?department_id=${filterId}` : "/sub-departments/";
    subDepartmentsCache = await get(url);
    const tbody = document.getElementById("sub-dept-table-body");
    if (!subDepartmentsCache.length) { tbody.innerHTML = `<tr class="empty-row"><td colspan="5">No sub-departments found</td></tr>`; return; }
    tbody.innerHTML = subDepartmentsCache.map(s => {
        const parent = departmentsCache.find(d => d.department_id === s.department_id);
        return `
            <tr>
                <td><strong>${s.sub_department_code}</strong></td>
                <td>${s.sub_department_name}</td>
                <td>${parent ? parent.department_name : "-"}</td>
                <td><span class="badge ${s.is_active ? 'badge-active' : 'badge-inactive'}">${s.is_active ? 'Active' : 'Inactive'}</span></td>
                <td><button class="btn-sm btn-view" onclick="viewSubDepartment('${s.sub_department_id}')">View / Edit</button></td>
            </tr>`;
    }).join("");
}

function populateFilterDropdown() {
    const s = document.getElementById("filter-department");
    if (s.options.length <= 1) {
        departmentsCache.forEach(d => { s.innerHTML += `<option value="${d.department_id}">${d.department_name}</option>`; });
    }
}

async function createSubDepartment(e) {
    e.preventDefault();
    const { form, data } = formData("sub-dept-add-form");
    try { await post("/sub-departments/", data); showToast("Sub-Department created!"); form.reset(); showView("sub-dept-list-view"); loadSubDepartments(); }
    catch (err) { showToast(err.message, "error"); }
}

async function viewSubDepartment(id) {
    const s = await get(`/sub-departments/${id}`);
    const form = document.getElementById("sub-dept-edit-form");
    form.sub_department_id.value = s.sub_department_id;
    form.sub_department_code.value = s.sub_department_code;
    form.sub_department_name.value = s.sub_department_name;
    form.description.value = s.description || "";
    form.is_active.value = String(s.is_active);
    showView("sub-dept-detail-view");
}

async function updateSubDepartment(e) {
    e.preventDefault();
    const form = document.getElementById("sub-dept-edit-form");
    const id = form.sub_department_id.value;
    const data = {
        sub_department_name: form.sub_department_name.value,
        description: form.description.value || null,
        is_active: form.is_active.value === "true",
    };
    try { await put(`/sub-departments/${id}`, data); showToast("Sub-Department updated!"); showView("sub-dept-list-view"); loadSubDepartments(); }
    catch (err) { showToast(err.message, "error"); }
}

// ============ EMPLOYEES ============
async function loadEmployees() {
    if (!employeesCache.length) employeesCache = await get("/employees/");
    if (!departmentsCache.length) departmentsCache = await get("/departments/");
    if (!subDepartmentsCache.length) subDepartmentsCache = await get("/sub-departments/");
    populateEmpFilters();
    renderEmployeeTable(employeesCache);
}

function populateEmpFilters() {
    const deptSelect = document.getElementById("emp-filter-dept");
    const subDeptSelect = document.getElementById("emp-filter-sub-dept");
    if (deptSelect.options.length <= 1) {
        departmentsCache.forEach(d => { deptSelect.innerHTML += `<option value="${d.department_id}">${d.department_code} - ${d.department_name}</option>`; });
    }
    if (subDeptSelect.options.length <= 1) {
        subDepartmentsCache.forEach(s => { subDeptSelect.innerHTML += `<option value="${s.sub_department_id}">${s.sub_department_code} - ${s.sub_department_name}</option>`; });
    }
}

function searchEmployees() {
    const query = document.getElementById("emp-search-input").value.toLowerCase().trim();
    const deptFilter = document.getElementById("emp-filter-dept").value;
    const subDeptFilter = document.getElementById("emp-filter-sub-dept").value;

    let filtered = employeesCache;

    if (query) {
        filtered = filtered.filter(emp =>
            (emp.employee_number || "").toLowerCase().includes(query) ||
            (emp.first_name || "").toLowerCase().includes(query) ||
            (emp.last_name || "").toLowerCase().includes(query)
        );
    }
    if (deptFilter) {
        filtered = filtered.filter(emp => emp.department_id === deptFilter);
    }
    if (subDeptFilter) {
        filtered = filtered.filter(emp => emp.sub_department_id === subDeptFilter);
    }

    renderEmployeeTable(filtered);
}

function renderEmployeeTable(employees) {
    const tbody = document.getElementById("emp-table-body");
    if (!employees.length) { tbody.innerHTML = `<tr class="empty-row"><td colspan="6">No employees found</td></tr>`; return; }
    tbody.innerHTML = employees.map(emp => {
        const dept = departmentsCache.find(d => d.department_id === emp.department_id);
        const subDept = subDepartmentsCache.find(s => s.sub_department_id === emp.sub_department_id);
        return `
            <tr>
                <td><strong>${emp.employee_number}</strong></td>
                <td>${emp.first_name} ${emp.last_name || ""}</td>
                <td>${dept ? dept.department_name : "-"}</td>
                <td>${subDept ? subDept.sub_department_name : "-"}</td>
                <td><span class="badge badge-active">${emp.employment_status || "active"}</span></td>
                <td><button class="btn-sm btn-view" onclick="viewEmployee('${emp.employee_id}')">View / Edit</button>
                <button class="btn-sm btn-danger" onclick="deleteEmployee('${emp.employee_id}')" style="margin-left:6px">Delete</button></td>
            </tr>
        `;
    }).join("");
}

async function populateEmpDropdowns(deptVal = "", subDeptVal = "") {
    if (!departmentsCache.length) departmentsCache = await get("/departments/");
    if (!subDepartmentsCache.length) subDepartmentsCache = await get("/sub-departments/");
    populateSelect("emp-add-dept", departmentsCache.map(d => ({ id: d.department_id, label: `${d.department_code} - ${d.department_name}` })), deptVal);
    populateSelect("emp-add-sub-dept", subDepartmentsCache.map(s => ({ id: s.sub_department_id, label: `${s.sub_department_code} - ${s.sub_department_name}` })), subDeptVal);
    await loadCountriesDropdown("emp-add-country");
    // Load roles
    const roles = await get("/auth/roles");
    const roleSelect = document.getElementById("emp-add-role");
    roleSelect.innerHTML = roles.map(r => `<option value="${r.role_name}">${r.role_name.replace(/_/g, ' ').toUpperCase()}</option>`).join("");
}

async function createEmployee(e) {
    e.preventDefault();
    const form = document.getElementById("emp-add-form");
    const fd = new FormData(form);
    const data = {
        first_name: fd.get("first_name"),
        last_name: fd.get("last_name"),
        gender: fd.get("gender") || null,
        date_of_birth: fd.get("date_of_birth") || null,
        date_of_joining: fd.get("date_of_joining") || null,
        official_email: fd.get("official_email") || null,
        official_phone: fd.get("official_phone") || null,
        department_id: fd.get("department_id") || null,
        sub_department_id: fd.get("sub_department_id") || null,
        roles: Array.from(document.getElementById("emp-add-role").selectedOptions).map(o => o.value),
        profile: {
            marital_status: fd.get("marital_status") || null,
            nationality: fd.get("nationality") || null,
            blood_group: fd.get("blood_group") || null,
            emergency_contact_name: fd.get("emergency_contact_name") || null,
            emergency_contact_phone: fd.get("emergency_contact_phone") || null,
        },
        address: {
            address_line_1: fd.get("address_line_1") || null,
            address_line_2: fd.get("address_line_2") || null,
            city: fd.get("city") || null,
            state: fd.get("state") || null,
            postal_code: fd.get("postal_code") || null,
            country: fd.get("country") || null,
        },
        contact: {
            personal_phone: fd.get("personal_phone") || null,
            personal_email: fd.get("personal_email") || null,
        },
    };
    try { await post("/employees/", data); showToast("Employee created!"); form.reset(); showView("emp-list-view"); loadEmployees(); }
    catch (err) { showToast(err.message, "error"); }
}

async function deleteEmployee(id) {
    if (!confirm("Are you sure you want to delete this employee? This cannot be undone.")) return;
    try {
        const r = await fetch(`${API}/employees/${id}`, { method: "DELETE" });
        if (!r.ok) { const e = await r.json(); throw new Error(e.detail || "Error"); }
        showToast("Employee deleted!");
        employeesCache = [];
        loadEmployees();
    } catch (err) { showToast(err.message, "error"); }
}

async function viewEmployee(id) {
    const emp = await get(`/employees/${id}`);
    if (!departmentsCache.length) departmentsCache = await get("/departments/");
    if (!subDepartmentsCache.length) subDepartmentsCache = await get("/sub-departments/");

    populateSelect("emp-edit-dept", departmentsCache.map(d => ({ id: d.department_id, label: `${d.department_code} - ${d.department_name}` })), emp.department_id || "");
    populateSelect("emp-edit-sub-dept", subDepartmentsCache.map(s => ({ id: s.sub_department_id, label: `${s.sub_department_code} - ${s.sub_department_name}` })), emp.sub_department_id || "");

    const form = document.getElementById("emp-edit-form");
    form.employee_id.value = emp.employee_id;
    form.employee_number.value = emp.employee_number;
    form.first_name.value = emp.first_name || "";
    form.last_name.value = emp.last_name || "";
    form.gender.value = emp.gender || "";
    form.official_email.value = emp.official_email || "";
    form.official_phone.value = emp.official_phone || "";
    form.date_of_birth.value = emp.date_of_birth || "";
    form.date_of_joining.value = emp.date_of_joining || "";
    form.employment_status.value = emp.employment_status || "active";
    form.department_id.value = emp.department_id || "";
    form.sub_department_id.value = emp.sub_department_id || "";

    // Profile
    form.marital_status.value = emp.profile?.marital_status || "";
    form.nationality.value = emp.profile?.nationality || "";
    form.blood_group.value = emp.profile?.blood_group || "";
    form.emergency_contact_name.value = emp.profile?.emergency_contact_name || "";
    form.emergency_contact_phone.value = emp.profile?.emergency_contact_phone || "";

    // Address
    form.address_line_1.value = emp.address?.address_line_1 || "";
    form.address_line_2.value = emp.address?.address_line_2 || "";
    form.city.value = emp.address?.city || "";
    form.postal_code.value = emp.address?.postal_code || "";
    await loadCountriesDropdown("emp-edit-country", emp.address?.country || "");
    if (emp.address?.country) await loadStatesDropdown("emp-edit-state", emp.address.country, emp.address?.state || "");

    // Contact
    form.personal_phone.value = emp.contact?.personal_phone || "";
    form.personal_email.value = emp.contact?.personal_email || "";

    showView("emp-detail-view");
}

async function updateEmployee(e) {
    e.preventDefault();
    const form = document.getElementById("emp-edit-form");
    const id = form.employee_id.value;
    const fd = new FormData(form);
    const data = {
        first_name: fd.get("first_name"),
        last_name: fd.get("last_name"),
        gender: fd.get("gender") || null,
        date_of_birth: fd.get("date_of_birth") || null,
        date_of_joining: fd.get("date_of_joining") || null,
        official_email: fd.get("official_email") || null,
        official_phone: fd.get("official_phone") || null,
        employment_status: fd.get("employment_status"),
        department_id: fd.get("department_id") || null,
        sub_department_id: fd.get("sub_department_id") || null,
        profile: {
            marital_status: fd.get("marital_status") || null,
            nationality: fd.get("nationality") || null,
            blood_group: fd.get("blood_group") || null,
            emergency_contact_name: fd.get("emergency_contact_name") || null,
            emergency_contact_phone: fd.get("emergency_contact_phone") || null,
        },
        address: {
            address_line_1: fd.get("address_line_1") || null,
            address_line_2: fd.get("address_line_2") || null,
            city: fd.get("city") || null,
            state: fd.get("state") || null,
            postal_code: fd.get("postal_code") || null,
            country: fd.get("country") || null,
        },
        contact: {
            personal_phone: fd.get("personal_phone") || null,
            personal_email: fd.get("personal_email") || null,
        },
    };
    try { await put(`/employees/${id}`, data); showToast("Employee updated!"); showView("emp-list-view"); loadEmployees(); }
    catch (err) { showToast(err.message, "error"); }
}

// ============ DOCUMENTS ============
let currentDocEmployeeId = null;

async function searchEmployeeForDocs() {
    const q = document.getElementById("doc-search-input").value.trim();
    const container = document.getElementById("doc-search-results");
    if (q.length < 1) { container.innerHTML = ""; return; }

    try {
        const results = await get(`/employee-documents/search-employee?q=${encodeURIComponent(q)}`);
        if (!results.length) { container.innerHTML = `<p style="color:var(--gray-500);padding:12px;">No employees found</p>`; return; }
        container.innerHTML = results.map(emp => `
            <div class="search-result-item" onclick="selectEmployeeForDocs('${emp.employee_id}', '${emp.employee_number}', '${emp.first_name} ${emp.last_name || ""}')">
                <div class="emp-info">
                    <span class="emp-name">${emp.first_name} ${emp.last_name || ""}</span>
                    <span class="emp-meta">${emp.employee_number} | ${emp.department_name || "N/A"} | ${emp.sub_department_name || "N/A"}</span>
                </div>
                <button class="btn-sm btn-view">View Docs</button>
            </div>
        `).join("");
    } catch (e) { container.innerHTML = ""; }
}

async function selectEmployeeForDocs(employeeId, empNumber, empName) {
    currentDocEmployeeId = employeeId;
    document.getElementById("doc-employee-title").textContent = `Documents - ${empName} (${empNumber})`;
    document.getElementById("doc-upload-employee-id").value = employeeId;
    await loadEmployeeDocs(employeeId);
    showView("doc-employee-view");
}

async function loadEmployeeDocs(employeeId) {
    const docs = await get(`/employee-documents/by-employee/${employeeId}`);
    const tbody = document.getElementById("doc-table-body");
    if (!docs.length) { tbody.innerHTML = `<tr class="empty-row"><td colspan="4">No documents uploaded yet</td></tr>`; return; }
    tbody.innerHTML = docs.map(doc => `
        <tr>
            <td><strong>${doc.document_name || "-"}</strong></td>
            <td>${doc.document_type || "-"}</td>
            <td>${doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : "-"}</td>
            <td>
                <button class="btn-sm btn-view" onclick="editDocument('${doc.employee_document_id}', '${doc.document_name}', '${doc.document_type}')">Edit</button>
                <button class="btn-sm btn-danger" onclick="deleteDocument('${doc.employee_document_id}')" style="margin-left:6px">Delete</button>
            </td>
        </tr>
    `).join("");
}

function addDocumentRow() {
    const container = document.getElementById("doc-fields-container");
    const row = document.createElement("div");
    row.className = "doc-field-row";
    row.innerHTML = `
        <div style="display:flex;justify-content:flex-end;"><button type="button" class="btn-sm btn-danger" onclick="this.closest('.doc-field-row').remove()">✕ Remove</button></div>
        <div class="form-row">
            <div class="form-group"><label>Document Name *</label><input type="text" name="document_names" required></div>
            <div class="form-group"><label>Type *</label>
                <select name="document_types" required>
                    <option value="">Select</option>
                    <option value="ID Proof">ID Proof</option>
                    <option value="Address Proof">Address Proof</option>
                    <option value="Educational">Educational</option>
                    <option value="Experience">Experience</option>
                    <option value="Medical">Medical</option>
                    <option value="License">License</option>
                    <option value="Other">Other</option>
                </select>
            </div>
        </div>
        <div class="form-group"><label>File *</label><input type="file" name="files" required></div>
    `;
    container.appendChild(row);
}

async function uploadDocuments(e) {
    e.preventDefault();
    const employeeId = document.getElementById("doc-upload-employee-id").value;
    const form = document.getElementById("doc-upload-form");
    const names = form.querySelectorAll('[name="document_names"]');
    const types = form.querySelectorAll('[name="document_types"]');
    const fileInputs = form.querySelectorAll('[name="files"]');

    const fd = new FormData();
    for (let i = 0; i < names.length; i++) {
        fd.append("document_names", names[i].value);
        fd.append("document_types", types[i].value);
        fd.append("files", fileInputs[i].files[0]);
    }

    try {
        await postForm(`/employee-documents/upload/${employeeId}`, fd);
        showToast("Documents uploaded!");
        closeModal("doc-upload-modal");
        // Reset form
        document.getElementById("doc-fields-container").innerHTML = `
            <div class="doc-field-row">
                <div class="form-row">
                    <div class="form-group"><label>Document Name *</label><input type="text" name="document_names" required></div>
                    <div class="form-group"><label>Type *</label>
                        <select name="document_types" required>
                            <option value="">Select</option>
                            <option value="ID Proof">ID Proof</option>
                            <option value="Address Proof">Address Proof</option>
                            <option value="Educational">Educational</option>
                            <option value="Experience">Experience</option>
                            <option value="Medical">Medical</option>
                            <option value="License">License</option>
                            <option value="Other">Other</option>
                        </select>
                    </div>
                </div>
                <div class="form-group"><label>File *</label><input type="file" name="files" required></div>
            </div>
        `;
        loadEmployeeDocs(employeeId);
    } catch (err) { showToast(err.message, "error"); }
}

function editDocument(docId, name, type) {
    const form = document.getElementById("doc-edit-form");
    form.document_id.value = docId;
    form.document_name.value = name;
    form.document_type.value = type;
    openModal("doc-edit-modal");
}

async function updateDocument(e) {
    e.preventDefault();
    const form = document.getElementById("doc-edit-form");
    const id = form.document_id.value;
    const data = {
        document_name: form.document_name.value,
        document_type: form.document_type.value,
    };
    try {
        await put(`/employee-documents/${id}`, data);
        showToast("Document updated!");
        closeModal("doc-edit-modal");
        loadEmployeeDocs(currentDocEmployeeId);
    } catch (err) { showToast(err.message, "error"); }
}

async function deleteDocument(docId) {
    if (!confirm("Are you sure you want to delete this document?")) return;
    try {
        await fetch(`${API}/employee-documents/${docId}`, { method: "DELETE" });
        showToast("Document deleted!");
        loadEmployeeDocs(currentDocEmployeeId);
    } catch (err) { showToast(err.message, "error"); }
}

// ============ COUNTRIES & STATES ============
let countriesCache = [];

async function loadCountriesDropdown(selectId, selectedVal = "") {
    if (!countriesCache.length) countriesCache = await get("/locations/countries");
    const s = document.getElementById(selectId);
    s.innerHTML = `<option value="">Select Country</option>` + countriesCache.map(c => `<option value="${c.country_name}" ${c.country_name === selectedVal ? 'selected' : ''}>${c.country_name}</option>`).join("");
}

async function loadStatesDropdown(selectId, countryName, selectedVal = "") {
    const s = document.getElementById(selectId);
    s.innerHTML = `<option value="">Select State</option>`;
    if (!countryName) return;
    const country = countriesCache.find(c => c.country_name === countryName);
    if (!country) return;
    const states = await get(`/locations/states?country_id=${country.country_id}`);
    s.innerHTML = `<option value="">Select State</option>` + states.map(st => `<option value="${st.state_name}" ${st.state_name === selectedVal ? 'selected' : ''}>${st.state_name}</option>`).join("");
}

// ============ INIT ============
async function init() {
    try {
        departmentsCache = await get("/departments/");
        subDepartmentsCache = await get("/sub-departments/");
        employeesCache = await get("/employees/");
        document.getElementById("stat-departments").textContent = departmentsCache.length;
        document.getElementById("stat-sub-departments").textContent = subDepartmentsCache.length;
        document.getElementById("stat-employees").textContent = employeesCache.length;
    } catch (e) { console.error(e); }
}

init();
