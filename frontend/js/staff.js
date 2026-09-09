"use strict";
const $ = id => document.getElementById(id);
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const money = value => Number(value || 0).toFixed(2);
let user, current, rows = [], catalog = [], prescriptionRows = [], selectedInvoice;
const modules = {
  pharmacy: {title:"Pharmacy", roles:["pharmacist"], path:"/pharmacist"},
  laboratory: {title:"Laboratory", roles:["lab_technician"], path:"/lab"},
  inpatient: {title:"Nursing & inpatient care", roles:["nurse","icu_staff"], path:"/nurse"},
  billing: {title:"Billing & payments", roles:["accountant","insurance_officer"], path:"/accounts"},
  radiology: {title:"Radiology", roles:["radiologist"], path:"/radiology"},
  blood: {title:"Blood bank", roles:["blood_bank_technician"], path:"/blood-bank"},
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
      $("content").innerHTML=`<div class="toolbar"><button class="primary" data-action="invoice">Create invoice</button></div><div class="panel">${table(rows,[["Invoice","invoice_number"],["Patient","patient_name"],["MRN","mrn"],["Total","total_amount"],["Balance","balance_amount"],["Status","status_name"]],(r,i)=>`<button data-action="view" data-index="${i}">Open</button>`)}</div><div id="invoice-detail"></div>`;
    }else if(current==="pharmacy"){
      [rows,catalog]=await Promise.all([api("/pharmacy/inventory"),api("/pharmacy/drugs")]);
      prescriptionRows=await api("/worklists/prescriptions");
      $("content").innerHTML=`<div class="toolbar"><button class="primary" data-action="stock">Receive stock</button><button data-action="dispense">Dispense without prescription</button></div><div class="panel"><h2>Inventory</h2>${table(rows,[["Drug","generic_name"],["Available","available_quantity"],["Reorder level","reorder_level"],["Low stock","is_low_stock"]])}</div><div class="panel"><h2>Prescription queue</h2>${table(prescriptionRows,[["Patient","patient_name"],["MRN","mrn"],["Medicine","generic_name"],["Dosage","dosage"],["Remaining","quantity_remaining"],["Status","item_status"]],(r,i)=>Number(r.quantity_remaining)>0?`<button class="primary" data-action="dispenseRx" data-index="${i}">Dispense</button>`:"Completed")}</div>`;
    }else if(current==="laboratory"){
      [rows,catalog]=await Promise.all([api("/worklists/laboratory"),api("/laboratory/tests")]);
      $("content").innerHTML=`<div class="panel">${table(rows,[["Order","order_number"],["Patient","patient_name"],["MRN","mrn"],["Test","test_name"],["Status","order_status"]],(r,i)=>`<button data-action="sample" data-index="${i}">Collect sample</button> <button data-action="result" data-index="${i}">Enter results</button>`)}</div>`;
    }else if(current==="inpatient"){
      const beds=await api("/inpatient/beds");rows=await api("/inpatient/admissions");
      $("content").innerHTML=`<div class="toolbar"><button data-action="round" class="primary">Record nursing round</button></div><div class="panel"><h2>Active admissions</h2>${table(rows,[["Admission","admission_number"],["Patient","patient_name"],["MRN","mrn"],["Bed","bed_number"]],(r,i)=>`<button data-action="discharge" data-index="${i}">Discharge</button>`)}</div><div class="panel"><h2>Bed availability</h2>${table(beds,[["Ward","ward_name"],["Room","room_number"],["Bed","bed_number"],["Status","status"]])}</div>`;
    }else if(current==="radiology"){
      rows=await api("/worklists/radiology");$("content").innerHTML=`<div class="panel">${table(rows,[["Order","order_number"],["Patient","patient_name"],["MRN","mrn"],["Test","test_name"],["Status","order_status"]])}</div>`;
    }else{
      rows=await api("/blood-bank/inventory");$("content").innerHTML=`<div class="panel">${table(rows,[["Unit","unit_number"],["Group","blood_group"],["Component","component_name"],["Expiry","expiry_date"],["Status","status"]])}</div>`;
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
  $("invoice-detail").innerHTML=`<div class="panel"><h2>${esc(r.invoice_number)}</h2><p>${esc(r.patient_name)} · ${esc(r.mrn)}</p>${table(r.items,[["Description","item_name"],["Quantity","quantity"],["Unit price","unit_price"],["Amount","line_total"]])}<p class="totals">Subtotal: ${money(r.subtotal_amount)}<br>Tax: ${money(r.tax_amount)} · Discount: ${money(r.discount_amount)}<br>Total: ${money(r.total_amount)}<br>Paid: ${money(r.paid_amount)} · Balance: ${money(r.balance_amount)}</p><h2>Payment history</h2>${table(r.payments,[["Method","method_name"],["Reference","payment_reference"],["Amount","payment_amount"],["Date","payment_date"]])}<div class="toolbar">${Number(r.balance_amount)>0?'<button class="primary" data-action="pay">Record payment</button>':''}<button data-action="print">Print invoice</button></div></div>`;
}
async function action(name,index){
  const row=rows[index];
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
  if(name==="round")return modal("Record nursing round",options("patient_id","Patient",rows,"patient_id","patient_name")+field("round_notes","Observations")+field("vital_signs_summary","Recorded vitals"),data=>api("/nursing/rounds","POST",data));
  if(name==="discharge")return modal(`Discharge · ${row.mrn}`,field("discharge_summary","Discharge summary")+options("discharge_disposition","Disposition",["Home","Transferred","Deceased"].map(v=>({v})),"v","v"),data=>api("/inpatient/discharges","POST",{...data,admission_id:row.admission_id}));
}
$("content").onclick=event=>{const button=event.target.closest("[data-action]");if(button)action(button.dataset.action,Number(button.dataset.index)).catch(error=>{$("message").textContent=error.message;});};
$("close-dialog").onclick=()=>$("dialog").close();$("refresh").onclick=render;
$("logout").onclick=()=>{Object.keys(localStorage).filter(k=>k.startsWith("hms_")).forEach(k=>localStorage.removeItem(k));location.assign("/");};
(async()=>{
  try{
    user=await api("/auth/me");$("user").textContent=user.name || user.username;
    const allowed=Object.entries(modules).filter(([,m])=>user.roles.some(r=>m.roles.includes(r)||["admin","super_admin"].includes(r)));
    if(!allowed.length){$("content").textContent="This role does not yet have an operational workspace.";return;}
    current=allowed.find(([,m])=>m.path===location.pathname)?.[0] || allowed[0][0];
    for(const [key,m] of allowed){const b=document.createElement("button");b.textContent=m.title;b.classList.toggle("active",key===current);b.onclick=()=>{current=key;document.querySelectorAll("nav button").forEach(el=>el.classList.remove("active"));b.classList.add("active");render();};$("navigation").append(b);}await render();
  }catch(error){$("message").textContent=error.message;}
})();
