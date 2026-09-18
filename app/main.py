from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from math import radians, sin, cos, sqrt, atan2
from app.cobli import CobliClient, CobliError

app=FastAPI(title="Rota API",version="0.2.0")

technicians=[
 {"id":1,"name":"Ana Silva","lat":-16.6869,"lng":-49.2648,"status":"Disponível"},
 {"id":2,"name":"Carlos Souza","lat":-16.7270,"lng":-49.2530,"status":"Em rota"},
 {"id":3,"name":"Marcos Lima","lat":-16.7490,"lng":-49.2850,"status":"Disponível"},
]
orders=[
 {"id":1001,"customer":"Loja Centro","address":"Centro, Goiânia","lat":-16.6799,"lng":-49.2550,"priority":"Alta","status":"Pendente"},
 {"id":1002,"customer":"Cliente Bueno","address":"Setor Bueno, Goiânia","lat":-16.7040,"lng":-49.2730,"priority":"Normal","status":"Pendente"},
 {"id":1003,"customer":"Empresa Aparecida","address":"Aparecida de Goiânia","lat":-16.8235,"lng":-49.2439,"priority":"Alta","status":"Pendente"},
 {"id":1004,"customer":"Cliente Jardim América","address":"Jardim América, Goiânia","lat":-16.7160,"lng":-49.2910,"priority":"Normal","status":"Pendente"},
]

def distance(a,b):
 r=6371
 p1,p2=radians(a["lat"]),radians(b["lat"])
 dp=radians(b["lat"]-a["lat"]); dl=radians(b["lng"]-a["lng"])
 x=sin(dp/2)**2+cos(p1)*cos(p2)*sin(dl/2)**2
 return 2*r*atan2(sqrt(x),sqrt(1-x))

@app.get("/api/dashboard")
def dashboard():
 return {"orders":len(orders),"technicians":len(technicians),"pending":sum(o["status"]=="Pendente" for o in orders),"routes":0}

@app.get("/api/technicians")
def get_technicians(): return technicians

@app.get("/api/orders")
def get_orders(): return orders

@app.post("/api/optimize")
def optimize():
 result=[]
 for o in orders:
  t=min(technicians,key=lambda x:distance(x,o))
  result.append({"order":o,"technician":t,"distance_km":round(distance(t,o),1)})
 return {"routes":result}

def cobli_call(method,*args,**kwargs):
 try:
  return getattr(CobliClient(),method)(*args,**kwargs)
 except CobliError as e:
  raise HTTPException(status_code=e.status_code,detail=e.message)

@app.get("/api/cobli/status")
def cobli_status(): return CobliClient().status()

@app.get("/api/cobli/drivers")
def cobli_drivers(limit:int=200,page:int=1): return cobli_call("drivers",limit,page)

@app.get("/api/cobli/devices")
def cobli_devices(limit:int=200,page:int=1): return cobli_call("devices",limit,page)

@app.get("/api/cobli/routes")
def cobli_routes(start_in_millis:int|None=None,end_in_millis:int|None=None):
 return cobli_call("routes",start_in_millis,end_in_millis)

@app.get("/api/cobli/paths")
def cobli_paths(startDate:str,endDate:str,limit:int=200,page:int=1):
 return cobli_call("paths",startDate,endDate,limit,page)

app.mount("/static",StaticFiles(directory="static"),name="static")
@app.get("/")
def home(): return FileResponse("static/index.html")
