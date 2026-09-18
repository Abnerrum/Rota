import os
import httpx

BASE_URL="https://api.cobli.co"

class CobliError(Exception):
 def __init__(self,status_code:int,message:str):
  self.status_code=status_code
  self.message=message

class CobliClient:
 def __init__(self):
  self.api_key=os.getenv("COBLI_API_KEY","").strip()

 def status(self):
  return {"configured":bool(self.api_key),"provider":"Cobli"}

 def _get(self,path,params=None):
  if not self.api_key:
   raise CobliError(503,"COBLI_API_KEY não configurada no servidor.")
  try:
   r=httpx.get(BASE_URL+path,headers={"cobli-api-key":self.api_key,"accept":"application/json"},params=params,timeout=20)
  except httpx.RequestError as e:
   raise CobliError(502,f"Falha de comunicação com a Cobli: {e}")
  if r.status_code>=400:
   raise CobliError(r.status_code,f"Cobli respondeu HTTP {r.status_code}")
  return r.json()

 def drivers(self,limit=200,page=1):
  return self._get("/public/v1/drivers",{"limit":limit,"page":page})

 def devices(self,limit=200,page=1):
  return self._get("/public/v1/devices",{"limit":limit,"page":page})

 def routes(self,start_in_millis=None,end_in_millis=None):
  params={"pageable.page":0,"pageable.size":200}
  if start_in_millis is not None: params["start_in_millis"]=start_in_millis
  if end_in_millis is not None: params["end_in_millis"]=end_in_millis
  return self._get("/public/v2/routes",params)

 def paths(self,start_date,end_date,limit=200,page=1):
  return self._get("/public/v1/paths",{"startDate":start_date,"endDate":end_date,"limit":limit,"page":page,"timezone":"America/Sao_Paulo"})
