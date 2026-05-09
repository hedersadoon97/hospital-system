function updateStatus(id, status){

  fetch("/update", {
    method: "POST",
    headers: {
      "Content-Type":"application/x-www-form-urlencoded"
    },
    body: new URLSearchParams({
      id: id,
      status: status
    }).toString()
  })

  .then(res => {

    if(!res.ok){
      throw new Error("Request failed");
    }

    return res.text();
  })

  .then(() => {

    if(status === "مكتمل"){

      showToast(
      "تم تحويل الحالة إلى مكتمل",
      "success"
      );

    }

    else if(status === "قيد العمل"){

      showToast(
      "تم تحويل الحالة إلى قيد العمل",
      "warn"
      );

    }

    else if(status === "تم استلام عينة التحليل"){

      showToast(
      "تم استلام عينة التحليل",
      "warn"
      );

    }

    else{

      showToast(
      "تم تحويل الحالة إلى غير مكتمل",
      "warn"
      );

    }

    fetchPatients(true);

  })

  .catch(err => {
    console.error(err);
    showToast("حدث خطأ أثناء تحديث الحالة", "error");
  });

}
async function loadUsers(){

const container =

document.getElementById(
"usersContainer"
);

if(!container) return;

const res =
await fetch("/all_users");

const users =
await res.json();

container.innerHTML = "";

users.forEach(user => {

container.innerHTML += `

<div class="
userCard
${user.blocked ? 'userBlocked' : ''}
">

<div>

<div style="font-weight:800">
${user.username}
</div>

<div style="
opacity:.7;
margin-top:4px;
">

الصلاحية:
${user.role}

<br>

الحالة:

${
user.blocked

?

'🚫 محظور'

:

'✅ نشط'

}

</div>

</div>

<div class="userActions">

${
!user.approved

?

`

<select id="role_${user.username}">

<option value="x2">
x2
</option>

<option value="view">
view
</option>

<option value="x1">
x1
</option>

</select>

<button
class="userBtn greenBtn"

onclick="
approveUser(
'${user.username}'
)
">

موافقة

</button>

<button
class="userBtn redBtn"

onclick="
rejectUser(
'${user.username}'
)
">

رفض

</button>

`

:

`

<button
class="userBtn redBtn"

onclick="
blockUser(
'${user.username}'
)
">

حظر

</button>
<button
class="userBtn blueBtn"

onclick="
unblockUser(
'${user.username}'
)
">

فك الحظر

</button>

<button
class="userBtn redBtn"

onclick="
deleteUser(
'${user.username}'
)
">

حذف

</button>

`

}

</div>

</div>

`;

});

}

async function approveUser(username){

const role = document
.getElementById(
`role_${username}`
).value;

const data =
new URLSearchParams({

username,
role

});

await fetch("/approve_user",{

method:"POST",

body:data

});

loadUsers();

}

async function rejectUser(username){

const data =
new URLSearchParams({

username

});

await fetch("/reject_user",{

method:"POST",

body:data

});

loadUsers();

}
async function unblockUser(username){

const data =
new URLSearchParams({

username

});

await fetch("/unblock_user",{

method:"POST",

body:data

});

showToast(
"تم فك الحظر",
"success"
);

loadUsers();

}
async function blockUser(username){

if(
!confirm(
"هل أنت متأكد من حظر المستخدم؟"
)
){

return;

}

const data =
new URLSearchParams({

username

});

await fetch("/block_user",{

method:"POST",

body:data

});

showToast(
"تم حظر المستخدم",
"warn"
);

loadUsers();

}

async function unblockUser(username){

const data =
new URLSearchParams({

username

});

await fetch("/unblock_user",{

method:"POST",

body:data

});

showToast(
"تم فك الحظر",
"success"
);

loadUsers();

}

