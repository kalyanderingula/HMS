"use strict";
const $=id=>document.getElementById(id);
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const money=v=>Number(v||0).toFixed(2);
let view="dashboard",profile,appointments=[],doctors=[];
async function api(path,method="GET",body){const response=await fetch(`/api/v1/patient-portal${path}`,{method,headers:{"Content-Type":"application/json"},...(body?{body:JSON.stringify(body)}:{})});if(response.status===401){localStorage.clear();location.assign("/");throw Error("Session expired");}const data=await response.json();if(!response.ok)throw Error(typeof data.detail==="string"?data.detail:JSON.stringify(data.detail));return data;}
function table(rows,columns,action){if(!rows.length)return '<p class="muted">No records available.</p>';return `<div class="table-wrap"><table><thead><tr>${columns.map(c=>`<th>${c[0]}</th>`).join("")}${action?"<th>Actions</th>":""}</tr></thead><tbody>${rows.map((r,i)=>`<tr>${columns.map(c=>`<td>${esc(r[c[1]])}</td>`).join("")}${action?`<td>${action(r,i)}</td>`:""}</tr>`).join("")}</tbody></table></div>`;}
function field(name,label,type="text",value="",extra=""){return `<label>${esc(label)}<input name="${name}" type="${type}" value="${esc(value)}" required ${extra}></label>`;}
function select(name,label,rows,key,text){return `<label>${label}<select name="${name}" required>${rows.map(r=>`<option value="${esc(r[key])}">${esc(r[text])}</option>`).join("")}</select></label>`;}
function modal(title,html,save){$("dialog-title").textContent=title;$("fields").innerHTML=html;$("form-error").textContent="";$("dialog").showModal();$("form").onsubmit=async e=>{e.preventDefault();try{await save(Object.fromEntries(new FormData(e.target)));$("dialog").close();await render();$("message").textContent="Saved successfully.";}catch(error){$("form-error").textContent=error.message;}};}
function localDate(){const now=new Date();return `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,"0")}-${String(now.getDate()).padStart(2,"0")}`;}
function bookAppointmentModal(){
  const options=doctors.map(d=>`<option value="${esc(d.doctor_id)}">${esc(d.doctor_name)}${d.specialization_name?` — ${esc(d.specialization_name)}`:""}</option>`).join("");
  $("dialog-title").textContent="Book appointment";
  $("fields").innerHTML=`<label>Appointment mode<select name="appointment_mode" required><option value="In-person">In-person consultation</option><option value="Virtual">Virtual consultation</option></select></label><label>Doctor<select name="doctor_id" id="patient-book-doctor" required><option value="">Choose doctor</option>${options}</select></label><label>Date<input name="appointment_date" id="patient-book-date" type="date" min="${localDate()}" value="${localDate()}" required></label><input name="time_slot" id="patient-book-time" type="hidden" required><div><strong>Available 15-minute times</strong><p class="muted" id="patient-slot-help">Choose a doctor to view the day sheet.</p><div id="patient-time-slots" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px;max-height:260px;overflow:auto;padding:10px;background:#f8fafc;border:1px solid #dbe5ec;border-radius:8px;"></div></div><label>Reason for visit<textarea name="chief_complaint" minlength="2" required></textarea></label>`;
  $("form-error").textContent="";
  $("dialog").showModal();
  $("patient-book-doctor").onchange=loadPatientDoctorSlots;
  $("patient-book-date").onchange=loadPatientDoctorSlots;
  $("form").onsubmit=async e=>{e.preventDefault();if(!$("patient-book-time").value){$("form-error").textContent="Select an available 15-minute time.";return;}try{await api("/appointments","POST",Object.fromEntries(new FormData(e.target)));$("dialog").close();await render();$("message").textContent="Appointment booked successfully.";}catch(error){$("form-error").textContent=error.message;await loadPatientDoctorSlots();}};
}
function rescheduleAppointmentModal(row){
  const doctor=doctors.find(item=>item.doctor_id===row.doctor_id);
  $("dialog-title").textContent="Reschedule appointment";
  $("fields").innerHTML=`<div class="panel" style="margin:8px 0;padding:12px;"><strong>${esc(doctor?.doctor_name||row.doctor_name)}</strong><br><small>${esc(doctor?.specialization_name||"")}</small></div><input id="patient-book-doctor" type="hidden" value="${esc(row.doctor_id)}"><label>New date<input name="appointment_date" id="patient-book-date" type="date" min="${localDate()}" value="${esc(row.appointment_date)}" required></label><input name="time_slot" id="patient-book-time" type="hidden" required><div><strong>Available 15-minute times</strong><p class="muted" id="patient-slot-help">Loading the doctor's schedule…</p><div id="patient-time-slots" data-exclude-appointment="${esc(row.appointment_id)}" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px;max-height:260px;overflow:auto;padding:10px;background:#f8fafc;border:1px solid #dbe5ec;border-radius:8px;"></div></div>`;
  $("form-error").textContent="";
  $("dialog").showModal();
  $("patient-book-date").onchange=loadPatientDoctorSlots;
  $("form").onsubmit=async e=>{e.preventDefault();if(!$("patient-book-time").value){$("form-error").textContent="Select an available 15-minute time.";return;}try{await api(`/appointments/${row.appointment_id}/reschedule`,"PUT",Object.fromEntries(new FormData(e.target)));$("dialog").close();await render();$("message").textContent="Appointment rescheduled successfully.";}catch(error){$("form-error").textContent=error.message;await loadPatientDoctorSlots();}};
  loadPatientDoctorSlots();
}
async function loadPatientDoctorSlots(){
  const doctor=$("patient-book-doctor").value,date=$("patient-book-date").value,box=$("patient-time-slots"),hidden=$("patient-book-time");
  hidden.value="";$("patient-slot-help").textContent=doctor&&date?"Loading the doctor's schedule…":"Choose a doctor and date to view the day sheet.";box.replaceChildren();
  if(!doctor||!date)return;
  try{const exclude=box.dataset.excludeAppointment?`&exclude_appointment_id=${box.dataset.excludeAppointment}`:"";const result=await api(`/doctors/${doctor}/availability?day=${date}${exclude}`);$("patient-slot-help").textContent="Green times are available. Your appointments, current booking, booked, and past times are red.";result.slots.forEach(slot=>{const button=document.createElement("button");button.type="button";button.disabled=!slot.available;button.innerHTML=`<strong>${esc(slot.start_time)}–${esc(slot.end_time)}</strong><small style="display:block;margin-top:3px;">${esc(slot.status)}</small>`;button.style.cssText=slot.available?"padding:9px;border-color:#86efac;background:#f0fdf4;color:#166534;":"padding:9px;border-color:#fecaca;background:#fef2f2;color:#991b1b;cursor:not-allowed;";if(slot.available)button.onclick=()=>{hidden.value=slot.start_time;box.querySelectorAll("button").forEach(item=>item.style.boxShadow="none");button.style.boxShadow="0 0 0 3px rgba(8,126,131,.3)";$("patient-slot-help").textContent=`Selected ${date}, ${slot.start_time}–${slot.end_time}`;};box.appendChild(button);});}catch(error){$("patient-slot-help").textContent=error.message;}
}
async function render(){$("content").setAttribute("aria-busy","true");$("message").textContent="";try{
  if(view==="dashboard"){const [a,r,p,b]=await Promise.all([api("/appointments"),api("/results"),api("/prescriptions"),api("/billing")]);appointments=a;const upcoming=a.filter(x=>x.status_name!=="Cancelled").slice(0,5);$("title").textContent="Patient dashboard";$("content").innerHTML=`<div class="panel"><h2>Welcome, ${esc(profile.first_name)}</h2><p>MRN: ${esc(profile.mrn)} · Blood group: ${esc(profile.blood_group_name||"Not recorded")}</p></div><div class="panel"><h2>Upcoming appointments</h2>${table(upcoming,[["Date","appointment_date"],["Time","start_time"],["Doctor","doctor_name"],["Status","status_name"]])}</div><div class="panel"><h2>Health summary</h2><p>${p.length} prescription items · ${r.laboratory.length+r.radiology.length} available results · Outstanding ₹${money(b.total_outstanding)}</p></div>`;}
  else if(view==="appointments"){[appointments,doctors]=await Promise.all([api("/appointments"),api("/doctors")]);$("title").textContent="Appointments";$("content").innerHTML=`<div class="toolbar"><button class="primary" data-action="book">Book appointment</button></div><div class="panel">${table(appointments,[["Number","appointment_number"],["Mode","appointment_mode"],["Doctor","doctor_name"],["Date","appointment_date"],["Time","start_time"],["Status","status_name"]],(r,i)=>r.appointment_mode==="Virtual"?(r.consultation_link?`<a href="${esc(r.consultation_link)}" target="_blank" rel="noopener"><button type="button" class="primary">Join virtual visit</button></a>`:""):!["Cancelled","Completed","Checked-In"].includes(r.status_name)?`<button data-action="move" data-index="${i}">Reschedule</button> <button data-action="cancel" data-index="${i}">Cancel</button>`:"")}</div>`;}
  else if(view==="results"){const r=await api("/results");$("title").textContent="Test results";$("content").innerHTML=`<div class="panel"><h2>Laboratory</h2>${table(r.laboratory,[["Test","test_name"],["Status","result_status"],["Approved","approved_at"],["Remarks","remarks"]])}</div><div class="panel"><h2>Radiology</h2>${table(r.radiology,[["Test","test_name"],["Status","report_status"],["Impression","impression"],["Reported","reported_at"]])}</div>`;}
  else if(view==="prescriptions"){const r=await api("/prescriptions");$("title").textContent="Prescriptions";$("content").innerHTML=`<div class="panel">${table(r,[["Prescription","prescription_number"],["Medicine","generic_name"],["Dose","dosage"],["Frequency","frequency"],["Dispensed","quantity_dispensed"],["Status","item_status"]])}</div>`;}
  else if(view==="billing"){const r=await api("/billing");$("title").textContent="Billing";$("content").innerHTML=`<div class="panel"><h2>Outstanding ₹${money(r.total_outstanding)}</h2>${table(r.invoices,[["Invoice","invoice_number"],["Date","invoice_date"],["Total","total_amount"],["Paid","paid_amount"],["Balance","balance_amount"],["Status","status_name"]])}</div>`;}
  else if(view==="history"){const r=await api("/care-history");$("title").textContent="Care history";$("content").innerHTML=`<div class="panel"><h2>Admissions</h2>${table(r.admissions,[["Admission","admission_number"],["Date","admission_date"],["Reason","admission_reason"],["Discharge summary","discharge_summary"]])}</div><div class="panel"><h2>Emergency visits</h2>${table(r.emergency,[["Date","arrival_time"],["Complaint","chief_complaint"],["Triage","triage_category"],["Disposition","disposition"]])}</div><div class="panel"><h2>Surgeries</h2>${table(r.surgeries,[["Procedure","procedure_name"],["Priority","request_priority"],["Date","scheduled_start"],["Status","request_status"],["Outcome","outcome"]])}</div>`;}
  else if(view==="notifications"){const r=await api("/notifications");$("title").textContent="Notifications";$("content").innerHTML=`<div class="panel">${table(r,[["Subject","subject"],["Message","body"],["Status","status"],["Date","created_at"]])}</div>`;}
  else{$("title").textContent="My profile";$("content").innerHTML=`<div class="panel"><h2>${esc(profile.first_name)} ${esc(profile.last_name)}</h2><p>MRN: ${esc(profile.mrn)}</p><p>Date of birth: ${esc(profile.date_of_birth)}</p><p>Gender: ${esc(profile.gender_name)}</p><p>Phone: ${esc(profile.phone||"-")}</p><p>Email: ${esc(profile.email||"-")}</p><button data-action="profile">Update contact details</button></div>`;}
}catch(error){$("message").textContent=error.message;$("content").innerHTML='<div class="panel">Unable to load this section.</div>';}finally{$("content").setAttribute("aria-busy","false");}}
async function action(name,index){const row=appointments[index];if(name==="book")return bookAppointmentModal();if(name==="move")return rescheduleAppointmentModal(row);if(name==="cancel")return modal("Cancel appointment",field("reason","Cancellation reason"),d=>api(`/appointments/${row.appointment_id}/cancel`,"POST",d));if(name==="profile")return modal("Update contact details",field("phone","Phone","tel",profile.phone||"")+field("email","Email","email",profile.email||""),d=>api("/me","PUT",d));}
$("navigation").onclick=e=>{const b=e.target.closest("[data-view]");if(!b)return;document.querySelectorAll("[data-view]").forEach(x=>x.classList.toggle("active",x===b));view=b.dataset.view;render();};$("content").onclick=e=>{const b=e.target.closest("[data-action]");if(b)action(b.dataset.action,Number(b.dataset.index)).catch(x=>$("message").textContent=x.message);};$("close").onclick=()=>$("dialog").close();$("refresh").onclick=render;$("logout").onclick=async()=>{try{await fetch("/api/v1/auth/logout",{method:"POST",credentials:"same-origin"});}finally{localStorage.clear();location.assign("/");}};
(async()=>{
  let me;
  try{
    const response=await fetch("/api/v1/auth/me",{credentials:"same-origin"});
    if(response.status===401){localStorage.clear();location.replace("/");return;}
    if(!response.ok)throw Error(`Unable to verify session (${response.status})`);
    me=await response.json();
  }catch(error){
    $("message").textContent=error.message||"Unable to verify the current session.";
    $("content").innerHTML='<div class="panel">The server could not verify your session. Use Refresh to try again.</div>';
    return;
  }
  if(!Array.isArray(me.roles)||!me.roles.includes("patient")){
    document.body.innerHTML='<main><div class="panel"><h1>403 · Access denied</h1><p>This page requires a patient account.</p><button id="wrong-account">Sign in with a patient account</button></div></main>';
    document.getElementById("wrong-account").onclick=()=>{localStorage.clear();location.replace("/");};
    return;
  }
  try{
    profile=await api("/me");
    $("user").textContent=`${profile.first_name} ${profile.last_name}`;
    await render();
  }catch(error){
    $("message").textContent=error.message||"Unable to load your patient record.";
    $("content").innerHTML='<div class="panel">Your session is valid, but the patient dashboard could not be loaded. Use Refresh to try again.</div>';
  }
})();
