"use strict";
const $ = id => document.getElementById(id);
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const money = value => Number(value || 0).toFixed(2);
let user, current, rows = [], catalog = [], prescriptionRows = [], bloodRows = [], marRows = [], selectedInvoice;
const modules = {
  pharmacy: {title:"Pharmacy", roles:["pharmacist"], path:"/pharmacist"},
  laboratory: {title:"Laboratory", roles:["lab_technician"], path:"/lab"},
  inpatient: {title:"Nursing & inpatient care", roles:["nurse","icu_staff"], path:"/nurse"},
  billing: {title:"Billing & payments", roles:["accountant","insurance_officer"], path:"/accounts"},
  radiology: {title:"Radiology", roles:["radiologist"], path:"/radiology"},
  blood: {title:"Blood bank", roles:["blood_bank_technician"], path:"/blood-bank"},
  emergency: {title:"Emergency department", roles:["emergency_staff","nurse","doctor"], path:"/emergency"},
  surgery: {title:"Surgery & operation theatre", roles:["surgeon","doctor","ot_nurse","anesthesiologist","nurse"], path:"/surgery"},
};
async function api(path, method="GET", body) {
  const response = await fetch(`/api/v1${path}`, {method, headers:{"Authorization":`Bearer ${localStorage.getItem("hms_token")}`,"Content-Type":"application/json"}, ...(body ? {body:JSON.stringify(body)} : {})});
  if(response.status === 401){localStorage.removeItem("hms_token");location.assign("/");throw Error("Session expired");}
  const data = await response.json();
  if(!response.ok) throw Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || "Request failed"));
  return data;
}
function table(data, columns, actions) {
  if(!data.length) return '<p class="muted">No records found.</p>';
  return `<div class="table-wrap"><table><thead><tr>${columns.map(([label])=>`<th>${esc(label)}</th>`).join("")}${actions?"<th>Actions</th>":""}</tr></thead><tbody>${data.map((row,index)=>`<tr>${columns.map(([,key])=>`<td>${esc(row[key])}</td>`).join("")}${actions?`<td>${actions(row,index)}</td>`:""}</tr>`).join("")}</tbody></table></div>`;
}
function field(name, label, type="text", value="", extra="") {
  return `<label>${esc(label)}<input name="${name}" type="${type}" value="${esc(value)}" required ${extra}></label>`;
}
function options(name,label,data,key,text){return `<label>${esc(label)}<select name="${name}" required>${data.map(r=>`<option value="${esc(r[key])}">${esc(r[text])}</option>`).join("")}</select></label>`;}
function modal(title, html, save) {
  $("dialog-title").textContent=title;$("fields").innerHTML=html;$("form-error").textContent="";
  $("submit").disabled=false;$("dialog").showModal();
  $("action-form").onsubmit=async event=>{
    event.preventDefault();$("submit").disabled=true;$("form-error").textContent="";
    try{await save(Object.fromEntries(new FormData(event.target)));$("dialog").close();await render();$("message").textContent="Saved successfully.";}
    catch(error){$("form-error").textContent=error.message;}finally{$("submit").disabled=false;}
  };
}
async function render(){
  $("message").textContent="";$("content").setAttribute("aria-busy","true");$("refresh").disabled=true;
  try {
    $("title").textContent=modules[current].title;
    if(current==="billing"){
      rows=await api("/billing/invoices");
      $("content").innerHTML=`<div class="toolbar"><button class="primary" data-action="invoice">Create invoice</button><button data-action="financialReport">Financial summary</button></div><div class="panel">${table(rows,[["Invoice","invoice_number"],["Patient","patient_name"],["MRN","mrn"],["Total","total_amount"],["Balance","balance_amount"],["Status","status_name"]],(r,i)=>`<button data-action="view" data-index="${i}">Open</button>`)}</div><div id="invoice-detail"></div>`;
    }else if(current==="pharmacy"){
      [rows,catalog]=await Promise.all([api("/pharmacy/inventory"),api("/pharmacy/drugs")]);
      prescriptionRows=await api("/worklists/prescriptions");
      $("content").innerHTML=`<div class="toolbar"><button class="primary" data-action="stock">Receive stock</button><button data-action="dispense">Dispense without prescription</button></div><div class="panel"><h2>Inventory</h2>${table(rows,[["Drug","generic_name"],["Available","available_quantity"],["Reorder level","reorder_level"],["Low stock","is_low_stock"]])}</div><div class="panel"><h2>Prescription queue</h2>${table(prescriptionRows,[["Patient","patient_name"],["MRN","mrn"],["Medicine","generic_name"],["Dosage","dosage"],["Remaining","quantity_remaining"],["Status","item_status"]],(r,i)=>Number(r.quantity_remaining)>0?`<button class="primary" data-action="dispenseRx" data-index="${i}">Dispense</button>`:"Completed")}</div>`;
    }else if(current==="laboratory"){
      [rows,catalog]=await Promise.all([api("/worklists/laboratory"),api("/laboratory/tests")]);
      const labActions=(r,i)=>r.order_status==="Ordered"?`<button data-action="sample" data-index="${i}">Collect sample</button>`:r.order_status==="Sample Collected"?`<button class="primary" data-action="result" data-index="${i}">Enter results</button>`:r.result_entry_id?`<button data-action="labReport" data-index="${i}">View report</button>`:"";
      $("content").innerHTML=`<div class="toolbar"><select id="lab-status"><option value="">All statuses</option><option>Ordered</option><option>Sample Collected</option><option>In Analysis</option><option>Completed</option></select></div><div class="panel"><div id="lab-table">${table(rows,[["Order","order_number"],["Patient","patient_name"],["MRN","mrn"],["Test","test_name"],["Status","order_status"],["Result","result_status"]],labActions)}</div></div><div id="lab-report"></div>`;
      $("lab-status").onchange=event=>{$("lab-table").innerHTML=table(rows.filter(r=>!event.target.value||r.order_status===event.target.value),[["Order","order_number"],["Patient","patient_name"],["MRN","mrn"],["Test","test_name"],["Status","order_status"],["Result","result_status"]],labActions);};
    }else if(current==="inpatient"){
      const beds=await api("/inpatient/beds");[rows,bloodRows]=await Promise.all([api("/inpatient/admissions"),api("/blood-bank/requests?status_filter=issued")]);
      $("content").innerHTML=`<div class="toolbar"><button data-action="round" class="primary">Record nursing round</button></div><div class="panel"><h2>Active admissions</h2>${table(rows,[["Admission","admission_number"],["Patient","patient_name"],["MRN","mrn"],["Bed","bed_number"]],(r,i)=>`<button data-action="openMar" data-index="${i}">Open MAR</button> <button data-action="discharge" data-index="${i}">Discharge</button>`)}</div><div id="mar-panel"></div><div class="panel"><h2>Blood units ready for transfusion</h2>${table(bloodRows,[["Patient","patient_name"],["MRN","mrn"],["Group","blood_group"],["Component","component_name"],["Unit","unit_number"]],(r,i)=>`<button class="primary" data-action="transfuse" data-index="${i}">Record transfusion</button>`)}</div><div class="panel"><h2>Bed availability</h2>${table(beds,[["Ward","ward_name"],["Room","room_number"],["Bed","bed_number"],["Status","status"]])}</div>`;
    }else if(current==="radiology"){
      [rows,catalog]=await Promise.all([api("/worklists/radiology"),api("/radiology/rooms")]);
      const buttons=(r,i)=>{
        if(r.report_id)return `<button data-action="viewReport" data-index="${i}">View report</button>`;
        if(r.study_id)return `<button class="primary" data-action="reportStudy" data-index="${i}">Enter report</button>`;
        if(r.radiology_appointment_id)return `<button class="primary" data-action="startStudy" data-index="${i}">Complete imaging</button>`;
        return `<button class="primary" data-action="scheduleStudy" data-index="${i}">Schedule</button>`;
      };
      $("content").innerHTML=`<div class="panel"><h2>Radiology worklist</h2>${table(rows,[["Order","order_number"],["Patient","patient_name"],["MRN","mrn"],["Test","test_name"],["Status","order_status"],["Scheduled","scheduled_start"]],buttons)}</div><div id="report-detail"></div>`;
    }else if(current==="surgery"){
      [rows,catalog]=await Promise.all([api("/surgery/worklist"),api("/surgery/options")]);
      const actions=(r,i)=>{
        if(!r.surgery_schedule_id)return `<button class="primary" data-action="scheduleSurgery" data-index="${i}">Schedule</button>`;
        if(r.request_status==="Scheduled")return `<button class="primary" data-action="preop" data-index="${i}">Pre-op checklist</button>`;
        if(r.request_status==="Pre-op Cleared")return `<button class="primary" data-action="startSurgery" data-index="${i}">Start case</button>`;
        if(r.request_status==="In Progress")return `<button data-action="consumable" data-index="${i}">Add consumable</button> <button class="primary" data-action="completeSurgery" data-index="${i}">Operation note</button>`;
        if(r.request_status==="Recovery")return `<button class="primary" data-action="recovery" data-index="${i}">Recovery assessment</button>`;
        return "Completed";
      };
      $("content").innerHTML=`<div class="toolbar"><button class="primary" data-action="requestSurgery">New surgery request</button></div><div class="panel"><h2>OT worklist</h2>${table(rows,[["Priority","request_priority"],["Patient","patient_name"],["MRN","mrn"],["Procedure","procedure_name"],["Theatre","ot_room_number"],["Start","scheduled_start"],["Status","request_status"]],actions)}</div>`;
    }else if(current==="emergency"){
      rows=await api("/emergency/queue");
      const actions=(r,i)=>`<button data-action="emergencyVitals" data-index="${i}">Vitals</button> <button data-action="emergencyNote" data-index="${i}">Clinical note</button> <button class="primary" data-action="emergencyDisposition" data-index="${i}">Disposition</button>`;
      $("content").innerHTML=`<div class="toolbar"><button class="primary" data-action="emergencyArrival">Register arrival</button><button data-action="emergencyTriage">Triage arrival</button></div><div class="panel"><h2>Priority queue</h2>${table(rows,[["ESI","esi_level"],["Patient","patient_name"],["MRN","mrn"],["Complaint","chief_complaint"],["Location","trauma_bay_code"],["Arrived","arrival_time"]],actions)}</div>`;
    }else{
      [catalog,rows]=await Promise.all([api("/blood-bank/inventory"),api("/blood-bank/requests")]);
      const actions=(r,i)=>r.status==="pending"?`<button class="primary" data-action="crossmatch" data-index="${i}">Cross-match</button>`:r.status==="crossmatched"?`<button class="primary" data-action="issueBlood" data-index="${i}">Issue unit</button>`:"";
      $("content").innerHTML=`<div class="panel"><h2>Blood requests</h2>${table(rows,[["Patient","patient_name"],["MRN","mrn"],["Group","blood_group"],["Component","component_name"],["Units","units_requested"],["Urgency","urgency"],["Status","status"]],actions)}</div><div class="panel"><h2>Available inventory</h2>${table(catalog,[["Unit","unit_number"],["Group","blood_group"],["Component","component_name"],["Expiry","expiry_date"],["Status","status"]])}</div>`;
    }
  }catch(error){$("message").textContent=error.message;$("content").innerHTML="<p>Unable to load workspace. Use Refresh to retry.</p>";}
  finally{$("content").setAttribute("aria-busy","false");$("refresh").disabled=false;}
}
async function choosePatient(){
  modal("Find patient",field("query","Search by name or MRN")+'<button type="button" id="search-patient">Search</button><div id="patient-results"></div>',async()=>{throw Error("Select a patient from search results.");});
  return new Promise(resolve=>{
    $("dialog").addEventListener("close",()=>resolve(null),{once:true});
    $("search-patient").onclick=async()=>{
      try{
        const found=await api(`/patients/?q=${encodeURIComponent($("action-form").elements.query.value)}`);
        $("patient-results").replaceChildren();
        found.forEach(p=>{const b=document.createElement("button");b.type="button";b.textContent=`${p.mrn} — ${p.first_name} ${p.last_name || ""}`;b.onclick=()=>{resolve(p);$("dialog").close();};$("patient-results").append(b);});
        if(!found.length)$("patient-results").textContent="No matching patients.";
      }catch(error){$("form-error").textContent=error.message;}
    };
  });
}
async function showInvoice(id){
  selectedInvoice=await api(`/billing/invoices/${id}`);const r=selectedInvoice;
  $("invoice-detail").innerHTML=`<div class="panel"><h2>${esc(r.invoice_number)}</h2><p>${esc(r.patient_name)} · ${esc(r.mrn)}</p>${table(r.items,[["Description","item_name"],["Quantity","quantity"],["Unit price","unit_price"],["Amount","line_total"]])}<p class="totals">Total: ${money(r.total_amount)}<br>Paid: ${money(r.paid_amount)} · Balance: ${money(r.balance_amount)}</p><h2>Payment history</h2>${table(r.payments,[["Method","method_name"],["Reference","payment_reference"],["Amount","payment_amount"],["Date","payment_date"]])}<div class="toolbar">${Number(r.balance_amount)>0?'<button class="primary" data-action="pay">Record payment</button><button data-action="credit">Credit note</button><button data-action="claim">Insurance claim</button>':''}${r.payments.length?'<button data-action="refund">Refund</button>':''}${Number(r.paid_amount)===0&&r.status_name!=="Cancelled"?'<button data-action="cancelInvoice">Cancel invoice</button>':''}<button data-action="print">Print</button></div></div>`;
}
async function action(name,index){
  const row=name==="transfuse"?bloodRows[index]:name==="recordDose"?marRows[index]:rows[index];
  if(name==="view")return showInvoice(row.invoice_id);
  if(name==="print")return window.print();
  if(name==="pay"){
    const id=selectedInvoice.invoice_id;
    return modal("Record payment",field("amount","Amount","number",selectedInvoice.balance_amount,'min="0.01" step="0.01"')+options("method","Payment method",["Cash","Credit Card","Debit Card","UPI","Net Banking","Insurance"].map(v=>({v})),"v","v")+field("reference","Receipt / transaction reference","text",crypto.randomUUID()),data=>api(`/billing/invoices/${id}/payments`,"POST",data));
  }
  if(name==="invoice"){
    const patient=await choosePatient();if(!patient)return;
    modal(`Create invoice · ${patient.mrn}`,'<div id="invoice-lines"></div><button type="button" id="add-line">Add charge</button>'+field("tax_amount","Tax amount","number","0",'min="0" step="0.01"')+field("discount_amount","Discount amount","number","0",'min="0" step="0.01"'),data=>{
      const items=[...document.querySelectorAll(".line")].map(el=>({item_name:el.querySelector('[data-field="name"]').value,quantity:el.querySelector('[data-field="quantity"]').value,unit_price:el.querySelector('[data-field="price"]').value}));
      return api("/billing/invoices","POST",{patient_id:patient.patient_id,items,tax_amount:data.tax_amount,discount_amount:data.discount_amount});
    });
    const add=()=>{const div=document.createElement("div");div.className="line";div.innerHTML='<input data-field="name" aria-label="Charge description" placeholder="Charge description" required><input data-field="quantity" aria-label="Quantity" type="number" min="0.01" step="0.01" value="1" required><input data-field="price" aria-label="Unit price" type="number" min="0" step="0.01" placeholder="Unit price" required><button type="button">Remove</button>';div.querySelector("button").onclick=()=>div.remove();$("invoice-lines").append(div);};$("add-line").onclick=add;add();return;
  }
  if(name==="stock")return modal("Receive stock",options("drug_id","Drug",catalog,"drug_id","generic_name")+field("batch_number","Batch number")+field("expiry_date","Expiry date","date")+field("quantity_received","Quantity","number","",'min="0.01" step="0.01"')+field("purchase_price","Purchase price","number","0",'min="0" step="0.01"')+field("selling_price","Selling price","number","0",'min="0" step="0.01"'),data=>api("/pharmacy/batches","POST",data));
  if(name==="dispense"){
    const patient=await choosePatient();if(!patient)return;
    const batches=rows.flatMap(inv=>inv.batches.filter(b=>!b.is_expired&&b.quantity_remaining>0).map(b=>({...b,label:`${inv.generic_name} · ${b.batch_number} · ${b.quantity_remaining} available`})));
    if(!batches.length)throw Error("No unexpired stock is available.");
    return modal(`Dispense · ${patient.mrn}`,options("batch_id","Stock batch",batches,"batch_id","label")+field("quantity_dispensed","Quantity","number","1",'min="0.01" step="0.01"'),data=>api("/pharmacy/dispense","POST",{patient_id:patient.patient_id,dispensing_reference:crypto.randomUUID(),items:[{...data,drug_id:batches.find(b=>b.batch_id===data.batch_id).drug_id}]}));
  }
  if(name==="cancelInvoice")return modal("Cancel invoice",field("reason","Cancellation reason"),d=>api(`/billing/invoices/${selectedInvoice.invoice_id}/cancel`,"POST",d));
  if(name==="credit")return modal("Credit note",field("amount","Amount","number",selectedInvoice.balance_amount,'min="0.01" step="0.01"')+field("reason","Reason"),d=>api(`/billing/invoices/${selectedInvoice.invoice_id}/credit-notes`,"POST",d));
  if(name==="refund")return modal("Refund",options("payment_id","Payment",selectedInvoice.payments.map(p=>({...p,label:`${p.method_name} · ${p.payment_amount}`})),"payment_id","label")+field("amount","Amount","number","",'min="0.01" step="0.01"')+field("reference","Reference","text",crypto.randomUUID())+field("reason","Reason"),d=>api(`/billing/invoices/${selectedInvoice.invoice_id}/refunds`,"POST",d));
  if(name==="claim")return modal("Insurance claim",field("insurance_provider","Provider")+field("policy_number","Policy number")+field("claim_number","Claim number")+field("claim_amount","Amount","number",selectedInvoice.balance_amount,'min="0.01" step="0.01"'),d=>api(`/billing/invoices/${selectedInvoice.invoice_id}/claims`,"POST",d));
  if(name==="financialReport"){const r=await api("/billing/reports/summary");$("invoice-detail").innerHTML=`<div class="panel"><h2>Financial summary</h2><p class="totals">Revenue: ${money(r.totals.revenue)}<br>Collected: ${money(r.totals.collected)}<br>Outstanding: ${money(r.totals.outstanding)}</p>${table(r.payment_methods,[["Payment method","method_name"],["Net collected","net_collected"]])}${table(r.services,[["Service","item_type"],["Revenue","revenue"]])}<button data-action="print">Print report</button></div>`;return;}
  if(name==="dispenseRx"){
    const rx=prescriptionRows[index];
    const batches=rows.flatMap(inv=>inv.drug_id===rx.drug_id?inv.batches.filter(b=>!b.is_expired&&Number(b.quantity_remaining)>0).map(b=>({...b,label:`${b.batch_number} · ${b.quantity_remaining} available`})) : []);
    if(!batches.length)throw Error(`No unexpired stock is available for ${rx.generic_name}.`);
    return modal(`Dispense prescription · ${rx.mrn}`,options("batch_id","Stock batch",batches,"batch_id","label")+field("quantity_dispensed","Quantity","number",rx.quantity_remaining,`min="0.01" max="${esc(rx.quantity_remaining)}" step="0.01"`),data=>api("/pharmacy/dispense","POST",{patient_id:rx.patient_id,prescription_id:rx.prescription_id,dispensing_reference:crypto.randomUUID(),items:[{drug_id:rx.drug_id,prescription_item_id:rx.prescription_item_id,batch_id:data.batch_id,quantity_dispensed:data.quantity_dispensed}]}));
  }
  if(name==="sample")return modal(`Collect sample · ${row.mrn}`,field("sample_type","Sample type","text","Venous Blood"),data=>api("/laboratory/collect-sample","POST",{...data,order_item_id:row.order_item_id}));
  if(name==="result"){
    const test=catalog.find(t=>t.test_id===row.test_id);if(!test?.parameters.length)throw Error("Configure test parameters before entering results.");
    return modal(`Results · ${row.test_name}`,test.parameters.map((p,i)=>field(`p${i}`,`${p.parameter_name} (${p.unit}) · Reference: ${p.normal_range}`)+options(`f${i}`,"Result flag",["Normal","High","Low","Critical"].map(v=>({v})),"v","v")).join(""),data=>api("/laboratory/results","POST",{order_item_id:row.order_item_id,parameters:test.parameters.map((p,i)=>({parameter_id:p.parameter_id,result_value:data[`p${i}`],result_flag:data[`f${i}`]}))}));
  }
  if(name==="labReport"){
    const report=await api(`/laboratory/results/${row.result_entry_id}`);
    const flags=report.parameters.some(p=>p.result_flag!=="Normal");
    $("lab-report").innerHTML=`<div class="panel"><h2>${esc(report.test_name)}</h2><p><strong>Status:</strong> ${esc(report.result_status)}${flags?' · ⚠ Abnormal result':''}</p>${table(report.parameters,[["Parameter","parameter_name"],["Result","result_value"],["Unit","unit"],["Reference range","normal_range"],["Flag","result_flag"]])}<p>Entered: ${esc(report.entered_at)}<br>Approved: ${esc(report.approved_at||"Awaiting doctor approval")}</p><button data-action="print">Print report</button></div>`;return;
  }
  if(name==="scheduleStudy"){
    if(!catalog.length)throw Error("No imaging rooms are configured.");
    return modal(`Schedule · ${row.test_name}`,options("imaging_room_id","Imaging room",catalog,"imaging_room_id","room_name")+field("scheduled_start","Start","datetime-local")+field("scheduled_end","End","datetime-local"),data=>api("/radiology/schedule","POST",{...data,order_item_id:row.order_item_id}));
  }
  if(name==="startStudy")return modal(`Complete imaging · ${row.test_name}`,field("study_description","Study description","text",row.test_name),data=>api("/radiology/studies","POST",{...data,radiology_appointment_id:row.radiology_appointment_id}));
  if(name==="reportStudy")return modal(`Final report · ${row.test_name}`,field("findings","Findings")+field("impression","Impression"),data=>api("/radiology/reports","POST",{...data,study_id:row.study_id}));
  if(name==="viewReport"){
    $("report-detail").innerHTML=`<div class="panel"><h2>${esc(row.test_name)} · Final report</h2><p><strong>Patient:</strong> ${esc(row.patient_name)} (${esc(row.mrn)})</p><p><strong>Impression:</strong> ${esc(row.impression)}</p><button data-action="print">Print report</button></div>`;
    return;
  }
  if(name==="crossmatch"){
    const units=catalog.filter(u=>u.blood_group===row.blood_group&&u.component_name===row.component_name);
    if(!units.length)throw Error(`No available ${row.blood_group} ${row.component_name} units.`);
    return modal(`Cross-match · ${row.mrn}`,options("blood_unit_id","Blood unit",units,"blood_unit_id","unit_number")+options("compatibility_result","Result",["Compatible","Incompatible"].map(v=>({v})),"v","v"),data=>api("/blood-bank/cross-match","POST",{...data,blood_request_id:row.blood_request_id}));
  }
  if(name==="issueBlood")return modal(`Issue unit · ${row.unit_number}`,`<p>Issue compatible unit ${esc(row.unit_number)} to ${esc(row.patient_name)}?</p>`,()=>api("/blood-bank/issue","POST",{blood_request_id:row.blood_request_id,blood_unit_id:row.blood_unit_id}));
  if(name==="transfuse")return modal(`Record transfusion · ${row.unit_number}`,field("volume_transfused","Volume transfused (ml)","number","350",'min="1"')+options("adverse_reaction","Adverse reaction",[{v:"false",label:"No"},{v:"true",label:"Yes"}],"v","label")+'<label>Reaction details<input name="reaction_details" type="text"></label>'+field("notes","Clinical notes","text","No immediate adverse transfusion reactions observed."),data=>api("/blood-bank/transfusions","POST",{...data,reaction_details:data.reaction_details||null,adverse_reaction:data.adverse_reaction==="true",blood_request_id:row.blood_request_id,blood_unit_id:row.blood_unit_id}));
  if(name==="round")return modal("Record nursing round",options("patient_id","Patient",rows,"patient_id","patient_name")+field("round_notes","Observations")+field("vital_signs_summary","Recorded vitals"),data=>api("/nursing/rounds","POST",data));
  if(name==="discharge")return modal(`Discharge · ${row.mrn}`,field("discharge_summary","Discharge summary")+options("discharge_disposition","Disposition",["Home","Transferred","Deceased"].map(v=>({v})),"v","v"),data=>api("/inpatient/discharges","POST",{...data,admission_id:row.admission_id}));
  if(name==="openMar"){
    marRows=await api(`/nursing/patients/${row.patient_id}/mar`);const act=(d,i)=>["Due","Overdue"].includes(d.administration_status)?`<button class="primary" data-action="recordDose" data-index="${i}">Record</button>`:"";
    $("mar-panel").innerHTML=`<div class="panel"><h2>MAR · ${esc(row.patient_name)}</h2>${table(marRows,[["Medicine","medicine_name"],["Dose","dosage"],["Frequency","frequency"],["Route","route"],["Scheduled","scheduled_time"],["Status","administration_status"],["Allergy","allergy_warning"]],act)}</div>`;return;
  }
  if(name==="recordDose")return modal(`Medication dose · ${row.medicine_name}`,options("administration_status","Status",["Administered","Missed","Refused","Withheld","Unavailable"].map(v=>({v})),"v","v")+field("dosage_given","Dosage","text",row.dosage)+field("route","Route","text",row.route)+'<label>Reason when not administered<input name="exception_reason"></label><label>Notes<input name="notes"></label>',data=>api("/nursing/administer-medication","POST",{...data,mar_id:row.mar_id,patient_id:row.patient_id,prescription_item_id:row.prescription_item_id,medicine_name:row.medicine_name,exception_reason:data.exception_reason||null,notes:data.notes||null}));
  if(name==="emergencyArrival"){
    const patient=await choosePatient();if(!patient)return;
    return modal("Register emergency arrival",options("arrival_mode","Arrival mode",["Walk-in","Ambulance","Police","Transfer"].map(v=>({v})),"v","v")+field("brought_by","Brought by","text","Family")+field("arrival_condition","Arrival condition"),data=>api("/emergency/arrivals","POST",{...data,patient_id:patient.patient_id}));
  }
  if(name==="emergencyTriage"){
    const patient=await choosePatient();if(!patient)return;
    const arrivals=await api(`/emergency/untriaged?patient_id=${patient.patient_id}`);
    if(!arrivals.length)throw Error("No untriaged emergency arrival exists for this patient.");
    return modal("Emergency triage",options("emergency_arrival_id","Arrival",arrivals,"emergency_arrival_id","arrival_label")+options("esi_level","ESI severity",[1,2,3,4,5].map(v=>({v,label:`ESI ${v}`})),"v","label")+field("chief_complaint","Chief complaint")+'<label>Vital signs summary<input name="vital_signs_summary"></label><label>Care location<input name="trauma_bay_code"></label>',data=>api("/emergency/triage","POST",{...data,esi_level:Number(data.esi_level),vital_signs_summary:data.vital_signs_summary||null,trauma_bay_code:data.trauma_bay_code||null}));
  }
  if(name==="emergencyVitals")return modal(`Vitals · ${row.patient_name}`,field("temperature","Temperature °C","number","37",'step="0.1"')+field("pulse_rate","Pulse","number","80")+field("respiratory_rate","Respiratory rate","number","18")+field("systolic_bp","Systolic BP","number","120")+field("diastolic_bp","Diastolic BP","number","80")+field("oxygen_saturation","Oxygen saturation %","number","98",'step="0.1"'),data=>api("/emergency/vitals","POST",{...Object.fromEntries(Object.entries(data).map(([k,v])=>[k,Number(v)])),emergency_encounter_id:row.emergency_encounter_id}));
  if(name==="emergencyNote")return modal(`Clinical note · ${row.patient_name}`,options("note_type","Type",["Assessment","Treatment","Procedure","Observation"].map(v=>({v})),"v","v")+field("note_text","Clinical note"),data=>api("/emergency/notes","POST",{...data,emergency_encounter_id:row.emergency_encounter_id}));
  if(name==="emergencyDisposition"){
    const choices=await api("/emergency/admission-options");
    const admissionFields=choices.beds.length&&choices.doctors.length?`<fieldset><legend>Required when admitted</legend>${options("doctor_id","Attending doctor",choices.doctors,"doctor_id","label")}${options("bed_id","Available bed",choices.beds,"bed_id","label")}</fieldset>`:"";
    return modal(`Disposition · ${row.patient_name}`,options("disposition","Disposition",["Discharged","Admitted","Transferred","Deceased"].map(v=>({v})),"v","v")+field("notes","Disposition summary")+admissionFields,data=>api(`/emergency/encounters/${row.emergency_encounter_id}/disposition`,"POST",{...data,doctor_id:data.disposition==="Admitted"?data.doctor_id:null,bed_id:data.disposition==="Admitted"?data.bed_id:null}));
  }
  if(name==="requestSurgery"){
    const patient=await choosePatient();if(!patient)return;
    return modal("New surgery request",field("procedure_name","Procedure")+field("procedure_code","Procedure code")+options("urgency","Priority",["Emergency","Urgent","Elective"].map(v=>({v})),"v","v")+field("clinical_indication","Clinical indication")+field("estimated_charge","Estimated procedure charge","number","0",'min="0" step="0.01"'),data=>api("/surgery/requests","POST",{...data,patient_id:patient.patient_id,estimated_charge:Number(data.estimated_charge)}));
  }
  if(name==="scheduleSurgery")return modal(`Schedule · ${row.patient_name}`,options("ot_room_number","Operating theatre",catalog.rooms.map(v=>({v})),"v","v")+options("primary_surgeon_id","Primary surgeon",catalog.doctors,"doctor_id","label")+field("anesthesiologist_name","Anesthesiologist")+field("scheduled_start","Start","datetime-local")+field("scheduled_end","End","datetime-local"),data=>api("/surgery/schedule","POST",{...data,surgery_request_id:row.surgery_request_id}));
  if(name==="preop"){
    const yesNo=label=>options(label.toLowerCase().replaceAll(" ","_"),label,[{v:"true",label:"Verified"},{v:"false",label:"Not verified"}],"v","label");
    return modal(`Pre-operative checklist · ${row.patient_name}`,yesNo("Consent verified")+yesNo("Identity verified")+yesNo("Surgical site verified")+yesNo("Allergies reviewed")+yesNo("Investigations reviewed")+yesNo("Fasting confirmed")+yesNo("Anesthesia cleared")+field("asa_classification","ASA classification","text","ASA II")+'<label>Notes<input name="notes"></label>',data=>api(`/surgery/requests/${row.surgery_request_id}/preoperative-checklist`,"POST",data));
  }
  if(name==="startSurgery")return modal(`Start case · ${row.patient_name}`,field("anesthesia_type","Anesthesia type","text","General anesthesia"),data=>api(`/surgery/cases/${row.surgery_schedule_id}/start`,"POST",data));
  if(name==="consumable")return modal("Add consumable or implant",field("item_name","Item")+field("quantity","Quantity","number","1",'min="0.01" step="0.01"')+field("unit_price","Unit price","number","0",'min="0" step="0.01"'),data=>api(`/surgery/cases/${row.surgery_schedule_id}/consumables`,"POST",data));
  if(name==="completeSurgery")return modal(`Operation note · ${row.patient_name}`,field("surgical_findings","Surgical findings")+field("outcome","Outcome","text","Successful - transferred to PACU")+field("complications","Complications","text","None"),data=>api(`/surgery/cases/${row.surgery_schedule_id}/complete`,"POST",data));
  if(name==="recovery")return modal(`Recovery · ${row.patient_name}`,options("recovery_status","Recovery status",["Stable","Needs Observation","Critical"].map(v=>({v})),"v","v")+field("pain_score","Pain score (0-10)","number","2",'min="0" max="10"')+field("observations","Recovery observations")+options("disposition","Disposition",["Ward","ICU","Discharged"].map(v=>({v})),"v","v"),data=>api(`/surgery/cases/${row.surgery_schedule_id}/recovery`,"POST",{...data,pain_score:Number(data.pain_score)}));
}
$("content").onclick=event=>{const button=event.target.closest("[data-action]");if(button)action(button.dataset.action,Number(button.dataset.index)).catch(error=>{$("message").textContent=error.message;});};
$("close-dialog").onclick=()=>$("dialog").close();$("refresh").onclick=render;
$("logout").onclick=()=>{Object.keys(localStorage).filter(k=>k.startsWith("hms_")).forEach(k=>localStorage.removeItem(k));location.assign("/");};
(async()=>{
  try{
    user=await api("/auth/me");$("user").textContent=user.name || user.username;
    const requested=document.body.dataset.workspace;
    const workspace=modules[requested];
    if(!workspace || workspace.path!==location.pathname){
      $("content").textContent="This workspace is not configured correctly.";
      return;
    }
    const authorized=user.roles.some(role=>workspace.roles.includes(role)||["admin","super_admin"].includes(role));
    if(!authorized){
      $("title").textContent="Access denied";
      $("message").textContent=`Your account cannot access the ${workspace.title} workspace.`;
      $("content").innerHTML='<div class="panel"><h2>403 · Access denied</h2><p>Sign in with an account assigned to this department.</p></div>';
      $("content").setAttribute("aria-busy","false");
      $("refresh").hidden=true;
      return;
    }
    current=requested;
    const label=document.createElement("span");label.textContent=workspace.title;label.className="active";$("navigation").append(label);
    await render();
  }catch(error){$("message").textContent=error.message;}
})();