async function deleteUser(username){

if(
!confirm(
"هل أنت متأكد من حذف المستخدم؟"
)
){

return;

}

const data =
new URLSearchParams({

username

});

await fetch("/delete_user",{

method:"POST",

body:data

});

showToast(
"تم حذف المستخدم",
"success"
);

loadUsers();

}

loadUsers();

function goSection(section){

  window.location =
  `/dashboard?section=${encodeURIComponent(section)}`;
}
function toggleDatePicker(){
  return;
}

function downloadCustomDate(){
  return;
}

window.addEventListener("click", function(e){
  return;
});
function customDateReport(){

  let d = prompt("ادخل التاريخ بهذا الشكل: 2026-05-01");

  if(!d) return;

  window.location = `/download?mode=custom&date=${d}`;
}


let allPatients = [];
let alertsStopped = false;
let lastData = "";
let currentFilter = "all";
let typingTimer = null;
let lastNoiseKey = "";

const bell =
document.getElementById(
"bellSound"
);

bell.loop = true;

const socket = io({

transports:["websocket"],

upgrade:false

});

socket.on(
"connect",
()=>{

console.log(
"✅ SOCKET CONNECTED"
);

}
);

socket.on(
"connect_error",
(err)=>{

console.log(
"❌ SOCKET ERROR",
err
);

}
);

socket.on(
"admin_notification",

(data)=>{

const badge =
document.getElementById(
"pendingBadge"
);

if(!badge) return;

loadPendingBadge();

showToast(
data.message,
"warn"
);

}
);
// 🔥 تنبيه فوري
socket.on("new_alert", (data) => {
  showToast("🚨 تنبيه جديد وصل فوراً", "error");
  bell.play();
  fetchPatients(true);
});

// 🔄 تحديث عام
socket.on("refresh", () => {
  fetchPatients(true);
});

document.body.addEventListener("click", () => {

  bell.volume = 1;

  bell.play()
  .then(() => {

    bell.pause();
    bell.currentTime = 0;

  })

  .catch(err => {
    console.log(err);
  });

}, { once: true });

function showToast(message, type = "success"){
  const t = document.getElementById("toast");
  t.className = "toast " + type;
  t.innerText = message;
  t.style.display = "block";
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => {
    t.style.display = "none";
  }, 2400);
}

