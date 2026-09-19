const API=(window.ROTA_CONFIG?.API_URL||"").replace(/\/$/,"");
const center=[-16.71,-49.27];
const url=p=>API+p;
let cachedOrders=[];
let cachedTechs=[];
let maps={};

async function api(path,opt){
  const response=await fetch(url(path),opt);
  if(!response.ok) throw new Error("API "+response.status);
  return response.json();
}

function alertApi(msg){
  apiAlert.textContent=msg;
  apiAlert.classList.remove("hidden");
}

function riskClass(risk){
  return {
    "Estourado":"danger",
    "Crítico":"danger",
    "Atenção":"warning",
    "Dentro do prazo":"ok"
  }[risk]||"";
}

async function load(){
  try{
    const [dashboard,orders,techs,health]=await Promise.all([
      api("/api/dashboard"),
      api("/api/orders"),
      api("/api/technicians"),
      api("/api/health")
    ]);
    cachedOrders=orders;
    cachedTechs=techs;
    ordersN.textContent=dashboard.orders;
    pendingN.textContent=dashboard.pending;
    criticalN.textContent=dashboard.critical_orders;
    slaN.textContent=dashboard.sla_risk;
    techN.textContent=dashboard.technicians;
    availableN.textContent=dashboard.available_technicians;
    healthBadge.textContent=health.status==="ok"?"API online":"API indisponível";
    healthBadge.classList.add("online");
    renderOrders();
    renderTechs();
    draw("miniMap",orders,techs);
  }catch(e){
    alertApi("Frontend publicado. Configure API_URL em static/config.js com o endereço público do backend FastAPI.");
    draw("miniMap");
  }
}

function renderOrders(){
  const priority=priorityFilter?.value||"";
  const risk=riskFilter?.value||"";
  const list=cachedOrders.filter(o=>(!priority||o.priority===priority)&&(!risk||o.sla_risk===risk));
  orderList.innerHTML=list.map(o=>`
    <div class="row">
      <span>
        <b>#${o.id} ${o.customer}</b><br>
        <small>${o.address} • ${o.type}</small>
      </span>
      <span class="row-meta">
        <span class="badge priority">${o.priority}</span>
        <span class="badge ${riskClass(o.sla_risk)}">${o.sla_risk}</span>
        <small>${o.sla_remaining_hours}h SLA</small>
      </span>
    </div>`).join("")||'<p class="empty">Nenhuma OS encontrada com esses filtros.</p>';
}

function renderTechs(){
  techList.innerHTML=cachedTechs.map(t=>`
    <div class="row">
      <span><b>${t.name}</b><br><small>${t.skills.join(" • ")}</small></span>
      <span class="row-meta">
        <span class="badge">${t.status}</span>
        <small>capacidade: ${t.capacity}</small>
      </span>
    </div>`).join("");
}

function draw(id,orders=[],techs=[]){
  const el=document.getElementById(id);
  if(!el) return;
  if(maps[id]){
    maps[id].remove();
  }
  const map=L.map(id).setView(center,11);
  maps[id]=map;
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{
    attribution:"© OpenStreetMap"
  }).addTo(map);
  orders.forEach(o=>{
    L.marker([o.lat,o.lng]).addTo(map)
      .bindPopup(`OS #${o.id} — ${o.customer}<br>${o.priority} • ${o.sla_risk||""}`);
  });
  techs.forEach(t=>{
    L.circleMarker([t.lat,t.lng],{radius:9}).addTo(map)
      .bindPopup(`Técnico: ${t.name}<br>${t.status}`);
  });
}

async function optimize(){
  show("map");
  try{
    const strategy=document.getElementById("strategy").value;
    const data=await api("/api/optimize?strategy="+encodeURIComponent(strategy),{method:"POST"});
    const os=data.routes.map(x=>x.order);
    const techMap={};
    data.routes.forEach(x=>techMap[x.technician.id]=x.technician);
    setTimeout(()=>draw("bigMap",os,Object.values(techMap)),50);

    routeSummary.innerHTML=`
      <article><b>${data.summary.orders_assigned}</b><span>OS distribuídas</span></article>
      <article><b>${data.summary.estimated_distance_km} km</b><span>Distância estimada</span></article>
      <article><b>${data.summary.strategy}</b><span>Estratégia</span></article>`;

    result.innerHTML='<h3>Distribuição sugerida</h3>'+data.routes.map(x=>`
      <div class="row">
        <span>
          OS #${x.order.id} → <b>${x.technician.name}</b><br>
          <small>${x.order.priority} • ${x.order.sla_risk}</small>
        </span>
        <span class="row-meta"><b>${x.distance_km} km</b><small>carga #${x.assigned_load}</small></span>
      </div>`).join("");
  }catch(e){
    alertApi("Backend indisponível. Confira API_URL.");
  }
}

function show(id){
  ["dashboard","map","orders","techs"].forEach(x=>document.getElementById(x).classList.toggle("hidden",x!==id));
  title.textContent={
    dashboard:"Visão Operacional",
    map:"Planejamento de Rotas",
    orders:"Ordens de Serviço",
    techs:"Equipes"
  }[id];
  if(id==="map"){
    setTimeout(()=>draw("bigMap",cachedOrders,cachedTechs),50);
  }
}

load();