"use strict";
const $=id=>document.getElementById(id);
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const money=v=>Number(v||0).toFixed(2);
let view="dashboard",profile,appointments=[],doctors=[];
async function api(path,method="GET",body){const response=await fetch(`/api/v1/patient-portal${path}`,{method,headers:{Authorization:`Bearer ${localStorage.getItem("hms_token")}`,"Content-Type":"application/json"},...(body?{body:JSON.stringify(body)}:{})});if(response.status===401){localStorage.clear();location.assign("/");throw Error("Session expired");}const data=await response.json();if(!response.ok)throw Error(typeof data.detail==="string"?data.detail:JSON.stringify(data.detail));return data;}
function table(rows,columns,action){if(!rows.length)return '<p class="muted">No records available.</p>';return `<div class="table-wrap"><table><thead><tr>${columns.map(c=>`<th>${c[0]}</th>`).join("")}${action?"<th>Actions</th>":""}</tr></thead><tbody>${rows.map((r,i)=>`<tr>${columns.map(c=>`<td>${esc(r[c[1]])}</td>`).join("")}${action?`<td>${action(r,i)}</td>`:""}</tr>`).join("")}</tbody></table></div>`;}
function field(name,label,type="text",value="",extra=""){return `<label>${esc(label)}<input name="${name}" type="${type}" value="${esc(value)}" required ${extra}></label>`;}
function select(name,label,rows,key,text){return `<label>${label}<select name="${name}" required>${rows.map(r=>`<option value="${esc(r[key])}">${esc(r[text])}</option>`).join("")}</select></label>`;}
function modal(title,html,save){$("dialog-title").textContent=title;$("fields").innerHTML=html;$("form-error").textContent="";$("dialog").showModal();$("form").onsubmit=async e=>{e.preventDefault();try{await save(Object.fromEntries(new FormData(e.target)));$("dialog").close();await render();$("message").textContent="Saved successfully.";}catch(error){$("form-error").textContent=error.message;}};}
async function render(){$("content").setAttribute("aria-busy","true");$("message").textContent="";try{
  if(view==="dashboard"){const [a,r,p,b]=await Promise.all([api("/appointments"),api("/results"),api("/prescriptions"),api("/billing")]);appointments=a;const upcoming=a.filter(x=>x.status_name!=="Cancelled").slice(0,5);$("title").textContent="Patient dashboard";$("content").innerHTML=`<div class="panel"><h2>Welcome, ${esc(profile.first_name)}</h2><p>MRN: ${esc(profile.mrn)} · Blood group: ${esc(profile.blood_group_name||"Not recorded")}</p></div><div class="panel"><h2>Upcoming appointments</h2>${table(upcoming,[["Date","appointment_date"],["Time","start_time"],["Doctor","doctor_name"],["Status","status_name"]])}</div><div class="panel"><h2>Health summary</h2><p>${p.length} prescription items · ${r.laboratory.length+r.radiology.length} available results · Outstanding ₹${money(b.total_outstanding)}</p></div>`;}
  else if(view==="appointments"){[appointments,doctors]=await Promise.all([api("/appointments"),api("/doctors")]);$("title").textContent="Appointments";$("content").innerHTML=`<div class="toolbar"><button class="primary" data-action="book">Book appointment</button></div><div class="panel">${table(appointments,[["Number","appointment_number"],["Doctor","doctor_name"],["Date","appointment_date"],["Time","start_time"],["Status","status_name"]],(r,i)=>!["Cancelled","Completed","Checked-In"].includes(r.status_name)?`<button data-action="move" data-index="${i}">Reschedule</button> <button data-action="cancel" data-index="${i}">Cancel</button>`:"")}</div>`;}
  else if(view==="results"){const r=await api("/results");$("title").textContent="Test results";$("content").innerHTML=`<div class="panel"><h2>Laboratory</h2>${table(r.laboratory,[["Test","test_name"],["Status","result_status"],["Approved","approved_at"],["Remarks","remarks"]])}</div><div class="panel"><h2>Radiology</h2>${table(r.radiology,[["Test","test_name"],["Status","report_status"],["Impression","impression"],["Reported","reported_at"]])}</div>`;}
  else if(view==="prescriptions"){const r=await api("/prescriptions");$("title").textContent="Prescriptions";$("content").innerHTML=`<div class="panel">${table(r,[["Prescription","prescription_number"],["Medicine","generic_name"],["Dose","dosage"],["Frequency","frequency"],["Dispensed","quantity_dispensed"],["Status","item_status"]])}</div>`;}
  else if(view==="billing"){const r=await api("/billing");$("title").textContent="Billing";$("content").innerHTML=`<div class="panel"><h2>Outstanding ₹${money(r.total_outstanding)}</h2>${table(r.invoices,[["Invoice","invoice_number"],["Date","invoice_date"],["Total","total_amount"],["Paid","paid_amount"],["Balance","balance_amount"],["Status","status_name"]])}</div>`;}
  else if(view==="history"){const r=await api("/care-history");$("title").textContent="Care history";$("content").innerHTML=`<div class="panel"><h2>Admissions</h2>${table(r.admissions,[["Admission","admission_number"],["Date","admission_date"],["Reason","admission_reason"],["Discharge summary","discharge_summary"]])}</div><div class="panel"><h2>Emergency visits</h2>${table(r.emergency,[["Date","arrival_time"],["Complaint","chief_complaint"],["Triage","triage_category"],["Disposition","disposition"]])}</div><div class="panel"><h2>Surgeries</h2>${table(r.surgeries,[["Procedure","procedure_name"],["Priority","request_priority"],["Date","scheduled_start"],["Status","request_status"],["Outcome","outcome"]])}</div>`;}
  else if(view==="notifications"){const r=await api("/notifications");$("title").textContent="Notifications";$("content").innerHTML=`<div class="panel">${table(r,[["Subject","subject"],["Message","body"],["Status","status"],["Date","created_at"]])}</div>`;}
  else{$("title").textContent="My profile";$("content").innerHTML=`<div class="panel"><h2>${esc(profile.first_name)} ${esc(profile.last_name)}</h2><p>MRN: ${esc(profile.mrn)}</p><p>Date of birth: ${esc(profile.date_of_birth)}</p><p>Gender: ${esc(profile.gender_name)}</p><p>Phone: ${esc(profile.phone||"-")}</p><p>Email: ${esc(profile.email||"-")}</p><button data-action="profile">Update contact details</button></div>`;}
}catch(error){$("message").textContent=error.message;$("content").innerHTML='<div class="panel">Unable to load this section.</div>';}finally{$("content").setAttribute("aria-busy","false");}}
async function action(name,index){const row=appointments[index];if(name==="book")return modal("Book appointment",select("doctor_id","Doctor",doctors,"doctor_id","doctor_name")+field("appointment_date","Date","date")+field("time_slot","Time","time")+field("chief_complaint","Reason for visit"),d=>api("/appointments","POST",d));if(name==="move")return modal("Reschedule appointment",field("appointment_date","New date","date",row.appointment_date)+field("time_slot","New time","time",String(row.start_time).slice(0,5)),d=>api(`/appointments/${row.appointment_id}/reschedule`,"PUT",d));if(name==="cancel")return modal("Cancel appointment",field("reason","Cancellation reason"),d=>api(`/appointments/${row.appointment_id}/cancel`,"POST",d));if(name==="profile")return modal("Update contact details",field("phone","Phone","tel",profile.phone||"")+field("email","Email","email",profile.email||""),d=>api("/me","PUT",d));}
$("navigation").onclick=e=>{const b=e.target.closest("[data-view]");if(!b)return;document.querySelectorAll("[data-view]").forEach(x=>x.classList.toggle("active",x===b));view=b.dataset.view;render();};$("content").onclick=e=>{const b=e.target.closest("[data-action]");if(b)action(b.dataset.action,Number(b.dataset.index)).catch(x=>$("message").textContent=x.message);};$("close").onclick=()=>$("dialog").close();$("refresh").onclick=render;$("logout").onclick=()=>{localStorage.clear();location.assign("/");};
(async()=>{
  const token=localStorage.getItem("hms_token");
  if(!token){location.replace("/");return;}
  let me;
  try{
    const response=await fetch("/api/v1/auth/me",{headers:{Authorization:`Bearer ${token}`}});
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
