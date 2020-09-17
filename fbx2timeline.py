import os
import struct
import json
import zlib



HEAD_MAGIC=b"Kaydara FBX Binary\x20\x20\x00\x1a\x00"
BLOCK_SENTINEL_LENGTH=13



def _r_arr(dt,i,f):
	ln,e,l=struct.unpack("<III",dt[i:i+12])
	o=dt[i+12:i+l+12]
	if (e==1):
		o=zlib.decompress(o)
	o=list(struct.unpack("<"+f*ln,o))
	return (i+l+12,o)



def parse(dt,i):
	e=struct.unpack("<I",dt[i:i+4])[0]
	if (e==0):
		return (None,{})
	pc=struct.unpack("<I",dt[i+4:i+8])[0]
	ln=struct.unpack("B",dt[i+12:i+13])[0]
	o={"name":str(dt[i+13:i+13+ln],"utf-8")}
	if (pc>0):
		o["data"]=[]
	i+=13+ln
	for _ in range(0,pc):
		if (chr(dt[i])=="Y"):
			o["data"]+=[struct.unpack("<h",dt[i+1:i+3])[0]]
			i+=3
		elif (chr(dt[i])=="C"):
			o["data"]+=[struct.unpack("?",dt[i+1:i+2])[0]]
			i+=2
		elif (chr(dt[i])=="I"):
			o["data"]+=[struct.unpack("<i",dt[i+1:i+5])[0]]
			i+=5
		elif (chr(dt[i])=="F"):
			o["data"]+=[struct.unpack("<f",dt[i+1:i+5])[0]]
			i+=5
		elif (chr(dt[i])=="D"):
			o["data"]+=[struct.unpack("<d",dt[i+1:i+9])[0]]
			i+=9
		elif (chr(dt[i])=="L"):
			o["data"]+=[struct.unpack("<q",dt[i+1:i+9])[0]]
			i+=9
		elif (chr(dt[i])=="R"):
			ln=struct.unpack("<I",dt[i+1:i+5])[0]
			o["data"]+=["".join([f"\\x{hex(e)[2:].rjust(2,'0')}" for e in dt[i+5:i+ln+5]])]
			i+=ln+5
		elif (chr(dt[i])=="S"):
			ln=struct.unpack("<I",dt[i+1:i+5])[0]
			o["data"]+=[str(dt[i+5:i+ln+5],"utf-8").replace("\x00\x01","::")]
			i+=ln+5
		elif (chr(dt[i])=="f"):
			i,el=_r_arr(dt,i+1,"f")
			o["data"]+=[el]
		elif (chr(dt[i])=="i"):
			i,el=_r_arr(dt,i+1,"i")
			o["data"]+=[el]
		elif (chr(dt[i])=="d"):
			i,el=_r_arr(dt,i+1,"d")
			o["data"]+=[el]
		elif (chr(dt[i])=="l"):
			i,el=_r_arr(dt,i+1,"q")
			o["data"]+=[el]
		elif (chr(dt[i])=="b"):
			i,el=_r_arr(dt,i+1,"b")
			o["data"]+=[el]
		elif (chr(dt[i])=="c"):
			i,el=_r_arr(dt,i+1,"c")
			o["data"]+=[el]
		else:
			raise RuntimeError("AAA")
	if (i<e):
		o["children"]=[]
		while (i<e-BLOCK_SENTINEL_LENGTH):
			i,el=parse(dt,i)
			if (i==None):
				raise RuntimeError("AAA")
			o["children"]+=[el]
		if (dt[i:i+BLOCK_SENTINEL_LENGTH]!=b"\x00"*BLOCK_SENTINEL_LENGTH):
			raise RuntimeError("AAA")
		i+=BLOCK_SENTINEL_LENGTH
	if (i!=e):
		print(i,e)
		raise IOError("Scope Not Reached!")
	return (i,o)



def _get_child(o,nm):
	for e in o["children"]:
		if (e["name"]==nm):
			return e
	return None



def _get_prop70(o,nm):
	for e in o["children"]:
		if (e["name"]=="P" and e["data"][0]==nm):
			return e["data"][4:]
	return None



def _get_frame(fps,f):
	return round(f//46186158/(1000/fps))



def _get_ref(cl,ol,id_,k=None):
	if (k==-1):
		return [ol[e[0]] for e in cl[id_]]
	for e in cl[id_]:
		if (e[1]==k):
			return ol[e[0]]
	return None



def _get_model(cl,ol,id_):
	m=_get_ref(cl,ol,id_)
	o={"name":m["name"]}
	print(o,_get_child(m,"Properties70"))
	return o



for k in os.listdir("."):
	if (k[-4:]==".fbx"):
		with open(k,"rb") as f:
			dt=f.read()
		if (dt[:len(HEAD_MAGIC)]!=HEAD_MAGIC):
			continue
		with open(f"{k[:-4]}-timeline.json","w") as f:
			i=len(HEAD_MAGIC)+4
			gs=None
			ol=None
			cl=None
			df=None
			as_=None
			while (i<len(dt)):
				i,e=parse(dt,i)
				if (i==None):
					break
				if (e["name"]=="GlobalSettings"):
					gs=e
				elif (e["name"]=="Objects"):
					ol={}
					for k in e["children"]:
						ol[k["data"][0]]={"id":k["data"][0],"type":k["name"],"name":k["data"][1],"children":k["children"]}
						if (k["name"]=="AnimationStack"):
							as_=ol[k["data"][0]]
				elif (e["name"]=="Definitions"):
					df={}
					for k in e["children"]:
						if (k["name"]=="ObjectType" and k["data"][0]!="GlobalSettings"):
							df[k["data"][0]]=_get_child(k,"PropertyTemplate")
							raise RuntimeError
				elif (e["name"]=="Connections"):
					cl={}
					for c in e["children"]:
						if (c["data"][2] not in list(cl.keys())):
							cl[c["data"][2]]=[]
						cl[c["data"][2]]+=[[c["data"][1],(None if len(c["data"])==3 else c["data"][3])]]
			fps=["default",120,100,60,50,48,30,30,"drop",29.97,25,24,"1000 milli/s",23.976,"custom",96,72,59.94,"time-modes"][_get_prop70(_get_child(gs,"Properties70"),"TimeMode")[0]]
			o={"name":as_["name"],"fps":fps,"start_frame":_get_frame(fps,_get_prop70(_get_child(gs,"Properties70"),"TimeSpanStart")[0]),"end_frame":_get_frame(fps,_get_prop70(_get_child(gs,"Properties70"),"TimeSpanStop")[0]),"model":_get_model(cl,ol,0)}
			# for l in _get_ref(cl,ol,as_["id"],-1):
			# 	for n in _get_ref(cl,ol,l["id"],-1):
			# 		o["nodes"]+=[{"name":n["name"],"channels":{}}]
			# 		for p in _get_child(n,"Properties70")["children"]:
			# 			o["nodes"][-1]["channels"][p["data"][0]]=[]
			# 			c=_get_ref(cl,ol,n["id"],p["data"][0])
			# 			kl=_get_child(c,"KeyTime")["data"][0]
			# 			kv=_get_child(c,"KeyValueFloat")["data"][0]
			# 			for i,t in enumerate(kl):
			# 				o["nodes"][-1]["channels"][p["data"][0]]+=[(_get_frame(fps,t),kv[i])]
			f.write(json.dumps(o,indent=4,sort_keys=False).replace("    ","\t"))
