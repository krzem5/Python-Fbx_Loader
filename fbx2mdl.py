import os
import struct
import zlib
import math



HEAD_MAGIC=b"Kaydara FBX Binary\x20\x20\x00\x1a\x00"
BLOCK_SENTINEL_LENGTH=13



def _r_arr(dt,i,f):
	ln,e,l=struct.unpack("<III",dt[i:i+12])
	o=dt[i+12:i+l+12]
	if (e==1):
		o=zlib.decompress(o)
	o=list(struct.unpack("<"+f*ln,o))
	return (i+l+12,o)



def _parse(dt,i):
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
			i,el=_parse(dt,i)
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



def _get_frame(off,f):
	return math.ceil(((f-off)//46186158)/(1000/60))



def _get_refs(cl,ol,id_,k=None):
	if (k==-1):
		return [(e[1],ol[e[0]]) for e in cl[id_] if e[0] in list(ol.keys())]
	for e in cl[id_]:
		if (e[1]==k):
			return ol[e[0]]
	return None



def _write_anim(f,off,cl,ol,m):
	p=_get_prop70(_get_child(m,"Properties70"),"Lcl Translation")
	r=_get_prop70(_get_child(m,"Properties70"),"Lcl Rotation")
	l=_get_refs(cl,ol,m["id"],-1)[:255]
	dt={"x":[p[0]],"y":[p[1]],"z":[p[2]],"rx":[r[0]],"ry":[r[1]],"rz":[r[2]]}
	fl=0
	c=0
	for et,e in l:
		if (e["type"]=="Model"):
			c+=1
		elif (e["type"]=="AnimationCurveNode"):
			al=_get_refs(cl,ol,e["id"],-1)
			for t,k in al:
				if (len(t)!=3 or t[:2]!="d|" or t[2] not in "xyzXYZ"):
					raise RuntimeError
				kl=_get_child(k,"KeyTime")["data"][0]
				kv=_get_child(k,"KeyValueFloat")["data"][0]
				dt[("" if et=="Lcl Translation" else "r")+t[2].lower()]=([] if kl[0]==0 else [(0,dt[("" if et=="Lcl Translation" else "r")+t[2].lower()])])
				lk=None
				for i,v in enumerate(kl):
					if (lk!=None and lk<_get_frame(off,v)-1):
						j=_get_frame(off,kl[i-1])+1
						ln=_get_frame(off,v)-_get_frame(off,kl[i-1])
						while (j!=_get_frame(off,v)):
							dt[("" if et=="Lcl Translation" else "r")+t[2].lower()]+=[kv[i-1]+j/ln*(kv[i]-kv[i-1])]
							j+=1
					dt[("" if et=="Lcl Translation" else "r")+t[2].lower()]+=[kv[i]]
					lk=_get_frame(off,v)
				if (len(dt[("" if et=="Lcl Translation" else "r")+t[2].lower()])>1):
					fl|=(1<<(ord(t[2].lower())-120+(0 if et=="Lcl Translation" else 3)))
	f.write(struct.pack(f">B{len(m['name'][:255])}sBB{sum([len(e) for e in dt.values()])}f",len(m["name"][:255]),bytes(m["name"][:255],"utf-8"),fl,c,*dt["x"],*dt["y"],*dt["z"],*dt["rx"],*dt["ry"],*dt["rz"]))
	for et,e in l:
		if (e["type"]=="Model"):
			_write_anim(f,off,cl,ol,e)



def _write_pose(f,cl,ol,p):
	def _join(l,ch,k):
		if (k in list(ch.keys())):
			if ("children" not in list(l[k].keys())):
				l[k]["children"]=[]
			for e in ch[k]:
				l=_join(l,ch,e)
				l[k]["children"]+=[l[e]]
				del l[e]
		return l
	def _read_mdl(cl,ol,l,ch,nr,k,anr):
		if (k["name"][:-len(k["name"].split("::")[-1])-2] not in list(l.keys())):
			l[k["name"][:-len(k["name"].split("::")[-1])-2]]={}
		l[k["name"][:-len(k["name"].split("::")[-1])-2]]["name"]=k["name"]
		if (anr==True):
			nr+=[k["name"][:-len(k["name"].split("::")[-1])-2]]
		for et,e in _get_refs(cl,ol,k["id"],-1):
			if (e["type"]=="NodeAttribute"):
				l[k["name"][:-len(k["name"].split("::")[-1])-2]]["len"]=_get_prop70(_get_child(e,"Properties70"),"Size")[0]
			elif (e["type"]=="Model"):
				if (k["name"][:-len(k["name"].split("::")[-1])-2] not in list(ch.keys())):
					ch[k["name"][:-len(k["name"].split("::")[-1])-2]]=[e["name"][:-len(e["name"].split("::")[-1])-2]]
				elif (e["name"][:-len(e["name"].split("::")[-1])-2] not in ch[k["name"][:-len(k["name"].split("::")[-1])-2]]):
					ch[k["name"][:-len(k["name"].split("::")[-1])-2]]+=[e["name"][:-len(e["name"].split("::")[-1])-2]]
				l,ch,nr=_read_mdl(cl,ol,l,ch,nr,e,True)
			elif (e["type"]=="Geometry"):
				pass
			elif (e["type"]=="Material"):
				pass
			elif (e["type"]=="AnimationCurveNode"):
				pass
			else:
				raise RuntimeError(e["type"])
		return (l,ch,nr)
	l={}
	ch={}
	nr=[]
	for k in p["children"]:
		if (k["name"]=="PoseNode"):
			k=ol[_get_child(k,"Node")["data"][0]]
			if (k["type"]=="NodeAttribute"):
				if (k["name"][:-len(k["name"].split("::")[-1])-2] not in list(l.keys())):
					l[k["name"][:-len(k["name"].split("::")[-1])-2]]={}
				l[k["name"][:-len(k["name"].split("::")[-1])-2]]["len"]=_get_prop70(_get_child(k,"Properties70"),"Size")[0]
			elif (k["type"]=="Model"):
				l,ch,nr=_read_mdl(cl,ol,l,ch,nr,k,False)
			else:
				raise RuntimeError(k["type"])
	for k in [e for e in l.keys() if e not in nr]:
		l=_join(l,ch,k)
	l={k:v for k,v in l.items() if "len" in list(v.keys())}
	with open("tmp.json","w") as tf:
		tf.write(__import__("json").dumps(l,indent=4,sort_keys=False).replace("    ","\t"))
	f.write(struct.pack(">I",_get_child(p,"NbPoseNodes")["data"][0]))



for fp in os.listdir("."):
	if (fp[-4:]==".fbx"):
		with open(fp,"rb") as f:
			dt=f.read()
		if (dt[:len(HEAD_MAGIC)]!=HEAD_MAGIC):
			continue
		print(fp)
		i=len(HEAD_MAGIC)+4
		gs=None
		ol=None
		cl=None
		df=None
		t=0
		p=None
		while (i<len(dt)):
			i,e=_parse(dt,i)
			if (i==None):
				break
			if (e["name"]=="GlobalSettings"):
				gs=e
			elif (e["name"]=="Objects"):
				ol={}
				for k in e["children"]:
					ol[k["data"][0]]={"id":k["data"][0],"type":k["name"],"name":k["data"][1],"children":k["children"]}
					if (k["name"]=="AnimationStack"):
						t|=1
					if (k["name"]=="Pose"):
						t|=2
						p=ol[k["data"][0]]
			elif (e["name"]=="Definitions"):
				df={}
				for k in e["children"]:
					if (k["name"]=="ObjectType" and k["data"][0]!="GlobalSettings"):
						if (_get_child(k,"PropertyTemplate")!=None):
							df[k["data"][0]]=_get_child(_get_child(k,"PropertyTemplate"),"Properties70")["children"]
						else:
							df[k["data"][0]]=[]
			elif (e["name"]=="Connections"):
				cl={}
				for c in e["children"]:
					if (c["data"][2] not in list(cl.keys())):
						cl[c["data"][2]]=[]
					cl[c["data"][2]]+=[[c["data"][1],(None if len(c["data"])==3 else c["data"][3])]]
		for k,v in ol.items():
			ch=_get_child(v,"Properties70")
			kn=[]
			if (ch==None):
				v["children"]+=[{"name":"Properties70","children":[]}]
				ch=v["children"][-1]
			else:
				for e in ch["children"]:
					kn+=[e["data"][0]]
			for e in df[v["type"]]:
				if (e["data"][0] not in kn):
					kn+=[e["data"][0]]
					ch["children"]+=[e]
		off=_get_prop70(_get_child(gs,"Properties70"),"TimeSpanStart")[0]
		if (t&1!=0):
			with open(f"{fp[:-4]}.anm","wb") as f:
				f.write(struct.pack(">H",_get_frame(off,_get_prop70(_get_child(gs,"Properties70"),"TimeSpanStop")[0])))
				_write_anim(f,off,cl,ol,_get_refs(cl,ol,0))
		if (t&2!=0):
			with open(f"{fp[:-4]}.mdl","wb") as f:
				_write_pose(f,cl,ol,p)
