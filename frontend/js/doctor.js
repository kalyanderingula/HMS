const API = "/api/v1";
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
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

let doctorProfilePromise = null;

async function ensureDoctorProfile() {
    if (window._profileData?.doctor?.doctor_id) return window._profileData;
    if (!doctorProfilePromise) {
        doctorProfilePromise = api("/doctor/my-profile/current")
            .then(profileData => {
                if (!profileData?.doctor?.doctor_id) throw new Error("No doctor record is linked to this account");
                window._profileData = profileData;
                window._doctorId = profileData.doctor.doctor_id;
                return profileData;
            })
            .catch(error => {
                doctorProfilePromise = null;
                throw error;
            });
    }
    return doctorProfilePromise;
}

// Load entire profile page
async function loadProfile() {
    const container = document.getElementById("profile-content");
    try {
        const profileData = await ensureDoctorProfile();
        const auxiliary = await Promise.allSettled([
            api("/doctor/document-types"),
            api("/doctor/specializations"),
            api("/doctor/languages"),
        ]);
        const [docTypes, specializations, languages] = auxiliary.map(result =>
            result.status === "fulfilled" ? result.value : []);

        // Store for later use
        window._docTypes = docTypes;
        window._specializations = specializations;
        window._languages = languages;

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
    if (link.dataset.page === "diagnostic-reports") loadDiagnosticReports();
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
        const historyButton = x => `<button class="btn btn-outline btn-sm" onclick='viewPatientHistoryFromQueue("${x.patient_id}", "${esc(x.patient_name)}", "${esc(x.mrn)}")' style="margin-right:6px;border:1px solid #cbd5e1;background:#fff;cursor:pointer;">📜 History</button>`;
        const section = (title, list, action) => `<div class="section-card"><h3>${title} (${list.length})</h3>${list.length ? `<div class="table-container"><table><thead><tr><th>Token</th><th>Patient</th><th>MRN</th><th>Status</th><th>Action</th></tr></thead><tbody>${list.map((x, index) => `<tr><td><strong>${x.token_number}</strong></td><td>${esc(x.patient_name)}</td><td>${esc(x.mrn)}</td><td><span class="badge">${x.status.replace('_',' ')}</span></td><td>${historyButton(x)}${action(x, index)}</td></tr>`).join("")}</tbody></table></div>` : '<p style="color:#64748b">None</p>'}</div>`;
        const current = rows.filter(x => ["called", "in_consultation"].includes(x.status));
        const waiting = rows.filter(x => x.status === "waiting");
        const completed = rows.filter(x => x.status === "completed");
        const ordinal = position => {
            const remainder = position % 100;
            if (remainder >= 11 && remainder <= 13) return `${position}th`;
            return `${position}${({1:"st", 2:"nd", 3:"rd"})[position % 10] || "th"}`;
        };
        const currentAction = x => x.status === "called"
            ? `<button class="btn btn-primary btn-sm" onclick='openConsultation(${JSON.stringify(JSON.stringify(x))})'>In-Room / Start</button>`
            : `<button class="btn btn-primary btn-sm" onclick='openConsultation(${JSON.stringify(JSON.stringify(x))})'>Resume</button>`;
        const waitingAction = (x, index) => index === 0
            ? (current.length
                ? '<span style="color:#64748b;font-size:12px;font-weight:600;">Waiting for current patient</span>'
                : `<button class="btn btn-primary btn-sm" onclick="callNextPatient('${x.token_id}')">Call Next</button>`)
            : `<span style="color:#64748b;font-size:12px;font-weight:600;">${index < 10 ? `${ordinal(index + 1)} Call` : "Queued"}</span>`;
        box.innerHTML = section("Current Patient", current, currentAction)
            + section("Next Patients", waiting, waitingAction)
            + section("Past Patients Today", completed, () => '<span style="color:#059669;font-size:12px;font-weight:600;">Done</span>');
    } catch (err) { box.innerHTML = `<div class="empty-state">${err.message}</div>`; }
}

function switchConsultationTab(tab) {
    const btnActive = document.getElementById("btn-subtab-active");
    const btnHistory = document.getElementById("btn-subtab-history");
    const viewActive = document.getElementById("view-subtab-active");
    const viewHistory = document.getElementById("view-subtab-history");

    if (tab === 'active') {
        if (btnActive) { btnActive.className = "btn btn-primary"; btnActive.style.background = ""; btnActive.style.border = ""; btnActive.style.color = ""; }
        if (btnHistory) { btnHistory.className = "btn"; btnHistory.style.background = "#fff"; btnHistory.style.border = "1px solid #cbd5e1"; btnHistory.style.color = "#1e293b"; }
        if (viewActive) viewActive.style.display = "block";
        if (viewHistory) viewHistory.style.display = "none";
    } else {
        if (btnHistory) { btnHistory.className = "btn btn-primary"; btnHistory.style.background = ""; btnHistory.style.border = ""; btnHistory.style.color = ""; }
        if (btnActive) { btnActive.className = "btn"; btnActive.style.background = "#fff"; btnActive.style.border = "1px solid #cbd5e1"; btnActive.style.color = "#1e293b"; }
        if (viewActive) viewActive.style.display = "none";
        if (viewHistory) viewHistory.style.display = "block";
        if (activeVisit && activeVisit.patient_id) {
            loadPatientClinicalHistory(activeVisit.patient_id, "patient-clinical-history-view");
        }
    }
}

function viewPatientHistoryFromQueue(patientId, patientName, mrn) {
    const dialog = document.getElementById("patient-history-dialog");
    document.getElementById("history-modal-title").textContent = `Clinical History: ${patientName} (${mrn})`;
    document.getElementById("history-modal-subtitle").textContent = `Full past consultations, attending doctors, SOAP notes, and diagnostic reports`;
    dialog.showModal();
    loadPatientClinicalHistory(patientId, "history-modal-body");
}

