const API = "/api/v1";
document.documentElement.style.display = "none";

const token = localStorage.getItem("hms_token");
const roles = localStorage.getItem("hms_roles");
const employeeId = localStorage.getItem("hms_employee_id");
const username = localStorage.getItem("hms_username");

if (!token || !roles) { window.location.replace("/"); }

document.getElementById("doc-sidebar-name").textContent = localStorage.getItem("hms_name") || "Doctor";

if (localStorage.getItem("hms_must_change_password") === "true") {
    document.getElementById("password-overlay").style.display = "flex";
}

function logout() { localStorage.clear(); window.location.href = "/"; }

function showToast(msg, type = "success") {
    const t = document.getElementById("toast");
    t.textContent = msg;
    t.className = `toast ${type} show`;
    setTimeout(() => t.classList.remove("show"), 3000);
}

async function api(url, method = "GET", body = null) {
    const opts = { method, headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` } };
    if (body) opts.body = JSON.stringify(body);
    const r = await fetch(`${API}${url}`, opts);
    if (!r.ok) {
        const text = await r.text();
        let msg = "Error";
        try { const e = JSON.parse(text); msg = e.detail || msg; } catch(_) { msg = text; }
        throw new Error(msg);
    }
    if (r.status === 204) return null;
    return r.json();
}

// Password Change
async function changePassword(e) {
    e.preventDefault();
    const form = e.target;
    const current = form.current_password.value;
    const newPwd = form.new_password.value;
    const confirm = form.confirm_password.value;
    const errEl = document.getElementById("pwd-error");

    if (newPwd !== confirm) { errEl.textContent = "Passwords do not match"; errEl.style.display = "block"; return; }
    if (newPwd.length < 8) { errEl.textContent = "Min 8 characters"; errEl.style.display = "block"; return; }

    try {
        await api("/auth/change-password", "POST", { username, current_password: current, new_password: newPwd });
        localStorage.setItem("hms_must_change_password", "false");
        document.getElementById("password-overlay").style.display = "none";
        showToast("Password changed successfully!");
        loadProfile();
    } catch (err) { errEl.textContent = err.message; errEl.style.display = "block"; }
}

// Load entire profile page
async function loadProfile() {
    const container = document.getElementById("profile-content");
    try {
        const [profileData, docTypes, specializations, languages] = await Promise.all([
            api("/doctor/my-profile/current"),
            api("/doctor/document-types"),
            api("/doctor/specializations"),
            api("/doctor/languages"),
        ]);

        // Store for later use
        window._docTypes = docTypes;
        window._specializations = specializations;
        window._languages = languages;
        window._doctorId = profileData.doctor.doctor_id;

        container.innerHTML = renderFullProfile(profileData);
    } catch (err) {
        container.innerHTML = `<p style="color:#dc2626;">${err.message}</p>`;
    }
}



function renderFullProfile(data) {
    const d = data.doctor;
    const p = data.profile;
    const emp = data.employee_details || {};
    const ep = emp.profile || {};
    const ea = emp.address || {};
    const ec = emp.contact || {};

    return `
        <!-- Basic Info (read-only from admin) -->
        <div class="section-card">
            <h3>Basic Info</h3>
            <div class="info-grid">
                <div class="info-item"><label>Doctor Code</label><span>${d.doctor_code}</span></div>
                <div class="info-item"><label>Name</label><span>Dr. ${d.first_name} ${d.middle_name || ''} ${d.last_name}</span></div>
                <div class="info-item"><label>Email</label><span>${d.email || '-'}</span></div>
                <div class="info-item"><label>Phone</label><span>${d.phone || '-'}</span></div>
                <div class="info-item"><label>Primary Specialization</label><span>${d.primary_specialization || '-'}</span></div>
                <div class="info-item"><label>Experience</label><span>${d.consultation_experience_years ? d.consultation_experience_years + ' years' : '-'}</span></div>
                <div class="info-item"><label>Joining Date</label><span>${d.joining_date || '-'}</span></div>
            </div>
        </div>

        <!-- Personal Info -->
        <div class="section-card">
            <h3>Personal Information</h3>
            <form id="personal-info-form" onsubmit="savePersonalInfo(event)">
                <div class="form-row">
                    <div class="form-group"><label>Marital Status</label>
                        <select name="marital_status"><option value="">Select</option><option value="Single" ${ep.marital_status==='Single'?'selected':''}>Single</option><option value="Married" ${ep.marital_status==='Married'?'selected':''}>Married</option><option value="Divorced" ${ep.marital_status==='Divorced'?'selected':''}>Divorced</option><option value="Widowed" ${ep.marital_status==='Widowed'?'selected':''}>Widowed</option></select>
                    </div>
                    <div class="form-group"><label>Nationality</label><input type="text" name="nationality" value="${ep.nationality || ''}"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Blood Group</label>
                        <select name="blood_group"><option value="">Select</option><option value="A+" ${ep.blood_group==='A+'?'selected':''}>A+</option><option value="A-" ${ep.blood_group==='A-'?'selected':''}>A-</option><option value="B+" ${ep.blood_group==='B+'?'selected':''}>B+</option><option value="B-" ${ep.blood_group==='B-'?'selected':''}>B-</option><option value="O+" ${ep.blood_group==='O+'?'selected':''}>O+</option><option value="O-" ${ep.blood_group==='O-'?'selected':''}>O-</option><option value="AB+" ${ep.blood_group==='AB+'?'selected':''}>AB+</option><option value="AB-" ${ep.blood_group==='AB-'?'selected':''}>AB-</option></select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Emergency Contact Name</label><input type="text" name="emergency_contact_name" value="${ep.emergency_contact_name || ''}"></div>
                    <div class="form-group"><label>Emergency Contact Phone</label><input type="text" name="emergency_contact_phone" value="${ep.emergency_contact_phone || ''}"></div>
                </div>
                <h4 style="margin:16px 0 8px;color:#334155;">Address</h4>
                <div class="form-row">
                    <div class="form-group"><label>Address Line 1</label><input type="text" name="address_line_1" value="${ea.address_line_1 || ''}"></div>
                    <div class="form-group"><label>Address Line 2</label><input type="text" name="address_line_2" value="${ea.address_line_2 || ''}"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>City</label><input type="text" name="city" value="${ea.city || ''}"></div>
                    <div class="form-group"><label>State</label><input type="text" name="state" value="${ea.state || ''}"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Country</label><input type="text" name="country" value="${ea.country || ''}"></div>
                    <div class="form-group"><label>Postal Code</label><input type="text" name="postal_code" value="${ea.postal_code || ''}"></div>
                </div>
                <h4 style="margin:16px 0 8px;color:#334155;">Personal Contact</h4>
                <div class="form-row">
                    <div class="form-group"><label>Personal Phone</label><input type="text" name="personal_phone" value="${ec.personal_phone || ''}"></div>
                    <div class="form-group"><label>Personal Email</label><input type="email" name="personal_email" value="${ec.personal_email || ''}"></div>
                </div>
                <button type="submit" class="btn btn-primary" style="width:auto;margin-top:12px;">Save Personal Info</button>
            </form>
        </div>

        <!-- Doctor Profile -->
        <div class="section-card">
            <h3>Doctor Profile</h3>
            <form id="doctor-profile-form" onsubmit="saveDoctorProfile(event)">
                <div class="form-row">
                    <div class="form-group"><label>Religion</label><input type="text" name="religion" value="${p.religion || ''}"></div>
                    <div class="form-group"><label>LinkedIn URL</label><input type="url" name="linkedin_url" value="${p.linkedin_url || ''}"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Website</label><input type="url" name="website_url" value="${p.website_url || ''}"></div>
                    <div class="form-group"></div>
                </div>
                <div class="form-group"><label>Biography</label><textarea name="biography" rows="3" style="width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:8px;">${p.biography || ''}</textarea></div>
                <button type="submit" class="btn btn-primary" style="width:auto;">Save Doctor Profile</button>
            </form>
        </div>

        <!-- Qualifications -->
        <div class="section-card">
            <h3>Qualifications</h3>
            <div id="qualifications-list">${renderQualifications(data.qualifications)}</div>
            <div class="add-section">
                <form id="qual-form" onsubmit="addQualification(event)">
                    <div class="form-row">
                        <div class="form-group"><label>Qualification *</label><input type="text" name="qualification_name" required></div>
                        <div class="form-group"><label>Institution</label><input type="text" name="institution_name"></div>
                    </div>
                    <div class="form-row">
                        <div class="form-group"><label>University</label><input type="text" name="university_name"></div>
                        <div class="form-group"><label>Country</label><input type="text" name="country"></div>
                    </div>
                    <div class="form-row">
                        <div class="form-group"><label>Year</label><input type="number" name="graduation_year" min="1950" max="2030"></div>
                        <div class="form-group"><label>Certificate No.</label><input type="text" name="certificate_number"></div>
                    </div>
                    <button type="submit" class="btn btn-primary" style="width:auto;">+ Add Qualification</button>
                </form>
            </div>
        </div>

        <!-- Licenses -->
        <div class="section-card">
            <h3>Medical Licenses</h3>
            <div id="licenses-list">${renderLicenses(data.licenses)}</div>
            <div class="add-section">
                <form id="license-form" onsubmit="addLicense(event)">
                    <div class="form-row">
                        <div class="form-group"><label>License Number *</label><input type="text" name="license_number" required></div>
                        <div class="form-group"><label>Issuing Authority</label><input type="text" name="issuing_authority"></div>
                    </div>
                    <div class="form-row">
                        <div class="form-group"><label>Issue Date</label><input type="date" name="issue_date"></div>
                        <div class="form-group"><label>Expiry Date</label><input type="date" name="expiry_date"></div>
                    </div>
                    <button type="submit" class="btn btn-primary" style="width:auto;">+ Add License</button>
                </form>
            </div>
        </div>

        <!-- Experience -->
        <div class="section-card">
            <h3>Work Experience</h3>
            <div id="experience-list">${renderExperiences(data.experiences)}</div>
            <div class="add-section">
                <form id="exp-form" onsubmit="addExperience(event)">
                    <div class="form-row">
                        <div class="form-group"><label>Hospital *</label><input type="text" name="hospital_name" required></div>
                        <div class="form-group"><label>Designation</label><input type="text" name="designation"></div>
                    </div>
                    <div class="form-row">
                        <div class="form-group"><label>Department</label><input type="text" name="department"></div>
                        <div class="form-group"><label>Responsibilities</label><input type="text" name="responsibilities"></div>
                    </div>
                    <div class="form-row">
                        <div class="form-group"><label>Start Date</label><input type="date" name="start_date"></div>
                        <div class="form-group"><label>End Date</label><input type="date" name="end_date"></div>
                    </div>
                    <button type="submit" class="btn btn-primary" style="width:auto;">+ Add Experience</button>
                </form>
            </div>
        </div>

        <!-- Documents -->
        <div class="section-card">
            <h3>Documents</h3>
            <div id="documents-list">${renderDocuments(data.documents || [])}</div>
            <div class="add-section">
                <form id="doc-upload-form" onsubmit="uploadDoc(event)" enctype="multipart/form-data">
                    <div class="form-row">
                        <div class="form-group"><label>Document Type *</label><select name="document_type_id" required><option value="">Select</option>${window._docTypes.map(t => `<option value="${t.document_type_id}">${t.document_type_name}</option>`).join('')}</select></div>
                        <div class="form-group"><label>File *</label><input type="file" name="file" required></div>
                    </div>
                    <button type="submit" class="btn btn-primary" style="width:auto;">Upload Document</button>
                </form>
            </div>
        </div>

        <!-- Availability -->
        <div class="section-card">
            <h3>Weekly Availability</h3>
            <div id="availability-list">${renderAvailability(data.availability)}</div>
            <div class="add-section">
                <form id="avail-form" onsubmit="addAvailability(event)">
                    <div class="form-row">
                        <div class="form-group"><label>Day *</label><select name="available_day" required><option value="">Select</option><option>Monday</option><option>Tuesday</option><option>Wednesday</option><option>Thursday</option><option>Friday</option><option>Saturday</option><option>Sunday</option></select></div>
                        <div class="form-group"><label>Type</label><select name="consultation_type"><option value="in_person">In Person</option><option value="telemedicine">Telemedicine</option><option value="both">Both</option></select></div>
                    </div>
                    <div class="form-row">
                        <div class="form-group"><label>Start Time *</label><input type="time" name="start_time" required></div>
                        <div class="form-group"><label>End Time *</label><input type="time" name="end_time" required></div>
                    </div>
                    <div class="form-row">
                        <div class="form-group"><label>Max Patients/Slot</label><input type="number" name="max_patients_per_slot" value="10"></div>
                        <div class="form-group"></div>
                    </div>
                    <button type="submit" class="btn btn-primary" style="width:auto;">+ Add Slot</button>
                </form>
            </div>
        </div>

        <!-- Consultation Fees -->
        <div class="section-card">
            <h3>Consultation Fees</h3>
            <div id="fees-list">${renderFees(data.consultation_fees)}</div>
            <div class="add-section">
                <form id="fee-form" onsubmit="addFee(event)">
                    <div class="form-row">
                        <div class="form-group"><label>Type *</label><select name="consultation_type" required><option value="">Select</option><option>General Consultation</option><option>Follow-up</option><option>Telemedicine</option><option>Emergency</option><option>Specialist</option></select></div>
                        <div class="form-group"><label>Fee Amount *</label><input type="number" name="fee_amount" step="0.01" required></div>
                    </div>
                    <div class="form-row">
                        <div class="form-group"><label>Currency</label><input type="text" name="currency" value="INR"></div>
                        <div class="form-group"></div>
                    </div>
                    <button type="submit" class="btn btn-primary" style="width:auto;">+ Add Fee</button>
                </form>
            </div>
        </div>
    `;
}

// Render helpers
function renderQualifications(list) {
    if (!list || !list.length) return '<p style="color:#64748b;">No qualifications added.</p>';
    return list.map(q => `<div class="doc-item"><div><strong>${q.qualification_name}</strong><br><small>${q.institution_name || ''} ${q.graduation_year ? '(' + q.graduation_year + ')' : ''} ${q.country ? '- ' + q.country : ''}</small></div><button class="btn-sm btn-danger" onclick="deleteItem('qualifications','${q.qualification_id}')">Delete</button></div>`).join('');
}

function renderLicenses(list) {
    if (!list || !list.length) return '<p style="color:#64748b;">No licenses added.</p>';
    return list.map(l => `<div class="doc-item"><div><strong>${l.license_number}</strong><br><small>${l.issuing_authority || ''} | Expires: ${l.expiry_date || 'N/A'}</small></div><button class="btn-sm btn-danger" onclick="deleteItem('licenses','${l.license_id}')">Delete</button></div>`).join('');
}

function renderExperiences(list) {
    if (!list || !list.length) return '<p style="color:#64748b;">No experience added.</p>';
    return list.map(e => `<div class="doc-item"><div><strong>${e.hospital_name}</strong><br><small>${e.designation || ''} | ${e.department || ''} | ${e.start_date || ''} - ${e.end_date || 'Present'}</small></div><button class="btn-sm btn-danger" onclick="deleteItem('experiences','${e.experience_id}')">Delete</button></div>`).join('');
}

function renderDocuments(list) {
    if (!list || !list.length) return '<p style="color:#64748b;">No documents uploaded.</p>';
    return list.map(d => `<div class="doc-item"><div><strong>${d.file_name}</strong><br><small>${d.document_type || 'Unknown'} | ${d.file_size ? Math.round(d.file_size / 1024) + ' KB' : ''}</small></div><button class="btn-sm btn-danger" onclick="deleteDoc('${d.document_id}')">Delete</button></div>`).join('');
}

function renderAvailability(list) {
    if (!list || !list.length) return '<p style="color:#64748b;">No availability set.</p>';
    return list.map(a => `<div class="doc-item"><div><strong>${a.available_day}</strong> ${a.start_time} - ${a.end_time}<br><small>${a.consultation_type || ''} | Max: ${a.max_patients_per_slot || '-'}</small></div><button class="btn-sm btn-danger" onclick="deleteAvail('${a.availability_id}')">Delete</button></div>`).join('');
}

function renderFees(list) {
    if (!list || !list.length) return '<p style="color:#64748b;">No fees set.</p>';
    return list.map(f => `<div class="doc-item"><div><strong>${f.consultation_type}</strong> - ${f.currency || 'INR'} ${f.fee_amount}</div><button class="btn-sm btn-danger" onclick="deleteFee('${f.fee_id}')">Delete</button></div>`).join('');
}

// Save personal info (updates employee record)
async function savePersonalInfo(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = {
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
            country: fd.get("country") || null,
            postal_code: fd.get("postal_code") || null,
        },
        contact: {
            personal_phone: fd.get("personal_phone") || null,
            personal_email: fd.get("personal_email") || null,
        },
    };
    try {
        await api(`/employees/${employeeId}`, "PUT", data);
        showToast("Personal info saved!");
    } catch (err) { showToast(err.message, "error"); }
}

// Save doctor profile
async function saveDoctorProfile(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = { biography: fd.get("biography") || null, religion: fd.get("religion") || null, linkedin_url: fd.get("linkedin_url") || null, website_url: fd.get("website_url") || null };
    try { await api(`/doctor/profile/${employeeId}`, "PUT", data); showToast("Doctor profile saved!"); }
    catch (err) { showToast(err.message, "error"); }
}

// Add qualification
async function addQualification(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = Object.fromEntries([...fd.entries()].map(([k, v]) => [k, v || null]));
    if (data.graduation_year) data.graduation_year = parseInt(data.graduation_year);
    try { await api(`/doctor/qualifications/${employeeId}`, "POST", data); showToast("Added!"); e.target.reset(); loadProfile(); }
    catch (err) { showToast(err.message, "error"); }
}

// Add license
async function addLicense(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = Object.fromEntries([...fd.entries()].map(([k, v]) => [k, v || null]));
    try { await api(`/doctor/licenses/${employeeId}`, "POST", data); showToast("Added!"); e.target.reset(); loadProfile(); }
    catch (err) { showToast(err.message, "error"); }
}

// Add experience
async function addExperience(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = Object.fromEntries([...fd.entries()].map(([k, v]) => [k, v || null]));
    try { await api(`/doctor/experiences/${employeeId}`, "POST", data); showToast("Added!"); e.target.reset(); loadProfile(); }
    catch (err) { showToast(err.message, "error"); }
}

// Upload document
async function uploadDoc(e) {
    e.preventDefault();
    const form = e.target;
    const fd = new FormData(form);
    try {
        const r = await fetch(`${API}/doctor/documents/${employeeId}`, { method: "POST", headers:{"Authorization":`Bearer ${token}`}, body: fd });
        if (!r.ok) { const err = await r.json(); throw new Error(err.detail || "Upload failed"); }
        showToast("Uploaded!"); form.reset(); loadProfile();
    } catch (err) { showToast(err.message, "error"); }
}

// Add availability
async function addAvailability(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = Object.fromEntries([...fd.entries()].map(([k, v]) => [k, v || null]));
    if (data.max_patients_per_slot) data.max_patients_per_slot = parseInt(data.max_patients_per_slot);
    try { await api(`/doctor/availability/${employeeId}`, "POST", data); showToast("Added!"); e.target.reset(); loadProfile(); }
    catch (err) { showToast(err.message, "error"); }
}

// Add fee
async function addFee(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = Object.fromEntries([...fd.entries()].map(([k, v]) => [k, v || null]));
    if (data.fee_amount) data.fee_amount = parseFloat(data.fee_amount);
    try { await api(`/doctor/consultation-fees/${employeeId}`, "POST", data); showToast("Added!"); e.target.reset(); loadProfile(); }
    catch (err) { showToast(err.message, "error"); }
}

// Deletes
async function deleteItem(type, id) {
    if (!confirm("Delete?")) return;
    try { await api(`/doctor/${type}/${id}`, "DELETE"); showToast("Deleted!"); loadProfile(); }
    catch (err) { showToast(err.message, "error"); }
}

async function deleteDoc(id) {
    if (!confirm("Delete?")) return;
    try { await api(`/doctor/documents/${id}`, "DELETE"); showToast("Deleted!"); loadProfile(); }
    catch (err) { showToast(err.message, "error"); }
}

async function deleteAvail(id) {
    if (!confirm("Delete?")) return;
    try { await api(`/doctor/availability/${id}`, "DELETE"); showToast("Deleted!"); loadProfile(); }
    catch (err) { showToast(err.message, "error"); }
}

async function deleteFee(id) {
    if (!confirm("Delete?")) return;
    try { await api(`/doctor/consultation-fees/${id}`, "DELETE"); showToast("Deleted!"); loadProfile(); }
    catch (err) { showToast(err.message, "error"); }
}

// Clinical workspace
let activeVisit = null;

document.querySelectorAll(".nav-links a[data-page]").forEach(link => link.addEventListener("click", e => {
    e.preventDefault();
    document.querySelectorAll(".nav-links a").forEach(x => x.classList.remove("active"));
    document.querySelectorAll(".page").forEach(x => x.classList.remove("active"));
    link.classList.add("active");
    document.getElementById(`page-${link.dataset.page}`).classList.add("active");
    if (link.dataset.page === "consultations") loadDoctorQueue();
    if (link.dataset.page === "telemedicine") loadTelemedicine();
}));

function formObject(form, numeric = []) {
    const data = Object.fromEntries(new FormData(form).entries());
    Object.keys(data).forEach(k => { if (data[k] === "") delete data[k]; });
    numeric.forEach(k => { if (data[k] !== undefined) data[k] = Number(data[k]); });
    return data;
}

async function loadDoctorQueue() {
    const box = document.getElementById("doctor-queue");
    box.innerHTML = '<div class="empty-state">Loading queue…</div>';
    try {
        const q = await api("/receptionist/queue/live");
        const rows = q.tokens.filter(x => !window._doctorId || !x.doctor_id || x.doctor_id === window._doctorId);
        if (!rows.length) { box.innerHTML = '<div class="empty-state">No patients in your queue today.</div>'; return; }
        const section = (title, list) => `<div class="section-card"><h3>${title} (${list.length})</h3>${list.length ? `<div class="table-container"><table><thead><tr><th>Token</th><th>Patient</th><th>MRN</th><th>Status</th><th>Action</th></tr></thead><tbody>${list.map(x => `<tr><td><strong>${x.token_number}</strong></td><td>${x.patient_name}</td><td>${x.mrn}</td><td><span class="badge">${x.status.replace('_',' ')}</span></td><td>${x.status === 'completed' ? 'Completed' : `<button class="btn btn-primary" onclick='openConsultation(${JSON.stringify(JSON.stringify(x))})'>${x.status === 'in_consultation' ? 'Resume' : 'Start'}</button>`}</td></tr>`).join("")}</tbody></table></div>` : '<p style="color:#64748b">None</p>'}</div>`;
        box.innerHTML = section("Current Patient", rows.filter(x => x.status === "in_consultation")) + section("Next Patients", rows.filter(x => ["waiting","called"].includes(x.status))) + section("Past Patients Today", rows.filter(x => x.status === "completed"));
    } catch (err) { box.innerHTML = `<div class="empty-state">${err.message}</div>`; }
}

async function openConsultation(serialized) {
    const visit = JSON.parse(serialized);
    try {
        if (!window._doctorId) throw new Error("Doctor profile is still loading");
        await api(`/receptionist/queue/${visit.token_id}/status?new_status=in_consultation`, "PUT");
        const encounter = await api("/emr/encounters", "POST", { patient_id:visit.patient_id, doctor_id:window._doctorId, appointment_id:visit.appointment_id, encounter_type:"OPD", chief_complaint:"Outpatient consultation" });
        activeVisit = {...visit, encounter_id:encounter.encounter_id};
        document.getElementById("clinical-workspace").style.display = "block";
        document.getElementById("patient-banner").innerHTML = `<div><h2>${visit.patient_name}</h2><p>MRN: ${visit.mrn} · Token: ${visit.token_number}</p></div><div><strong>${encounter.encounter_number}</strong><br>${encounter.encounter_status}</div>`;
        await loadPatientSummary();
        await loadReferralDoctors();
        await loadPrescriptionCatalog();
        document.getElementById("clinical-workspace").scrollIntoView({behavior:"smooth"});
    } catch (err) { showToast(err.message, "error"); }
}

async function loadPatientSummary() {
    if (!activeVisit) return;
    try {
        const s = await api(`/emr/patients/${activeVisit.patient_id}/summary`);
        const allergies = s.active_allergies.map(a => `${a.allergen_name} (${a.severity})`).join(", ");
        const v = s.latest_vitals;
        document.getElementById("patient-summary").innerHTML = `${allergies ? `<div class="alert-list"><strong>⚠ Allergy alerts:</strong> ${allergies}</div>` : ""}<div class="section-card"><strong>Latest vitals:</strong> ${v ? `BP ${v.systolic_bp || '-'} / ${v.diastolic_bp || '-'}, Pulse ${v.heart_rate || '-'}, SpO₂ ${v.oxygen_saturation || '-'}%, BMI ${v.bmi || '-'}` : 'No vitals'} &nbsp; · &nbsp; <strong>Diagnoses:</strong> ${s.active_diagnoses.map(d => `${d.diagnosis_code} ${d.diagnosis_name}`).join(', ') || 'None'} &nbsp; · &nbsp; <strong>Current medications:</strong> ${s.current_medications.map(m => m.medicine_name).join(', ') || 'None'}<hr style="margin:12px 0;border:0;border-top:1px solid #e2e8f0"><strong>Past consultations:</strong> ${s.past_encounters.map(x => `${x.date} — ${x.doctor}: ${x.chief_complaint || 'Consultation'}`).join('<br>') || 'None'}</div>`;
    } catch (err) { showToast(err.message, "error"); }
}

async function clinicalSubmit(e, suffix, body, success) {
    e.preventDefault();
    if (!activeVisit) return showToast("Start a consultation first", "error");
    try { await api(`/emr/encounters/${activeVisit.encounter_id}/${suffix}`, "POST", body); showToast(success); e.target.reset(); await loadPatientSummary(); }
    catch (err) { showToast(err.message, "error"); }
}
function saveVitals(e) { return clinicalSubmit(e, "vitals", formObject(e.target,["temperature","systolic_bp","diastolic_bp","heart_rate","oxygen_saturation","height_cm","weight_kg","pain_score"]), "Vitals saved"); }
function saveDiagnosis(e) { return clinicalSubmit(e, "diagnoses", formObject(e.target), "Diagnosis added"); }
function saveSoap(e) { return clinicalSubmit(e, "soap-notes", formObject(e.target), "SOAP note saved"); }
async function loadPrescriptionCatalog() {
    const select = document.getElementById("prescription-drug");
    if (!select || select.options.length > 1) return;
    try {
        const drugs = await api("/pharmacy/drugs");
        select.insertAdjacentHTML("beforeend", drugs.map(d => `<option value="${d.drug_id}">${d.generic_name}${d.scientific_name ? ` (${d.scientific_name})` : ""}</option>`).join(""));
    } catch (err) { showToast(err.message, "error"); }
}

function savePrescription(e) { return clinicalSubmit(e, "prescriptions", {medications:[formObject(e.target)]}, "Medication added to draft prescription"); }
async function saveAllergy(e) { e.preventDefault(); try { await api(`/emr/patients/${activeVisit.patient_id}/allergies`, "POST", formObject(e.target)); showToast("Allergy alert added"); e.target.reset(); loadPatientSummary(); } catch(err) { showToast(err.message,"error"); } }
async function loadReferralDoctors() { try { const doctors=await api("/receptionist/doctors/availability"); document.getElementById("referral-doctor").innerHTML='<option value="">Select doctor</option>'+doctors.filter(d => d.doctor_id !== window._doctorId).map(d => `<option value="${d.doctor_id}">${d.doctor_name} — ${d.specialization_name || d.department_name}</option>`).join(''); } catch(err) { showToast(err.message,"error"); } }
async function referPatient(e) { e.preventDefault(); if(!activeVisit) return; try { await api(`/emr/encounters/${activeVisit.encounter_id}/referrals`,"POST",formObject(e.target)); showToast("Patient added to the receiving doctor's queue"); e.target.reset(); } catch(err){showToast(err.message,"error");} }
async function completeEncounter(e) { e.preventDefault(); if (!confirm("Complete this consultation? Clinical entries will become read-only.")) return; try { await api(`/emr/encounters/${activeVisit.encounter_id}/complete`, "POST", formObject(e.target)); showToast("Consultation completed"); activeVisit=null; document.getElementById("clinical-workspace").style.display="none"; loadDoctorQueue(); } catch(err) { showToast(err.message,"error"); } }

async function loadTelemedicine() {
    try {
        const [appointments, patients] = await Promise.all([api("/telemedicine/appointments"), api("/patients/")]);
        document.getElementById("tele-patient").innerHTML = '<option value="">Select patient</option>' + patients.map(p => `<option value="${p.patient_id}">${p.first_name} ${p.last_name} (${p.mrn})</option>`).join("");
        document.getElementById("tele-appointments").innerHTML = appointments.length ? `<div class="table-container"><table><thead><tr><th>Patient</th><th>Date</th><th>Platform</th><th>Status</th><th>Action</th></tr></thead><tbody>${appointments.map(a => `<tr><td>${a.patient_name}<br><small>${a.mrn}</small></td><td>${new Date(a.appointment_datetime).toLocaleString()}</td><td>${a.meeting_platform}</td><td>${a.status}</td><td>${a.status==='Scheduled' ? `<button class="btn btn-primary" onclick="startTeleSession('${a.virtual_appointment_id}','${a.consultation_link}')">Start</button>` : a.consultation_link ? `<a href="${a.consultation_link}" target="_blank">Room link</a>` : '-'}</td></tr>`).join("")}</tbody></table></div>` : '<div class="empty-state">No virtual appointments.</div>';
    } catch(err) { showToast(err.message,"error"); }
}
async function scheduleTeleAppointment(e) { e.preventDefault(); const data=formObject(e.target); data.doctor_id=window._doctorId; data.appointment_datetime=new Date(data.appointment_datetime).toISOString(); try { await api("/telemedicine/appointments","POST",data); showToast("Virtual consultation scheduled"); e.target.reset(); loadTelemedicine(); } catch(err){showToast(err.message,"error");} }
async function startTeleSession(appointmentId, link) { try { const s=await api("/telemedicine/sessions/start","POST",{virtual_appointment_id:appointmentId}); if(link) window.open(link,"_blank"); const notes=prompt("Enter session clinical notes when the consultation is complete:"); if(notes) { await api(`/telemedicine/sessions/${s.session_id}/complete`,"POST",{clinical_notes:notes}); showToast("Session completed and synced to EMR"); loadTelemedicine(); } } catch(err){showToast(err.message,"error");} }

// Init only after the server validates the JWT and its clinical role.
async function initDoctorPortal() {
    try {
        const me = await api("/auth/me");
        if (!me.roles.some(r => ["doctor","surgeon","telemedicine_doctor","super_admin"].includes(r))) {
            localStorage.clear();
            window.location.replace("/"); return;
        }
        document.documentElement.style.display = "";
        await loadProfile();
    } catch (_) {
        localStorage.clear();
        window.location.replace("/");
    }
}
initDoctorPortal();