function safe(text){
  return String(text ?? "")
    .replace(/&/g,"&amp;")
    .replace(/</g,"&lt;")
    .replace(/>/g,"&gt;")
    .replace(/"/g,"&quot;")
    .replace(/'/g,"&#39;");
}

function jsEscape(text){
  return String(text ?? "")
    .replace(/\\/g,"\\\\")
    .replace(/'/g,"\\'")
    .replace(/\r?\n/g," ")
    .replace(/"/g,'\\"');
}

let currentReportMode = "";


/* ===== فتح نافذة اختيار الشفت ===== */

function downloadReport(mode){

currentReportMode = mode;

document.getElementById(
"shiftModal"
).style.display = "flex";

}

/* ===== إغلاق نافذة الشفت ===== */

function closeShiftModal(){

document.getElementById(
"shiftModal"
).style.display = "none";

}

/* ===== اختيار الشفت ===== */

function selectShift(shift){

window.selectedShift = shift;

closeShiftModal();

/* ===== تاريخ مخصص ===== */

if(currentReportMode === "custom"){

document.getElementById(
"reportDateModal"
).style.display = "flex";

return;

}

/* ===== من تاريخ إلى تاريخ ===== */

if(currentReportMode === "range"){

document.getElementById(
"reportRangeModal"
).style.display = "flex";

return;

}

/* ===== التقارير العادية ===== */

window.location =

`/download?mode=${currentReportMode}&shift=${shift}`;

}

/* ===== إغلاق عند الضغط بالخارج ===== */

window.addEventListener(
"click",
function(e){
  return;
}
);

function logout(){
  window.location = "/logout";
}

function manualRefresh(){
  fetchPatients(true);
  showToast("تم تحديث البيانات", "info");
}

function setFilter(filter, el){
  currentFilter = filter;
  document.querySelectorAll(".filterBtn").forEach(btn => btn.classList.remove("active"));
  el.classList.add("active");
  renderTable();
}

function getSearchValue(){
  return document.getElementById("search").value.trim().toLowerCase();
}

function getAgeMinutes(timeStr){
  if(!timeStr) return null;
  const parts = String(timeStr).split(":");
  if(parts.length < 2) return null;

  const h = parseInt(parts[0], 10);
  const m = parseInt(parts[1], 10);
  const s = parseInt(parts[2] || "0", 10);

  if(Number.isNaN(h) || Number.isNaN(m) || Number.isNaN(s)) return null;

  const now = new Date();
  const patientTime = new Date();
  patientTime.setHours(h, m, s, 0);

  return (now - patientTime) / 1000 / 60;
}

function deriveStatus(p){
  const raw = p.status;
  const elapsed = getAgeMinutes(p.time);

  if(raw === "تنبيه 🔔"){
    return { status: raw, cls: "alert", display: raw, danger: false };
  }

  if(raw === "مكتمل"){
    return { status: raw, cls: "done", display: raw, danger: false };
  }

  if(raw === "غير مكتمل"){
    return { status: raw, cls: "notdone", display: raw, danger: false };
  }

  if(raw === "جار العمل"){

  // ⚠️ متأخر بعد ساعة ونصف
  if(elapsed !== null && elapsed > 90){

    return {

      status: "⚠️ متأخر",

      cls: "danger",

      display: "⚠️ متأخر",

      danger: true

    };

  }

  // ⏳ قيد العمل بعد 10 دقائق
  if(elapsed !== null && elapsed > 10){

    return {

      status: "⏳ قيد العمل",

      cls: "warning",

      display: "⏳ قيد العمل",

      danger: false

    };

  }

  // 🧪 تم استلام العينة
  return {

    status: "🧪 تم استلام عينة التحليل",

    cls: "working",

    display: "🧪 تم استلام عينة التحليل",

    danger: false

  };


  }

  if(raw === "⚠️ متأخر"){
    return { status: raw, cls: "danger", display: raw, danger: true };
  }

  if(raw === "⏳ قيد العمل"){
    return { status: raw, cls: "warning", display: raw, danger: false };
  }

  return { status: raw, cls: "working", display: raw, danger: false };
}

function getFilteredPatients(){
  const search = getSearchValue();
  let items = allPatients.slice();

  if(currentFilter === "done"){
    items = items.filter(p => deriveStatus(p).status === "مكتمل");
  }else if(currentFilter === "working"){
    items = items.filter(p => deriveStatus(p).status === "جار العمل" || deriveStatus(p).status === "⏳ قيد العمل");
  }else if(currentFilter === "alert"){
    items = items.filter(p => deriveStatus(p).status === "تنبيه 🔔");
  }else if(currentFilter === "danger"){
    items = items.filter(p => deriveStatus(p).danger);
  }

  if(!search){
    return items;
  }

  if(search.includes("متأخر")){
    return items.filter(p => deriveStatus(p).status === "⚠️ متأخر");
  }

  if(search.includes("تنبيه")){
    return items.filter(p => deriveStatus(p).status === "تنبيه 🔔");
  }

  return items.filter(p => {
    const d = deriveStatus(p);
    const text = [
      p.id, p.name, p.age, p.section, d.display, p.time, p.date, p.extra || ""
    ].join(" ").toLowerCase();

    return text.includes(search);
  });
}

function updateStats(){
  const total = allPatients.length;
  const done = allPatients.filter(p => deriveStatus(p).status === "مكتمل").length;
  const working = allPatients.filter(p => deriveStatus(p).status === "جار العمل" || deriveStatus(p).status === "⏳ قيد العمل").length;
  const alerts = allPatients.filter(p => deriveStatus(p).status === "تنبيه 🔔" || deriveStatus(p).danger).length;

  document.getElementById("totalCount").innerText = total;
  document.getElementById("doneCount").innerText = done;
  document.getElementById("workingCount").innerText = working;
  document.getElementById("alertCount").innerText = alerts;
}

function renderTable(){
  const scrollPosition = window.scrollY;
  const filtered = getFilteredPatients();
  const search = getSearchValue();

  let html = `
    <thead>
      <tr>
        <th>#</th>
        <th>اسم المريض</th>
        <th>العمر</th>
        <th>التحاليل</th>
        <th>القسم</th>
        <th>الحالة</th>
        <th>الوقت</th>
        <th>ملاحظات</th>
        <th>الإجراءات</th>
      </tr>
    </thead>
    <tbody>
  `;

  if(filtered.length === 0){
    html += `<tr><td colspan="7" class="noData">لا توجد نتائج مطابقة</td></tr>`;
  }else{
    filtered.forEach((p, i) => {
      const d = deriveStatus(p);

      html += `
   <tr class="${d.cls}">
  <td>${i + 1}</td>
  <td>${safe(p.name)}</td>
  <td>${safe(p.age)}</td>
  <td>

${p.tests

? `

<button
class="testsBtn"
data-tests="${safe(p.tests || '')}"
onclick="showTests(this.dataset.tests)">

🧪 ${(p.tests || '').split(',').filter(Boolean).length} عرض

</button>

`

: "-"}

</td>
  <td>${safe(p.section)}</td>

  <td>
    <span class="badgeStatus ${d.cls}">
      ${safe(d.display)}
    </span>
  </td>

  <td>${safe(p.time)}</td>

  <!-- 🔥 الملاحظات -->
  <td>

   ${
role === "view"

?

`

<div style="
opacity:.45;
font-size:13px;
text-align:center;
padding:10px;
">

🔒 مخفية

</div>

`

:

`

<textarea
class="noteBox"
onchange="saveNote(${p.id}, this.value)"
placeholder="اكتب ملاحظة...">${safe(p.extra || "")}</textarea>

`

}
</td>

<td>
      ${
role === "view"

?

`

<div style="
opacity:.45;
font-size:13px;
text-align:center;
padding:10px;
min-width:120px;
">

👁 مشاهدة فقط

</div>

`

:

role === "x1" ? `

<button class="btn green"
onclick="updateStatus(${p.id}, 'مكتمل')">
✔ مكتمل
</button>

<button class="btn amber"
onclick="updateStatus(${p.id}, 'قيد العمل')">
⏳ قيد العمل
</button>

<button class="btn red"
onclick="updateStatus(${p.id}, 'غير مكتمل')">
✖ غير مكتمل
</button>

<button class="btn blue"
onclick="openEditModal(
${p.id},
'${jsEscape(p.name)}',
'${jsEscape(p.age)}',
'${jsEscape(p.section)}'
)">
✏ تعديل
</button>

<button class="btn red"
onclick="deletePatient(${p.id})">
🗑 حذف
</button>

`

:

role === "x2" ? `

<button class="btn red"
onclick="alertPatient(${p.id})">
🚨 تنبيه
</button>

`

:

``

}

  

  </td>

</tr>
      `;
    });
  }

  html += `</tbody>`;

  document.getElementById("table").innerHTML = html;
  document.getElementById("searchInfo").innerText = search
    ? `نتائج البحث: ${filtered.length} | إجمالي السجلات اليوم: ${allPatients.length}`
    : `عرض السجلات الخاصة باليوم الحالي: ${filtered.length} سجل`;

  updateStats();
  window.scrollTo(0, scrollPosition);

  const dangerItems = filtered.filter(p => deriveStatus(p).danger);
  const alertItems = filtered.filter(p => deriveStatus(p).status === "تنبيه 🔔");
  const currentNoiseKey = `${dangerItems.length}-${alertItems.length}-${currentFilter}-${search}`;

  if(
!alertsStopped &&
(dangerItems.length > 0 || alertItems.length > 0) &&
role === "x1"
){
    if(bell.paused){
      bell.play().catch(() => {});
    }

    if(currentNoiseKey !== lastNoiseKey){
      if(dangerItems.length > 0){
        showToast("🚨 توجد حالة متأخرة تحتاج مراجعة", "error");
        notify("🚨 توجد حالة متأخرة في النظام");
      }else{
        showToast("🔔 يوجد تنبيه جديد", "warn");
        notify("🔔 يوجد تنبيه جديد في النظام");
      }
      lastNoiseKey = currentNoiseKey;
    }
  }else{
    bell.pause();
    bell.currentTime = 0;
    lastNoiseKey = "";
  }
}
async function fetchPatients(forceRender = false){

try{

const currentSection =
new URLSearchParams(window.location.search)
.get("section") || "all";

const r = await fetch(
`/api/patients?section=${encodeURIComponent(currentSection)}`,
{
cache:"no-store"
});

if(!r.ok){

throw new Error(
`Server Error: ${r.status}`
);

}

const data = await r.json();

const currentData =
JSON.stringify(data);

if(currentData !== lastData){

allPatients = data;

lastData = currentData;

renderTable();

}
else if(forceRender){

renderTable();

}

}
catch(e){

console.error(e);

showToast(
"حدث خطأ في جلب البيانات",
"error"
);

}

}
function showTests(tests){

const old =
document.getElementById("dynamicTestsPopup");

if(old){
old.remove();
}

const popup =
document.createElement("div");

popup.id = "dynamicTestsPopup";

popup.style.cssText = `

position:fixed;
inset:0;
background:rgba(0,0,0,.75);
z-index:999999999;
display:flex;
align-items:center;
justify-content:center;
padding:20px;

`;

const box =
document.createElement("div");

box.style.cssText = `

width:min(520px,100%);
max-height:80vh;
overflow:auto;
background:#0f172a;
border-radius:24px;
padding:24px;
border:1px solid rgba(255,255,255,.1);

`;

let html = `

<h2 style="
margin-top:0;
margin-bottom:20px;
text-align:center;
">

🧪 التحاليل المطلوبة

</h2>

`;

const arr =
(tests || "")
.split(",")
.filter(t => t.trim() !== "");

if(arr.length === 0){

html += `
<div>
لا توجد تحاليل
</div>
`;

}else{

arr.forEach(t => {

html += `

<div style="
background:rgba(59,130,246,.12);
padding:14px;
border-radius:14px;
margin-bottom:10px;
font-weight:700;
color:white;
">

🧪 ${t}

</div>

`;

});

}

html += `

<button
onclick="document.getElementById('dynamicTestsPopup').remove()"
style="
width:100%;
margin-top:14px;
padding:14px;
border:none;
border-radius:14px;
background:#ef4444;
color:white;
font-weight:800;
cursor:pointer;
">

إغلاق

</button>

`;

box.innerHTML = html;

popup.appendChild(box);

document.body.appendChild(popup);

}
function notify(msg){
  if("Notification" in window){
    if(Notification.permission === "granted"){
      new Notification(msg);
    }else if(Notification.permission !== "denied"){
      Notification.requestPermission();
    }
  }
}

function openAddModal(){
  document.getElementById("modalTitle").innerText = "إضافة مريض";
  document.getElementById("modalDesc").innerText = "أدخل اسم المريض والعمر والقسم بشكل صحيح.";
  document.getElementById("patientId").value = "";
  document.getElementById("name").value = "";
  document.getElementById("age").value = "";
  document.getElementById("section").value = "الاستشارية";
  document.getElementById("saveBtn").innerText = "حفظ";
  document.getElementById("saveBtn").className = "mBtn green";
  document
.querySelectorAll('input[name="tests"]')
.forEach(x => x.checked = false);
  openModal();
}

function openEditModal(id, name, age, section){
  document.getElementById("modalTitle").innerText = "تعديل مريض";
  document.getElementById("modalDesc").innerText = "قم بتحديث البيانات الأساسية للمريض.";
  document.getElementById("patientId").value = id;
  document.getElementById("name").value = name;
  document.getElementById("age").value = age;
  document.getElementById("section").value = section;
  document.getElementById("saveBtn").innerText = "تحديث";
  document.getElementById("saveBtn").className = "mBtn blue";
  openModal();
}

function openModal(){
  document.getElementById("modalBackdrop").style.display = "flex";
}

function closeModal(){
  document.getElementById("modalBackdrop").style.display = "none";
}

async function savePatient(){
  const id = document.getElementById("patientId").value.trim();
  const name = document.getElementById("name").value.trim();
  const age = document.getElementById("age").value.trim();
  const section = document.getElementById("section").value.trim();

  if(!name || !age || !section){
    showToast("املأ جميع الحقول", "error");
    return;
  }

  const btn = document.getElementById("saveBtn");
  const oldText = btn.innerText;
  btn.disabled = true;
  btn.innerText = "جاري الحفظ...";

try{

  const extra =
  document.getElementById("extra").value;
  const tests = [...document.querySelectorAll('input[name="tests"]:checked')]
.map(x => x.value);

  if(id){

    await fetch("/edit", {
      method:"POST",
      headers:{
        "Content-Type":"application/x-www-form-urlencoded"
      },
body:new URLSearchParams({

id,
name,
age,
section,
extra,
tests

}).toString()
    });

    showToast(
      "تم تحديث بيانات المريض",
      "success"
    );

  }else{

    await fetch("/add", {
      method:"POST",
      headers:{
        "Content-Type":"application/x-www-form-urlencoded"
      },
body:new URLSearchParams({

    name,
    age,
    section,
    extra,
    tests

}).toString()
    });

    showToast(
      "تمت إضافة المريض بنجاح",
      "success"
    );
  }

  closeModal();

  await fetchPatients(true);

}catch(e){

  console.log(e);

  showToast(
    "حدث خطأ أثناء الحفظ",
    "error"
  );

}finally{

  btn.disabled = false;

  btn.innerText = oldText;
}

}

function deletePatient(id){
  if(confirm("هل أنت متأكد من حذف هذا المريض؟")){
    fetch("/delete", {
      method:"POST",
      headers:{"Content-Type":"application/x-www-form-urlencoded"},
      body:new URLSearchParams({id}).toString()
    }).then(() => {
      showToast("تم حذف المريض", "success");
      fetchPatients(true);
    }).catch(() => {
      showToast("حدث خطأ أثناء الحذف", "error");
    });
  }
}

function alertPatient(id){
  fetch("/alert", {
  method:"POST",
  credentials: "include",   // 🔥 هذا المهم
  headers:{"Content-Type":"application/x-www-form-urlencoded"},
  body:new URLSearchParams({id}).toString()
}).then(() => {
  showToast("تم إرسال التنبيه", "warn");
  fetchPatients(true);
}).catch(() => {
  showToast("حدث خطأ في إرسال التنبيه", "error");
});
}

function stopAlert(){

  alertsStopped = true;

  fetch("/stop_alert", {
    method:"POST",
    headers:{
      "Content-Type":"application/x-www-form-urlencoded"
    },
    body:new URLSearchParams().toString()
  })

  .then(() => {

    showToast(
      "تم إيقاف التنبيهات",
      "info"
    );

    fetchPatients(true);

  })

  .catch(() => {

    showToast(
      "حدث خطأ أثناء إيقاف التنبيه",
      "error"
    );

  });

  bell.pause();
  bell.currentTime = 0;

}

function loadPageEffects(){
  document.getElementById("page").animate(
    [
      { opacity: 0, transform: "translateY(12px)" },
      { opacity: 1, transform: "translateY(0)" }
    ],
    { duration: 650, easing: "ease-out" }
  );
}

window.addEventListener("keydown", (e) => {
  if(e.key === "Escape"){
    closeModal();
  }
});

window.onload = function(){
  const params = new URLSearchParams(location.search);
  if(params.get("success")){ 
    showToast("✅ تم تسجيل الدخول بنجاح", "success");
    history.replaceState(null, "", "/dashboard");
  }

  if("Notification" in window && Notification.permission === "default"){
    Notification.requestPermission();
  }

  loadPageEffects();
  fetchPatients(true);
  loadPendingBadge();
};

async function loadPendingBadge(){

if(role !== "x1") return;

try{

const r = await fetch(
"/pending_notifications_count"
);

const data = await r.json();

const badge =
document.getElementById(
"pendingBadge"
);

if(!badge) return;

if(data.count > 0){

badge.style.display = "flex";

badge.innerText = data.count;

}else{

badge.style.display = "none";

}

}catch(err){

console.log(err);

}

}

setInterval(
loadPendingBadge,
5000
);

loadPendingBadge();
function saveNote(id, note){

fetch("/save_note", {

method:"POST",

headers:{
"Content-Type":"application/x-www-form-urlencoded"
},

body:new URLSearchParams({
id,
note
}).toString()

})

.then(() => {

showToast(
"تم حفظ الملاحظة",
"success"
);

})

.catch(() => {

showToast(
"حدث خطأ",
"error"
);

});

}

let settingsCaptchaResult = 0;

function generateSettingsCaptcha(){

const a = Math.floor(Math.random() * 9) + 1;
const b = Math.floor(Math.random() * 9) + 1;

settingsCaptchaResult = a + b;

document.getElementById(
"settingsCaptchaQuestion"
).innerText = `${a} + ${b} = ؟`;

}

function openSettingsModal(){

document.getElementById(
"settingsBackdrop"
).style.display = "flex";

generateSettingsCaptcha();

}

function closeSettingsModal(){

document.getElementById(
"settingsBackdrop"
).style.display = "none";

}

async function sendUsernameChangeRequest(){

const newUsername =
document.getElementById(
"newUsername"
).value.trim();

const currentPassword =
document.getElementById(
"currentPasswordForUsername"
).value.trim();

if(!newUsername){

showToast(
"اكتب اسم المستخدم الجديد",
"error"
);

return;

}

if(!currentPassword){

showToast(
"اكتب كلمة المرور الحالية",
"error"
);

return;

}

const data =
new URLSearchParams({

new_username:newUsername,

current_password:currentPassword

});

const res =
await fetch(
"/request_username_change",
{
method:"POST",
body:data
}
);

const text =
await res.text();

if(
text.includes("OK") ||
text.includes("success")
){

showToast(
"تم إرسال طلب تغيير الاسم",
"success"
);

}else{

showToast(
text,
"error"
);

}

}

async function sendPasswordChangeRequest(){

const currentPassword =
document.getElementById(
"currentPassword"
).value.trim();

const newPassword =
document.getElementById(
"newPassword"
).value.trim();

const confirmPassword =
document.getElementById(
"confirmNewPassword"
).value.trim();

const captcha =
document.getElementById(
"settingsCaptcha"
).value.trim();

if(
Number(captcha)
!== Number(settingsCaptchaResult)
){

showToast(
"فشل التحقق الأمني",
"error"
);

generateSettingsCaptcha();

return;

}

if(!currentPassword){

showToast(
"اكتب كلمة المرور الحالية",
"error"
);

return;

}

if(newPassword.length < 6){

showToast(
"كلمة المرور قصيرة",
"error"
);

return;

}

if(newPassword !== confirmPassword){

showToast(
"كلمتا المرور غير متطابقتين",
"error"
);

return;

}

const data =
new URLSearchParams({

current_password:currentPassword,

new_password:newPassword

});

const res =
await fetch(
"/request_password_change",
{
method:"POST",
body:data
}
);

const text =
await res.text();

if(text === "OK"){

showToast(
"تم إرسال طلب تغيير كلمة المرور",
"success"
);

}else{

showToast(
text,
"error"
);

}

}
/* ===== إغلاق نافذة التاريخ ===== */

function closeDateModal(){

document.getElementById(
"reportDateModal"
).style.display = "none";

}

/* ===== إغلاق نافذة المدى ===== */

function closeRangeModal(){

document.getElementById(
"reportRangeModal"
).style.display = "none";

}

/* ===== تحميل تقرير بتاريخ واحد ===== */

function downloadCustomReport(){

const date =
document.getElementById(
"singleReportDate"
).value;

if(!date){

showToast(
"اختر التاريخ",
"error"
);

return;

}

const url =

`/download?mode=custom&shift=${window.selectedShift}&date=${date}`;

closeDateModal();

window.location = url;

}

/* ===== تحميل تقرير بين تاريخين ===== */

function downloadRangeReport(){

const from =
document.getElementById(
"fromReportDate"
).value;

const to =
document.getElementById(
"toReportDate"
).value;

if(!from || !to){

showToast(
"اختر التاريخين",
"error"
);

return;

}

const url =

`/download?mode=range&shift=${window.selectedShift}&from=${from}&to=${to}`;

closeRangeModal();

window.location = url;

}

document.addEventListener("DOMContentLoaded", () => {

  // ===== زر الأرشيف العام =====

  const generalArchiveBtn =
  document.getElementById(
    "generalArchiveBtn"
  );

  if(generalArchiveBtn){

    generalArchiveBtn.onclick = () => {

      window.location.href =
      "/archive";

    };

  }

  // ===== زر أرشيف الشفت =====

  const privateArchiveBtn =
  document.getElementById(
    "privateArchiveBtn"
  );

  if(privateArchiveBtn){

    privateArchiveBtn.onclick = () => {

      window.location.href =
      "/shift_archive_page";

    };

  }

});

document.addEventListener("DOMContentLoaded", () => {

  // ===== اليومية =====

  const dailyStatsBtn =
  document.getElementById(
    "dailyStatsBtn"
  );

  if(dailyStatsBtn){

    dailyStatsBtn.onclick = () => {

      window.location.href =
      "/download?mode=day&shift=all";

    };

  }

  // ===== الأسبوعية =====

  const weeklyStatsBtn =
  document.getElementById(
    "weeklyStatsBtn"
  );

  if(weeklyStatsBtn){

    weeklyStatsBtn.onclick = () => {

      window.location.href =
      "/download?mode=week&shift=all";

    };

  }

  // ===== الشهرية =====

  const monthlyStatsBtn =
  document.getElementById(
    "monthlyStatsBtn"
  );

  if(monthlyStatsBtn){

    monthlyStatsBtn.onclick = () => {

      window.location.href =
      "/download?mode=month&shift=all";

    };

  }

});

  // ===== تاريخ مخصص =====

 // ===== التاريخ المخصص =====

const customStatsBtn =
document.getElementById(
  "customStatsBtn"
);

if(customStatsBtn){

  customStatsBtn.onclick = () => {

    document.getElementById(
      "customDateModal"
    ).style.display = "flex";

  };

}

// ===== اغلاق النافذة =====

function closeCustomDateModal(){

  document.getElementById(
    "customDateModal"
  ).style.display = "none";

}

// ===== تنزيل التقرير =====

function downloadCustomRange(){

  const fromDate =
  document.getElementById(
    "oldCustomFromDate"
  );

  const toDate =
  document.getElementById(
    "oldCustomToDate"
  );

  if(
    !fromDate.value ||
    !toDate.value
  ){

    showToast(
      "اختر التاريخ",
      "error"
    );

    return;

  }

  window.location.href =

  `/download?mode=range&shift=all&from=${encodeURIComponent(fromDate.value)}&to=${encodeURIComponent(toDate.value)}`;

}