async function loadPatientClinicalHistory(patientId, containerId = "patient-clinical-history-view") {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '<div class="empty-state">Loading comprehensive clinical history…</div>';

    try {
        const data = await api(`/doctor/patients/${patientId}/clinical-history`);
        const p = data.patient || {};
        const consultations = data.consultations || [];
        const labs = data.laboratory_results || [];
        const rads = data.radiology_reports || [];
        const vitals = data.vitals_timeline || [];

        let html = '';

        // 1. Patient Demographics & Key Clinical Alerts Header
        const age = p.date_of_birth ? `${Math.floor((new Date() - new Date(p.date_of_birth))/(365.25*24*3600*1000))} yrs` : '-';
        html += `
            <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:16px;margin-bottom:18px;">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
                    <div>
                        <h3 style="margin:0;color:#0f172a;font-size:17px;">👤 ${esc(p.full_name)} <span style="font-size:13px;color:#64748b;font-weight:normal;">(MRN: ${esc(p.mrn)})</span></h3>
                        <p style="margin:4px 0 0;font-size:13px;color:#475569;">
                            Age: <strong>${age}</strong> &nbsp;·&nbsp; Gender: <strong>${esc(p.gender || '-')}</strong> &nbsp;·&nbsp; Blood Group: <strong>${esc(p.blood_group || '-')}</strong>
                        </p>
                    </div>
                    <div>
                        ${(p.allergies && p.allergies.length) ? `
                            <div style="background:#fee2e2;border:1px solid #fca5a5;color:#991b1b;padding:6px 12px;border-radius:6px;font-size:12px;font-weight:600;">
                                ⚠️ Known Allergies: ${p.allergies.map(a => `${esc(a.allergen)} (${esc(a.severity)})`).join(", ")}
                            </div>
                        ` : '<span style="font-size:12px;color:#10b981;font-weight:600;">✓ No recorded drug allergies</span>'}
                    </div>
                </div>
                ${(p.active_diagnoses && p.active_diagnoses.length) ? `
                    <div style="margin-top:10px;font-size:12px;color:#334155;">
                        <strong>Chronic / Active Diagnoses:</strong> ${p.active_diagnoses.map(d => `<span class="badge" style="background:#e0e7ff;color:#3730a3;margin-left:4px;">${esc(d.code)}: ${esc(d.name)}</span>`).join(" ")}
                    </div>
                ` : ''}
            </div>
        `;

        // 2. Previous Consultations & Previous Doctors Consulted
        html += `
            <div class="section-card">
                <h3>👨‍⚕️ Previous Doctor Consultations (${consultations.length})</h3>
                ${!consultations.length ? '<p style="color:#64748b;margin:0;">No previous doctor consultations found in hospital records.</p>' : `
                    <div style="display:flex;flex-direction:column;gap:14px;">
                        ${consultations.map((c, idx) => `
                            <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #2563eb;border-radius:8px;padding:16px;">
                                <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
                                    <div>
                                        <h4 style="margin:0;color:#1e293b;font-size:15px;">Dr. ${esc(c.doctor_name || 'Consultant')} &nbsp;<span style="font-size:12px;color:#2563eb;font-weight:500;">— ${esc(c.specialization || c.department || 'General OPD')}</span></h4>
                                        <div style="font-size:12px;color:#64748b;margin-top:2px;">
                                            Encounter: <strong>${esc(c.encounter_number)}</strong> (${esc(c.encounter_type)}) &nbsp;·&nbsp; Date: <strong>${c.encounter_datetime ? new Date(c.encounter_datetime).toLocaleString() : '-'}</strong> &nbsp;·&nbsp; Status: <span class="badge" style="font-size:10px;">${esc(c.status)}</span>
                                        </div>
                                    </div>
                                    <div style="font-size:12px;color:#475569;background:#f1f5f9;padding:4px 8px;border-radius:6px;">
                                        <strong>Chief Complaint:</strong> ${esc(c.chief_complaint || 'General Checkup')}
                                    </div>
                                </div>

                                <!-- SOAP Note -->
                                ${c.soap_note ? `
                                    <div style="margin-top:12px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:10px 12px;font-size:12px;">
                                        <div style="color:#0284c7;font-weight:600;margin-bottom:6px;">📝 Doctor Clinical SOAP Note:</div>
                                        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px;">
                                            <div><strong style="color:#475569;">Subjective:</strong> <div style="color:#1e293b;">${esc(c.soap_note.subjective || '-')}</div></div>
                                            <div><strong style="color:#475569;">Objective:</strong> <div style="color:#1e293b;">${esc(c.soap_note.objective || '-')}</div></div>
                                            <div><strong style="color:#475569;">Assessment:</strong> <div style="color:#1e293b;">${esc(c.soap_note.assessment || '-')}</div></div>
                                            <div><strong style="color:#475569;">Plan:</strong> <div style="color:#1e293b;">${esc(c.soap_note.plan || '-')}</div></div>
                                        </div>
                                    </div>
                                ` : ''}

                                <!-- Diagnoses Made In This Visit -->
                                ${c.diagnoses && c.diagnoses.length ? `
                                    <div style="margin-top:10px;font-size:12px;">
                                        <strong style="color:#475569;">Diagnoses Recorded:</strong>
                                        <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:4px;">
                                            ${c.diagnoses.map(d => `<span class="badge" style="background:#fef3c7;color:#92400e;border:1px solid #fde68a;">${esc(d.code)} ${esc(d.name)} (${esc(d.severity || d.type || 'Confirmed')})</span>`).join("")}
                                        </div>
                                    </div>
                                ` : ''}

                                <!-- Prescriptions Issued In This Visit -->
                                ${c.prescriptions && c.prescriptions.length ? `
                                    <div style="margin-top:10px;font-size:12px;">
                                        <strong style="color:#475569;">Prescriptions Issued:</strong>
                                        <div style="display:flex;flex-direction:column;gap:4px;margin-top:4px;">
                                            ${c.prescriptions.map(med => `
                                                <div style="background:#f0fdf4;border:1px solid #bbf7d0;color:#166534;padding:4px 8px;border-radius:4px;">
                                                    💊 <strong>${esc(med.medicine_name)}</strong> — ${esc(med.dosage || '')} · ${esc(med.frequency || '')} · ${esc(med.duration || '')} · Route: ${esc(med.route || 'Oral')} ${med.instructions ? `(${esc(med.instructions)})` : ''}
                                                </div>
                                            `).join("")}
                                        </div>
                                    </div>
                                ` : ''}
                            </div>
                        `).join("")}
                    </div>
                `}
            </div>
        `;

        // 3. Laboratory Test Results History
        html += `
            <div class="section-card">
                <h3>🧪 Laboratory Reports History (${labs.length})</h3>
                ${!labs.length ? '<p style="color:#64748b;margin:0;">No previous laboratory results found for this patient.</p>' : `
                    <div style="display:flex;flex-direction:column;gap:12px;">
                        ${labs.map(l => `
                            <div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:14px;">
                                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                                    <div>
                                        <strong style="font-size:14px;color:#0f172a;">${esc(l.test_name)}</strong> &nbsp;
                                        <span class="badge">${esc(l.category || 'Clinical Pathology')}</span>
                                    </div>
                                    <div style="font-size:12px;color:#64748b;">
                                        Date: <strong>${l.approved_at ? new Date(l.approved_at).toLocaleDateString() : '-'}</strong> &nbsp;·&nbsp; Status: <span class="badge" style="background:#10b981;color:#fff;">${esc(l.result_status || 'Approved')}</span>
                                    </div>
                                </div>
                                <div class="table-container">
                                    <table>
                                        <thead><tr><th>Parameter</th><th>Value</th><th>Unit</th><th>Reference Range</th><th>Flag</th></tr></thead>
                                        <tbody>
                                            ${(l.parameters || []).map(param => `
                                                <tr style="${param.result_flag === 'Critical' ? 'background:#fef2f2;font-weight:bold;' : param.result_flag === 'Abnormal' ? 'background:#fffbeb;' : ''}">
                                                    <td>${esc(param.parameter_name)}</td>
                                                    <td>${esc(param.result_value)}</td>
                                                    <td>${esc(param.unit || '-')}</td>
                                                    <td>${esc(param.normal_range || '-')}</td>
                                                    <td>${param.result_flag === 'Critical' ? '<span class="badge" style="background:#dc2626;color:#fff;">CRITICAL</span>' : param.result_flag === 'Abnormal' ? '<span class="badge" style="background:#f59e0b;color:#fff;">ABNORMAL</span>' : '<span class="badge">NORMAL</span>'}</td>
                                                </tr>
                                            `).join("")}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        `).join("")}
                    </div>
                `}
            </div>
        `;

        // 4. Radiology & Imaging Reports History
        html += `
            <div class="section-card">
                <h3>☢️ Radiology & Imaging Studies History (${rads.length})</h3>
                ${!rads.length ? '<p style="color:#64748b;margin:0;">No previous radiology imaging reports found for this patient.</p>' : `
                    <div style="display:flex;flex-direction:column;gap:12px;">
                        ${rads.map(r => `
                            <div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:14px;${r.is_critical ? 'border-left:4px solid #dc2626;' : ''}">
                                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:8px;">
                                    <div>
                                        <strong style="font-size:14px;color:#0f172a;">${esc(r.test_name)}</strong> &nbsp;
                                        <span class="badge">${esc(r.modality || 'Imaging')}</span>
                                        ${r.is_critical ? '<span class="badge" style="background:#dc2626;color:#fff;margin-left:6px;">🚨 CRITICAL ALERT</span>' : ''}
                                    </div>
                                    <div style="display:flex;align-items:center;gap:8px;">
                                        <span style="font-size:12px;color:#64748b;">Date: <strong>${r.finalized_at ? new Date(r.finalized_at).toLocaleDateString() : '-'}</strong></span>
                                        ${r.study_id ? `<button class="btn btn-outline btn-sm" onclick="openPacsViewer('${r.study_id}')" style="background:#fff;border:1px solid #cbd5e1;cursor:pointer;">PACS Viewer</button>` : ''}
                                    </div>
                                </div>
                                <div style="font-size:13px;color:#1e293b;margin-bottom:6px;">
                                    <strong>Impression:</strong> ${esc(r.impression || '-')}
                                </div>
                                <div style="font-size:12px;color:#64748b;">
                                    <strong>Findings:</strong> ${esc(r.findings || '-')}
                                </div>
                                ${r.critical_alert_details ? `
                                    <div style="margin-top:8px;background:#fef2f2;color:#991b1b;padding:6px 10px;border-radius:6px;font-size:12px;">
                                        ⚠️ ${esc(r.critical_alert_details)}
                                    </div>
                                ` : ''}
                            </div>
                        `).join("")}
                    </div>
                `}
            </div>
        `;

        // 5. Vitals Timeline
        if (vitals && vitals.length) {
            html += `
                <div class="section-card">
                    <h3>📈 Recorded Vitals Timeline (${vitals.length})</h3>
                    <div class="table-container">
                        <table>
                            <thead><tr><th>Recorded Time</th><th>BP (SYS/DIA)</th><th>Pulse</th><th>SpO₂</th><th>Temp °C</th><th>BMI</th><th>Pain</th></tr></thead>
                            <tbody>
                                ${vitals.map(v => `
                                    <tr>
                                        <td>${v.recorded_at ? new Date(v.recorded_at).toLocaleString() : '-'}</td>
                                        <td><strong>${v.systolic_bp || '-'} / ${v.diastolic_bp || '-'}</strong> mmHg</td>
                                        <td>${v.heart_rate ? `${v.heart_rate} bpm` : '-'}</td>
                                        <td>${v.oxygen_saturation ? `${v.oxygen_saturation}%` : '-'}</td>
                                        <td>${v.temperature ? `${v.temperature}°C` : '-'}</td>
                                        <td>${v.bmi || '-'}</td>
                                        <td>${v.pain_score !== null && v.pain_score !== undefined ? `${v.pain_score}/10` : '-'}</td>
                                    </tr>
                                `).join("")}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }

        container.innerHTML = html;
    } catch (err) {
        container.innerHTML = `<div class="empty-state" style="color:#dc2626;">Error loading clinical history: ${esc(err.message)}</div>`;
    }
}

async function openConsultation(serialized) {
    const visit = JSON.parse(serialized);
    try {
        // Queue entries already identify the doctor assigned to the appointment.
        // Use that value when an admin opens the doctor console; an admin account
        // does not necessarily have its own doctor profile.
        let consultationDoctorId = visit.doctor_id || window._doctorId;
        if (!consultationDoctorId) {
            showToast("Loading doctor profile...");
            await ensureDoctorProfile();
            consultationDoctorId = window._doctorId;
        }
        await api(`/receptionist/queue/${visit.token_id}/status?new_status=in_consultation`, "PUT");
        const encounter = await api("/emr/encounters", "POST", { patient_id:visit.patient_id, doctor_id:consultationDoctorId, appointment_id:visit.appointment_id, encounter_type:"OPD", chief_complaint:"Outpatient consultation" });
        activeVisit = {...visit, doctor_id:consultationDoctorId, encounter_id:encounter.encounter_id};
        document.getElementById("clinical-workspace").style.display = "block";
        switchConsultationTab('active');
        document.getElementById("patient-banner").innerHTML = `<div><h2>${visit.patient_name}</h2><p>MRN: ${visit.mrn} · Token: ${visit.token_number}</p></div><div><strong>${encounter.encounter_number}</strong><br>${encounter.encounter_status}</div>`;
        await loadPatientSummary();
        await loadLabApprovals();
        await loadReferralDoctors();
        await loadPrescriptionCatalog();
        await loadLabCatalog();
        document.getElementById("clinical-workspace").scrollIntoView({behavior:"smooth"});
    } catch (err) { showToast(err.message, "error"); }
}

async function loadPatientSummary() {
    if (!activeVisit) return;
    try {
        const s = await api(`/emr/patients/${activeVisit.patient_id}/summary`);
        const allergies = s.active_allergies.map(a => `${a.allergen_name} (${a.severity})`).join(", ");
        const v = s.latest_vitals;
        const reports=(s.radiology_reports || []).map(r=>`${r.test_name}: ${r.impression} (${new Date(r.reported_at).toLocaleDateString()})`).join('<br>');
        const transfusions=(s.blood_transfusions || []).map(t=>`${t.component_name} ${t.blood_group}, unit ${t.unit_number}, ${t.volume_transfused} ml${t.adverse_reaction?' · adverse reaction recorded':''}`).join('<br>');
        document.getElementById("patient-summary").innerHTML = `${allergies ? `<div class="alert-list"><strong>⚠ Allergy alerts:</strong> ${allergies}</div>` : ""}<div class="section-card"><strong>Latest vitals:</strong> ${v ? `BP ${v.systolic_bp || '-'} / ${v.diastolic_bp || '-'}, Pulse ${v.heart_rate || '-'}, SpO₂ ${v.oxygen_saturation || '-'}%, BMI ${v.bmi || '-'}` : 'No vitals'} &nbsp; · &nbsp; <strong>Diagnoses:</strong> ${s.active_diagnoses.map(d => `${d.diagnosis_code} ${d.diagnosis_name}`).join(', ') || 'None'} &nbsp; · &nbsp; <strong>Current medications:</strong> ${s.current_medications.map(m => m.medicine_name).join(', ') || 'None'}<hr style="margin:12px 0;border:0;border-top:1px solid #e2e8f0"><strong>Radiology reports:</strong><br>${reports || 'None'}<hr style="margin:12px 0;border:0;border-top:1px solid #e2e8f0"><strong>Transfusion history:</strong><br>${transfusions || 'None'}<hr style="margin:12px 0;border:0;border-top:1px solid #e2e8f0"><strong>Past consultations:</strong> ${s.past_encounters.map(x => `${x.date} — ${x.doctor}: ${x.chief_complaint || 'Consultation'}`).join('<br>') || 'None'}</div>`;
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

async function loadLabApprovals(){
    if(!activeVisit)return;const box=document.getElementById("lab-approvals");
    try{const rows=(await api("/worklists/laboratory")).filter(r=>r.patient_id===activeVisit.patient_id&&r.result_entry_id&&r.result_status!=="Approved");
    box.innerHTML=rows.length?`<div class="section-card"><h3>Laboratory results awaiting approval</h3>${rows.map(r=>`<p><strong>${r.test_name}</strong> · ${r.order_number} <button class="btn btn-primary" onclick="reviewLabResult('${r.result_entry_id}')">Review</button></p>`).join("")}</div>`:"";}catch(err){box.textContent=err.message;}
}
async function reviewLabResult(id){try{const r=await api(`/laboratory/results/${id}`);const lines=r.parameters.map(p=>`${p.parameter_name}: ${p.result_value} ${p.unit||''} · ${p.normal_range||'-'} · ${p.result_flag}`).join("\n");if(confirm(`${r.test_name}\n\n${lines}\n\nApprove and release this report?`)){await api(`/laboratory/results/${id}/approve`,"POST");showToast("Laboratory report approved");await loadPatientSummary();await loadLabApprovals();}}catch(err){showToast(err.message,"error");}}

function savePrescription(e) { return clinicalSubmit(e, "prescriptions", {medications:[formObject(e.target)]}, "Medication added to draft prescription"); }
async function saveAllergy(e) { e.preventDefault(); try { await api(`/emr/patients/${activeVisit.patient_id}/allergies`, "POST", formObject(e.target)); showToast("Allergy alert added"); e.target.reset(); loadPatientSummary(); } catch(err) { showToast(err.message,"error"); } }
async function requestBlood(e) { e.preventDefault(); if(!activeVisit)return; const body=formObject(e.target,["units_requested"]);body.patient_id=activeVisit.patient_id;try{await api("/blood-bank/requests","POST",body);showToast("Blood request sent");e.target.reset();}catch(err){showToast(err.message,"error");} }
async function loadLabCatalog(){const tests=await api("/laboratory/tests");document.getElementById("lab-test-select").innerHTML=tests.map(t=>`<option value="${t.test_id}">${t.test_name} · ₹${t.price}</option>`).join("");}
async function requestLab(e){e.preventDefault();const form=e.target;const ids=[...form.elements.test_ids.selectedOptions].map(x=>x.value);try{await api("/laboratory/orders","POST",{patient_id:activeVisit.patient_id,encounter_id:activeVisit.encounter_id,doctor_id:activeVisit.doctor_id,priority:form.elements.priority.value,clinical_notes:form.elements.clinical_notes.value,items:ids.map(test_id=>({test_id}))});showToast("Laboratory order sent");form.reset();}catch(err){showToast(err.message,"error");}}
async function loadReferralDoctors() { try { const doctors=await api("/receptionist/doctors/availability"); document.getElementById("referral-doctor").innerHTML='<option value="">Select doctor</option>'+doctors.filter(d => d.doctor_id !== activeVisit?.doctor_id).map(d => `<option value="${d.doctor_id}">${d.doctor_name} — ${d.specialization_name || d.department_name}</option>`).join(''); } catch(err) { showToast(err.message,"error"); } }
async function referPatient(e) { e.preventDefault(); if(!activeVisit) return; try { await api(`/emr/encounters/${activeVisit.encounter_id}/referrals`,"POST",formObject(e.target)); showToast("Patient added to the receiving doctor's queue"); e.target.reset(); } catch(err){showToast(err.message,"error");} }
async function completeEncounter(e) {
    e.preventDefault();
    if (!confirm("Complete this consultation? Clinical entries will become read-only.")) return;
    try {
        const fd = new FormData(e.target);
        const followUpDate = fd.get("follow_up_date");
        const followUpTime = fd.get("follow_up_time") || "10:00";
        await api(`/emr/encounters/${activeVisit.encounter_id}/complete`, "POST", formObject(e.target));
        if (followUpDate) {
            try {
                await api("/doctor/follow-up", "POST", {
                    patient_id: activeVisit.patient_id,
                    doctor_id: activeVisit.doctor_id,
                    follow_up_date: followUpDate,
                    time_slot: followUpTime,
                    reason: "Doctor consultation follow-up"
                });
                showToast("Consultation completed & follow-up scheduled!");
            } catch (_) { showToast("Consultation completed"); }
        } else {
            showToast("Consultation completed");
        }
        activeVisit = null;
        document.getElementById("clinical-workspace").style.display = "none";
        loadDoctorQueue();
    } catch (err) { showToast(err.message, "error"); }
}

// Notifications
let docNotifsOpen = false;
async function loadDocNotifs() {
    try {
        const res = await api("/notifications/my");
        const badge = document.getElementById("doc-notif-badge");
        if (badge) {
            if (res.unread_count > 0) {
                badge.textContent = res.unread_count;
                badge.style.display = "inline-block";
            } else {
                badge.style.display = "none";
            }
        }
        const dd = document.getElementById("doc-notif-dropdown");
        if (!dd) return;
        if (!res.notifications.length) {
            dd.innerHTML = '<div style="padding:12px;color:#64748b;font-size:13px;text-align:center;">No notifications</div>';
            return;
        }
        dd.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid #e2e8f0;">
                <strong style="font-size:13px;color:#0f172a;">Notifications (${res.unread_count} unread)</strong>
                <button class="btn-sm" style="font-size:11px;background:#f1f5f9;border:1px solid #cbd5e1;cursor:pointer;padding:3px 6px;border-radius:4px;" onclick="markAllDocNotifsRead()">Mark all read</button>
            </div>
            <div style="max-height:280px;overflow-y:auto;">
                ${res.notifications.map(n => `
                    <div style="padding:8px;border-radius:6px;margin-bottom:6px;font-size:12px;background:${n.status==='read'?'#f8fafc':n.is_urgent?'#fef2f2':'#eff6ff'};border-left:3px solid ${n.is_urgent?'#dc2626':'#3b82f6'};cursor:pointer;" onclick="markDocNotifRead('${n.notification_id}')">
                        <div style="display:flex;justify-content:space-between;color:#0f172a;font-weight:600;"><span>${esc(n.subject)}</span><span style="font-size:10px;color:#94a3b8;">${n.source_module}</span></div>
                        <p style="margin:3px 0 0;color:#475569;font-size:11px;">${esc(n.body || '')}</p>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (_) {}
}
function toggleDocNotifs() {
    docNotifsOpen = !docNotifsOpen;
    const dd = document.getElementById("doc-notif-dropdown");
    if (dd) dd.style.display = docNotifsOpen ? "block" : "none";
    if (docNotifsOpen) loadDocNotifs();
}
async function markDocNotifRead(id) {
    try { await api(`/notifications/${id}/read`, "POST"); loadDocNotifs(); } catch(_) {}
}
async function markAllDocNotifsRead() {
    try { await api("/notifications/read-all", "POST"); loadDocNotifs(); } catch(_) {}
}

// ==================== Diagnostic Reports Workspace ====================
let currentReportScope = 'pending';
let currentReportQuery = '';
let reportSearchTimer = null;

function setReportsFilter(scope) {
    currentReportScope = scope;
    const btnPending = document.getElementById("btn-scope-pending");
    const btnOrdered = document.getElementById("btn-scope-ordered");
    const btnAll = document.getElementById("btn-scope-all");

    [btnPending, btnOrdered, btnAll].forEach(btn => {
        if (btn) {
            btn.className = "btn btn-sm";
            btn.style.background = "#fff";
            btn.style.border = "1px solid #cbd5e1";
            btn.style.color = "#1e293b";
        }
    });

    if (scope === 'pending' && btnPending) {
        btnPending.className = "btn btn-primary btn-sm";
        btnPending.style.background = "";
        btnPending.style.border = "";
        btnPending.style.color = "";
    } else if (scope === 'ordered_by_me' && btnOrdered) {
        btnOrdered.className = "btn btn-primary btn-sm";
        btnOrdered.style.background = "";
        btnOrdered.style.border = "";
        btnOrdered.style.color = "";
    } else if (scope === 'all' && btnAll) {
        btnAll.className = "btn btn-primary btn-sm";
        btnAll.style.background = "";
        btnAll.style.border = "";
        btnAll.style.color = "";
    }

    loadDiagnosticReports();
}

function onReportSearch(val) {
    clearTimeout(reportSearchTimer);
    reportSearchTimer = setTimeout(() => {
        currentReportQuery = (val || "").trim();
        loadDiagnosticReports();
    }, 300);
}

async function loadDiagnosticReports() {
    const box = document.getElementById("pending-reports-container");
    if (!box) return;
    box.innerHTML = '<div class="empty-state">Loading diagnostic reports…</div>';

    try {
        const queryParams = new URLSearchParams();
        queryParams.set("scope", currentReportScope);
        if (currentReportQuery) queryParams.set("q", currentReportQuery);

        const res = await api(`/doctor/reports?${queryParams.toString()}`);
        const badge = document.getElementById("pending-reports-badge");
        if (badge && res.total_pending !== undefined) {
            if (res.total_pending > 0) {
                badge.textContent = res.total_pending;
                badge.style.display = "inline-block";
            } else {
                badge.style.display = "none";
            }
        }

        const labs = res.laboratory_reports || [];
        const rads = res.radiology_reports || [];

        if (!labs.length && !rads.length) {
            const scopeLabel = currentReportScope === 'pending' ? 'awaiting your review' : currentReportScope === 'ordered_by_me' ? 'ordered by you' : 'matching criteria';
            box.innerHTML = `<div class="empty-state">No diagnostic reports found ${scopeLabel}.</div>`;
            return;
        }

        let html = '';

        if (labs.length) {
            html += `
                <div class="section-card">
                    <h3>🧪 Laboratory Reports (${labs.length})</h3>
                    <div class="table-container">
                        <table>
                            <thead><tr><th>Patient & MRN</th><th>Ordered By</th><th>Test Name</th><th>Parameters</th><th>Status & Flags</th><th>Action</th></tr></thead>
                            <tbody>
                                ${labs.map(r => `
                                    <tr style="${r.has_critical ? 'background:#fef2f2;' : r.has_abnormal ? 'background:#fffbeb;' : ''}">
                                        <td><strong>${esc(r.patient_name)}</strong><br><small style="color:#64748b;">MRN: ${esc(r.mrn)} · Order: ${esc(r.order_number)}</small></td>
                                        <td><div style="font-size:12px;">${esc(r.ordering_doctor || 'Hospital Doctor')}</div><small style="color:#94a3b8;">${r.order_date ? new Date(r.order_date).toLocaleDateString() : ''}</small></td>
                                        <td><strong>${esc(r.test_name)}</strong></td>
                                        <td><div style="font-size:12px;">${(r.parameters || []).map(p => `<div>${esc(p.parameter_name)}: <strong>${esc(p.value)}</strong> ${esc(p.unit)} <small style="color:#64748b;">(${esc(p.normal_range)})</small></div>`).join('')}</div></td>
                                        <td>
                                            ${r.has_critical ? '<span class="badge" style="background:#dc2626;color:#fff;">CRITICAL</span>' : r.has_abnormal ? '<span class="badge" style="background:#f59e0b;color:#fff;">ABNORMAL</span>' : '<span class="badge">NORMAL</span>'}
                                            ${r.is_acknowledged ? '<br><span class="badge" style="background:#10b981;color:#fff;margin-top:4px;">✓ Acknowledged</span>' : ''}
                                        </td>
                                        <td>
                                            ${r.is_acknowledged ? '<span style="font-size:12px;color:#10b981;font-weight:600;">Reviewed</span>' : `<button class="btn btn-primary btn-sm" onclick="acknowledgeReport('lab', '${r.result_entry_id}')">Acknowledge</button>`}
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }

        if (rads.length) {
            html += `
                <div class="section-card">
                    <h3>☢️ Radiology & Imaging Reports (${rads.length})</h3>
                    <div class="table-container">
                        <table>
                            <thead><tr><th>Patient & MRN</th><th>Ordered By</th><th>Exam / Study</th><th>Impression</th><th>Alert</th><th>Action</th></tr></thead>
                            <tbody>
                                ${rads.map(r => `
                                    <tr style="${r.is_critical ? 'background:#fef2f2;' : ''}">
                                        <td><strong>${esc(r.patient_name)}</strong><br><small style="color:#64748b;">MRN: ${esc(r.mrn)} · Order: ${esc(r.order_number)}</small></td>
                                        <td><div style="font-size:12px;">${esc(r.ordering_doctor || 'Hospital Doctor')}</div><small style="color:#94a3b8;">${r.order_date ? new Date(r.order_date).toLocaleDateString() : ''}</small></td>
                                        <td><strong>${esc(r.test_name)}</strong></td>
                                        <td style="max-width:280px;font-size:12px;">${esc(r.impression)}</td>
                                        <td>
                                            ${r.is_critical ? '<span class="badge" style="background:#dc2626;color:#fff;">🚨 CRITICAL</span>' : '<span class="badge">FINAL</span>'}
                                            ${r.is_acknowledged ? '<br><span class="badge" style="background:#10b981;color:#fff;margin-top:4px;">✓ Acknowledged</span>' : ''}
                                        </td>
                                        <td>
                                            ${r.study_id ? `<button class="btn btn-outline btn-sm" onclick="openPacsViewer('${r.study_id}')" style="margin-right:6px;border:1px solid #cbd5e1;background:#fff;cursor:pointer;">PACS View</button>` : ''}
                                            ${r.is_acknowledged ? '<span style="font-size:12px;color:#10b981;font-weight:600;">Reviewed</span>' : `<button class="btn btn-primary btn-sm" onclick="acknowledgeReport('radiology', '${r.report_id}')">Acknowledge</button>`}
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }

        box.innerHTML = html;
    } catch (err) {
        box.innerHTML = `<div class="empty-state" style="color:#dc2626;">${esc(err.message)}</div>`;
    }
}

function loadPendingReports() {
    setReportsFilter('pending');
}

async function acknowledgeReport(type, id) {
    const notes = prompt("Enter clinical review note (optional):") || "";
    try {
        await api(`/doctor/reports/${type}/${id}/acknowledge`, "POST", { notes });
        showToast("Report reviewed and acknowledged successfully");
        loadDiagnosticReports();
    } catch(err) { showToast(err.message, "error"); }
}

async function openPacsViewer(studyId) {
    try {
        const data = await api(`/radiology/studies/${studyId}/viewer`);
        document.getElementById("pacs-title").textContent = `${data.modality_code} · ${data.study_description}`;
        document.getElementById("pacs-subtitle").textContent = `Patient: ${data.patient_name} (MRN: ${data.mrn}) · Accession: ${data.accession_number} · Date: ${new Date(data.study_date).toLocaleDateString()}`;
        const body = document.getElementById("pacs-body");
        let imagesHtml = '';
        if (data.images && data.images.length) {
            imagesHtml = `
                <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px;margin-bottom:20px;">
                    ${data.images.map((img) => `
                        <div style="background:#1e293b;border:1px solid ${img.is_key_image?'#38bdf8':'#334155'};border-radius:8px;overflow:hidden;padding:8px;text-align:center;">
                            <div style="height:150px;background:#020617;display:flex;align-items:center;justify-content:center;border-radius:6px;margin-bottom:8px;overflow:hidden;">
                                <img src="${esc(img.image_url)}" alt="Slice ${img.instance_number}" style="max-height:100%;max-width:100%;object-fit:contain;" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'160\\' height=\\'160\\'><rect fill=\\'%231e293b\\' width=\\'160\\' height=\\'160\\'/><text fill=\\'%2394a3b8\\' font-size=\\'12\\' x=\\'50%\\' y=\\'50%\\' text-anchor=\\'middle\\'>Series ${img.series_number} #${img.instance_number}</text></svg>'">
                            </div>
                            <div style="font-size:12px;color:#cbd5e1;display:flex;justify-content:space-between;">
                                <span>Slice #${img.instance_number}</span>
                                ${img.is_key_image ? '<span style="color:#38bdf8;font-weight:bold;">★ Key Slice</span>' : ''}
                            </div>
                            ${img.slice_description ? `<div style="font-size:11px;color:#94a3b8;margin-top:2px;">${esc(img.slice_description)}</div>` : ''}
                        </div>
                    `).join('')}
                </div>
            `;
        } else {
            imagesHtml = `<div style="padding:24px;text-align:center;background:#1e293b;border-radius:8px;color:#94a3b8;margin-bottom:20px;">No imaging series slices attached yet.</div>`;
        }
        let reportHtml = '';
        if (data.report) {
            reportHtml = `
                <div style="background:#1e293b;border-radius:8px;padding:16px;">
                    <h4 style="margin:0 0 8px;color:#38bdf8;font-size:14px;">Radiologist Impression & Findings</h4>
                    <p style="font-size:13px;margin:0 0 6px;color:#e2e8f0;"><strong>Impression:</strong> ${esc(data.report.impression)}</p>
                    <p style="font-size:12px;margin:0;color:#94a3b8;"><strong>Findings:</strong> ${esc(data.report.findings)}</p>
                    ${data.report.is_critical ? `<div style="margin-top:10px;background:#7f1d1d;color:#fecaca;padding:8px 12px;border-radius:6px;font-size:12px;"><strong>🚨 Critical Alert:</strong> ${esc(data.report.critical_alert_details || 'Immediate attention required')}</div>` : ''}
                </div>
            `;
        }
        body.innerHTML = imagesHtml + reportHtml;
        document.getElementById("pacs-dialog").showModal();
    } catch(err) { showToast(err.message, "error"); }
}

// ==================== Advanced Telemedicine Workstation ====================
let currentTeleRoomData = null;
let currentTeleSessionId = null;
let liveOrdersInCall = [];

async function loadTelemedicine() {
    try {
        const patientSelect = document.getElementById("tele-patient");
        if (patientSelect && patientSelect.options.length <= 1) {
            const patients = await api("/patient/patients");
            patientSelect.innerHTML = '<option value="">Select registered patient...</option>' +
                patients.map(p => `<option value="${p.patient_id}">${esc(p.first_name)} ${esc(p.last_name)} (MRN: ${esc(p.mrn)})</option>`).join('');
        }
    } catch (_) {}

    const box = document.getElementById("tele-appointments");
    if (!box) return;
    box.innerHTML = '<div class="empty-state">Loading virtual consultations…</div>';

    try {
        const apts = await api("/telemedicine/appointments");
        
        const scheduledCount = apts.filter(a => a.status === "Scheduled").length;
        const activeCount = apts.filter(a => a.status === "In Progress").length;
        const completedCount = apts.filter(a => a.status === "Completed").length;

        const statSched = document.getElementById("tele-stat-scheduled");
        const statAct = document.getElementById("tele-stat-active");
        const statComp = document.getElementById("tele-stat-completed");
        if (statSched) statSched.textContent = scheduledCount;
        if (statAct) statAct.textContent = activeCount;
        if (statComp) statComp.textContent = completedCount;

        if (!apts.length) {
            box.innerHTML = '<div class="empty-state">No virtual consultations scheduled yet. Use the form above to schedule a virtual session.</div>';
            return;
        }

        box.innerHTML = `
            <div class="table-container">
                <table>
                    <thead>
                        <tr><th>Patient & MRN</th><th>Date & Time</th><th>Platform</th><th>Chief Complaint</th><th>Status</th><th>Actions</th></tr>
                    </thead>
                    <tbody>
                        ${apts.map(a => `
                            <tr>
                                <td><strong>${esc(a.patient_name)}</strong><br><small style="color:#64748b;">MRN: ${esc(a.mrn)}</small></td>
                                <td><strong>${new Date(a.appointment_datetime).toLocaleDateString()}</strong><br><small style="color:#64748b;">${new Date(a.appointment_datetime).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</small></td>
                                <td><span class="badge" style="background:#e0f2fe;color:#0369a1;">${esc(a.meeting_platform)}</span></td>
                                <td>${esc(a.chief_complaint || 'Virtual Consultation')}</td>
                                <td>
                                    <span class="badge" style="${a.status === 'Scheduled' ? 'background:#3b82f6;color:#fff;' : a.status === 'In Progress' ? 'background:#10b981;color:#fff;' : 'background:#64748b;color:#fff;'}">
                                        ${esc(a.status)}
                                    </span>
                                </td>
                                <td>
                                    ${a.status !== 'Completed' ? `
                                        <button class="btn btn-primary btn-sm" onclick='launchTeleRoom("${a.virtual_appointment_id}", "${esc(a.patient_name)}", "${esc(a.mrn)}", "${esc(a.consultation_link || "")}")' style="margin-right:4px;">🎥 Launch Room</button>
                                        <button class="btn btn-outline btn-sm" onclick='copyPatientInvite("${esc(a.consultation_link || "")}", "${esc(a.patient_name)}", "${a.appointment_datetime}")' style="border:1px solid #cbd5e1;background:#fff;cursor:pointer;">📋 Copy Invite</button>
                                    ` : '<span style="color:#64748b;font-size:12px;">Completed</span>'}
                                </td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            </div>
        `;
    } catch (err) {
        box.innerHTML = `<div class="empty-state" style="color:#dc2626;">${esc(err.message)}</div>`;
    }
}

async function scheduleTeleAppointment(e) {
    e.preventDefault();
    const form = e.target;
    const body = {
        patient_id: form.patient_id.value,
        doctor_id: window._doctorId,
        appointment_datetime: form.appointment_datetime.value,
        meeting_platform: form.meeting_platform.value,
        chief_complaint: form.chief_complaint.value || "Telemedicine virtual consultation"
    };

    try {
        await api("/telemedicine/appointments", "POST", body);
        showToast("Virtual appointment scheduled successfully!");
        form.reset();
        loadTelemedicine();
    } catch (err) {
        showToast(err.message, "error");
    }
}

function copyPatientInvite(link, patientName, datetimeStr) {
    const formattedDate = new Date(datetimeStr).toLocaleString();
    const docName = localStorage.getItem("hms_name") || "Specialist";
    const text = `🏥 *HMS Virtual Consultation Invitation*\n\nDear ${patientName},\nYour virtual appointment is scheduled for: ${formattedDate}\nAttending Doctor: Dr. ${docName}\n\nJoin Video Room:\n${link || 'https://meet.hmshospital.com'}\n\nPlease click the link 5 minutes before your scheduled appointment time.`;

    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showToast("📋 Patient invite link copied to clipboard!");
        }).catch(() => {
            prompt("Copy Patient Invitation:", text);
        });
    } else {
        prompt("Copy Patient Invitation:", text);
    }
}

function copyPatientInviteFromRoom() {
    if (!currentTeleRoomData) return;
    copyPatientInvite(currentTeleRoomData.consultationLink, currentTeleRoomData.patientName, new Date().toISOString());
}

async function launchTeleRoom(appointmentId, patientName, mrn, consultLink) {
    try {
        const room = await api(`/telemedicine/appointments/${appointmentId}/video-room`, "POST");
        
        let session = null;
        try {
            session = await api("/telemedicine/sessions/start", "POST", { virtual_appointment_id: appointmentId });
        } catch (_) {
            // Already active
        }

        currentTeleRoomData = {
            appointmentId,
            patientName,
            mrn,
            roomUrl: room.room_url,
            consultationLink: consultLink || room.room_url
        };
        currentTeleSessionId = session ? session.session_id : null;
        liveOrdersInCall = [];

        document.getElementById("tele-room-title").textContent = `🎥 Consultation Room: ${patientName} (${mrn})`;
        document.getElementById("tele-room-subtitle").textContent = `Room: ${room.room_name} · Secure WebRTC Encryption Active`;

        const embedBox = document.getElementById("tele-room-embed");
        embedBox.innerHTML = `
            <iframe src="${esc(room.room_url)}" allow="camera; microphone; fullscreen; display-capture" style="width:100%;height:100%;border:none;background:#000;"></iframe>
            <a href="${esc(room.room_url)}" target="_blank" style="position:absolute;top:10px;right:10px;background:rgba(15,23,42,0.85);color:#38bdf8;padding:6px 12px;border-radius:6px;font-size:11px;text-decoration:none;border:1px solid #334155;z-index:10;">↗ Open Full Window</a>
        `;

        renderLiveOrdersHistory();
        document.getElementById("tele-room-dialog").showModal();
    } catch (err) {
        showToast(err.message, "error");
    }
}

function closeTeleRoomDialog() {
    const dialog = document.getElementById("tele-room-dialog");
    document.getElementById("tele-room-embed").innerHTML = "";
    dialog.close();
    loadTelemedicine();
}

function renderLiveOrdersHistory() {
    const box = document.getElementById("live-orders-history");
    if (!box) return;
    if (!liveOrdersInCall.length) {
        box.innerHTML = '<p style="color:#64748b;margin:0;">No orders placed yet in this session.</p>';
        return;
    }
    box.innerHTML = liveOrdersInCall.map((ord) => `
        <div style="background:#0f172a;border:1px solid #334155;padding:8px;border-radius:6px;">
            <div style="display:flex;justify-content:space-between;color:#38bdf8;font-weight:600;">
                <span>${ord.order_type === 'e-prescription' ? '💊 E-Prescription' : ord.order_type === 'lab_order' ? '🧪 Lab Order' : '☢️ Radiology Order'}</span>
                <span style="font-size:10px;color:#94a3b8;">${ord.time}</span>
            </div>
            <p style="margin:4px 0 0;color:#e2e8f0;font-size:11px;">${esc(ord.details)}</p>
        </div>
    `).join("");
}

async function submitInSessionOrder(e) {
    e.preventDefault();
    if (!currentTeleSessionId) {
        showToast("Live session ID is initializing...", "error");
        return;
    }
    const form = e.target;
    const order_type = form.order_type.value;
    const details = form.details.value;

    try {
        await api(`/telemedicine/sessions/${currentTeleSessionId}/orders`, "POST", {
            order_type,
            details,
            item_catalog_ids: []
        });
        liveOrdersInCall.unshift({
            order_type,
            details,
            time: new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})
        });
        renderLiveOrdersHistory();
        form.reset();
        showToast("Live clinical order synchronized to patient record!");
    } catch (err) {
        showToast(err.message, "error");
    }
}

function openCompleteSessionModal() {
    if (!currentTeleSessionId) {
        closeTeleRoomDialog();
        return;
    }
    document.getElementById("tele-complete-dialog").showModal();
}

async function submitCompleteTeleSession(e) {
    e.preventDefault();
    const form = e.target;
    const notes = form.clinical_notes.value;

    try {
        await api(`/telemedicine/sessions/${currentTeleSessionId}/complete`, "POST", {
            clinical_notes: notes
        });
        showToast("Virtual consultation completed and EMR encounter recorded!");
        document.getElementById("tele-complete-dialog").close();
        closeTeleRoomDialog();
    } catch (err) {
        showToast(err.message, "error");
    }
}

// ==================== Doctor Profile Self-Editing ====================
function openDoctorProfileEditModal() {
    if (!window._profileData) {
        showToast("Profile data still loading, please wait...", "error");
        return;
    }

    const d = window._profileData.doctor || {};
    const p = window._profileData.profile || {};
    const emp = window._profileData.employee_details || {};
    const fees = window._profileData.fees || [];

    const opdFee = fees.find(f => f.consultation_type === 'OPD')?.fee_amount || 500;

    document.getElementById("self-edit-phone").value = d.phone || emp.contact?.personal_phone || "";
    document.getElementById("self-edit-email").value = d.email || emp.contact?.personal_email || "";
    document.getElementById("self-edit-experience").value = d.consultation_experience_years || "";
    document.getElementById("self-edit-fee").value = opdFee;
    document.getElementById("self-edit-linkedin").value = p.linkedin_url || "";
    document.getElementById("self-edit-website").value = p.website_url || "";
    document.getElementById("self-edit-bio").value = p.biography || "";

    document.getElementById("doctor-profile-edit-modal").showModal();
}

async function saveDoctorSelfProfile(e) {
    e.preventDefault();
    const form = e.target;
    const body = {
        phone: form.phone.value || null,
        email: form.email.value || null,
        consultation_experience_years: form.consultation_experience_years.value ? parseInt(form.consultation_experience_years.value) : null,
        consultation_fee: form.consultation_fee.value ? parseFloat(form.consultation_fee.value) : null,
        biography: form.biography.value || null,
        linkedin_url: form.linkedin_url.value || null,
        website_url: form.website_url.value || null
    };

    try {
        await api("/doctor/my-profile", "PUT", body);
        showToast("Doctor profile updated successfully!");
        document.getElementById("doctor-profile-edit-modal").close();
        loadProfile();
    } catch (err) {
        showToast(err.message, "error");
    }
}

// Init only after the server validates the JWT and its clinical role.
async function initDoctorPortal() {
    let me;
    try {
        me = await api("/auth/me");
    } catch (error) {
        localStorage.clear();
        window.location.replace("/");
        return;
    }
    if (!me.roles.some(r => ["doctor","surgeon","telemedicine_doctor","super_admin"].includes(r))) {
        document.documentElement.style.display = "";
        document.body.innerHTML = '<main><h1>403 · Access denied</h1><p>This account cannot access the Doctor workspace.</p><a href="/">Choose another portal</a></main>';
        return;
    }
    document.documentElement.style.display = "";
    try {
        await loadProfile();
        loadDocNotifs();
        setInterval(loadDocNotifs, 30000);
    } catch (error) {
        showToast(error.message || "Unable to load the workspace", "error");
    }
}

async function callNextPatient(tokenId) {
    try {
        await api(`/receptionist/queue/${tokenId}/status?new_status=called`, "PUT");
        showToast("Patient called. Waiting for the patient to enter the room.");
        await loadDoctorQueue();
    } catch (err) { showToast(err.message, "error"); }
}
initDoctorPortal();
